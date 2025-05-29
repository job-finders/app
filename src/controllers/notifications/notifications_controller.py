from datetime import datetime

from flask import render_template, url_for
import asyncio
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


    async def send_job_alert_email(self, notification: Notifications, jobs: list, category: str):
        """
        Send a job alert email with a list of job postings.

        :param notification: Notifications instance with user details.
        :param jobs: List of dicts with keys: title, company, location, link
        :param category: Category of the job alert, e.g., "nursing"
        """
        try:
            context = {
                "user_name": "Job Seeker",  # fallback name
                "jobs": jobs,
                "more_jobs_link": f"https://jobfinders.site/jobs/{category}"
            }

            email_html = render_template("email/job_alert.html", **context)
            subject = f"New {category.title()} Jobs Available on JobFinders.site"

            msg = EmailModel(
                subject_=subject,
                to_=notification.email,
                html_=email_html
            )

            self.logger.info(f"Job Alert Email sent to: {notification.email} | Category: {category}")
            await send_mail.send_mail_resend(email=msg)

        except Exception as e:
            self.logger.error(f"Failed to send job alert email to {notification.email}: {e}")

    async def job_alert_daemon(self):
        """
        Runs a background loop that sends job alerts periodically based on user preferences.
        Operates on +2 Pretoria timezone (use system time, assumed to be in +2 or handled externally).
        """
        from src.main import scrapper
        while True:
            try:
                self.logger.info(f"[{datetime.now()}] Job Alert Daemon running...")

                with self.get_session() as session:
                    verified_notifications = session.query(NotificationsORM).filter(
                        NotificationsORM.is_verified == True
                    ).all()

                if not verified_notifications:
                    self.logger.info("No verified users found for job alerts.")
                else:
                    for n in verified_notifications:
                        topic = n.topic

                        # Grab up to 5 jobs matching user's topic
                        jobs = [
                                   {
                                       "title": job.title,
                                       "company": job.company_name,
                                       "location": job.location,
                                       "link": url_for('home.job_detail', reference=job.reference, _external=True)
                                   }
                                   for job in scrapper.jobs.values()
                                   if job.search_term.casefold() == topic.casefold()
                               ][:5]

                        if not jobs:
                            self.logger.info(f"No matching jobs for topic '{topic}'")
                            continue

                        notification_model = Notifications(
                            email=n.email,
                            topic=n.topic,
                            verification_id=n.verification_id
                        )

                        await self.send_job_alert_email(
                            notification=notification_model,
                            jobs=jobs,
                            category=topic
                        )

                self.logger.info("Job Alert Daemon sleeping for 6 hours.")
                await asyncio.sleep(6 * 60 * 60)  # Wait 6 hours

            except Exception as e:
                self.logger.error(f"Job Alert Daemon encountered an error: {e}")
                self.logger.info("Retrying in 10 minutes...")
                await asyncio.sleep(10 * 60)  # Wait 10 minutes before retrying
