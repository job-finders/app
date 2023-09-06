from flask import render_template, url_for

from src.main import send_mail
from src.emailer import EmailModel
from src.database.sql.notifications import NotificationsORM
from src.database.models.notifications import Notifications
from src.controllers.controller import Controllers


class NotificationsController(Controllers):

    def __init__(self):
        super().__init__()

    async def create_notification_email(self, notification: Notifications):
        with self.get_session() as session:
            notification_orm = NotificationsORM(**notification.dict())
            session.add(notification_orm)
            session.commit()

            return notification

    async def send_notification_verification_email(self, notification: Notifications):
        link = url_for('home.verify_email', _external=True, verification_id=notification.verification_id)
        link_with_params = f"{link}?email={notification.email}"
        context = dict(verification_link=link_with_params)
        email_html = render_template("email/welcome.html", **context)
        msg = EmailModel(subject_="JobFinders.site Job Alert - Email Verification",
                         to_=notification.email, html_=email_html)
        self.logger.info(f"Welcome Email Sent to : {notification.email}")
        await send_mail.send_mail_resend(email=msg)

    async def check_verification(self, verification_id: str, email: str) -> bool:
        with self.get_session() as session:
            notification_orm: NotificationsORM = session.query(NotificationsORM).filter(
                NotificationsORM.email == email).first()
            if notification_orm.verification_id == verification_id:
                notification_orm.is_verified = True
                session.merge(notification_orm)
                session.commit()
            return notification_orm.verification_id == verification_id
