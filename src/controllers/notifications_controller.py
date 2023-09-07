from flask import render_template, url_for
from pymysql import OperationalError

from src.main import send_mail
from src.emailer import EmailModel
from src.database.sql.notifications import NotificationsORM
from src.database.models.notifications import Notifications
from src.controllers.controller import Controllers


class NotificationsController(Controllers):

    def __init__(self):
        super().__init__()

    async def create_notification_email(self, notification: Notifications):
        try:
            with self.get_session() as session:
                notification_orm_ = session.query(NotificationsORM).filter(NotificationsORM.email == notification.email).first()
                if notification_orm_:
                    return None
                notification_orm = NotificationsORM(**notification.dict())

                session.add(notification_orm)
                session.commit()

                return notification
        except OperationalError as e:
            self.logger.info("Operational Error on create_notification_email")

    @staticmethod
    def generate_verification_link(notification):
        return url_for('home.verify_email', _external=True, verification_id=notification.verification_id, email=notification.email)

    async def send_notification_verification_email(self, notification):
        link_with_params = self.generate_verification_link(notification)
        context = {'verification_link': link_with_params}
        email_html = render_template("email/welcome.html", **context)
        subject = "JobFinders.site Job Alert - Email Verification"
        msg = EmailModel(subject_=subject, to_=notification.email, html_=email_html)
        self.logger.info(f"Welcome Email Sent to: {notification.email}")
        await send_mail.send_mail_resend(email=msg)

    async def check_verification(self, verification_id: str, email: str) -> bool:
        with self.get_session() as session:
            notification_orm: NotificationsORM = session.query(NotificationsORM).filter(
                NotificationsORM.email == email).first()
            if notification_orm and notification_orm.verification_id == verification_id:
                notification_orm.is_verified = True
                session.commit()

            return notification_orm and notification_orm.verification_id == verification_id
