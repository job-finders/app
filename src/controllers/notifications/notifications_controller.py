
from src.controllers.controller import Controllers, error_handler
from src.emailer import EmailModel
from src.utils.route_helpers import get_service
from flask import render_template
from datetime import datetime


class NotificationsController(Controllers):

    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app):
        super().init_app(app)
    
    @error_handler
    async def send_application_submission_notification(self, application_data: dict, user_email: str, user_name: str):
        """
        Send application submission confirmation email to job seeker
        
        Args:
            application_data: Dictionary containing application details
            user_email: Job seeker's email address
            user_name: Job seeker's name
        """
        try:
            with self.app.app_context():
                context = {
                    'user_name': user_name,
                    'job_title': application_data.get('job_title', 'Unknown Position'),
                    'company_name': application_data.get('company_name', 'Unknown Company'),
                    'application_id': application_data.get('application_id'),
                    'submission_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                    'next_steps': [
                        'Your application is being reviewed by the employer',
                        'You will receive updates on your application status',
                        'You can track your application progress in your dashboard'
                    ]
                }
                
                email_html = render_template("email/application_submission_confirmation.html", **context)
                subject = f"Application Submitted: {application_data.get('job_title', 'Job Position')} - JobFinders"
                
                email = EmailModel(
                    subject_=subject,
                    to_=user_email,
                    html_=email_html
                )
                
                self.logger.info(f"Application submission confirmation sent to: {user_email}")
                await get_service('send_mail')().send_mail_resend(email=email)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to send application submission notification: {e}")
            return False
    
    @error_handler
    async def send_new_application_notification(self, application_data: dict, employer_email: str, employer_name: str):
        """
        Send new application notification email to employer
        
        Args:
            application_data: Dictionary containing application details
            employer_email: Employer's email address
            employer_name: Employer's name
        """
        try:
            with self.app.app_context():
                context = {
                    'employer_name': employer_name,
                    'applicant_name': application_data.get('applicant_name', 'Anonymous Applicant'),
                    'job_title': application_data.get('job_title', 'Unknown Position'),
                    'application_id': application_data.get('application_id'),
                    'submission_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                    'match_score': application_data.get('match_score'),
                    'application_url': f"/employers/applications/{application_data.get('application_id')}",
                    'dashboard_url': "/employers/applications/dashboard"
                }
                
                email_html = render_template("email/new_application_notification.html", **context)
                subject = f"New Application: {application_data.get('job_title', 'Job Position')} - JobFinders"
                
                email = EmailModel(
                    subject_=subject,
                    to_=employer_email,
                    html_=email_html
                )
                
                self.logger.info(f"New application notification sent to employer: {employer_email}")
                await get_service('send_mail')().send_mail_resend(email=email)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to send new application notification: {e}")
            return False
    
    @error_handler
    async def send_application_status_update(self, application_data: dict, user_email: str, user_name: str, new_status: str):
        """
        Send application status update notification to job seeker
        
        Args:
            application_data: Dictionary containing application details
            user_email: Job seeker's email address
            user_name: Job seeker's name
            new_status: New application status
        """
        try:
            status_messages = {
                'reviewing': 'Your application is now under review',
                'shortlisted': 'Congratulations! You have been shortlisted',
                'interviewed': 'Interview scheduled - check your dashboard for details',
                'hired': 'Congratulations! You have been selected for the position',
                'rejected': 'Thank you for your interest. Unfortunately, we have decided to move forward with other candidates'
            }
            
            with self.app.app_context():
                context = {
                    'user_name': user_name,
                    'job_title': application_data.get('job_title', 'Unknown Position'),
                    'company_name': application_data.get('company_name', 'Unknown Company'),
                    'application_id': application_data.get('application_id'),
                    'new_status': new_status.title(),
                    'status_message': status_messages.get(new_status, 'Your application status has been updated'),
                    'update_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                    'application_url': f"/applications/{application_data.get('application_id')}"
                }
                
                email_html = render_template("email/application_status_update.html", **context)
                subject = f"Application Update: {application_data.get('job_title', 'Job Position')} - JobFinders"
                
                email = EmailModel(
                    subject_=subject,
                    to_=user_email,
                    html_=email_html
                )
                
                self.logger.info(f"Application status update sent to: {user_email} - Status: {new_status}")
                await get_service('send_mail')().send_mail_resend(email=email)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to send application status update: {e}")
            return False

    # async def create_notification_email(self, notification: Notifications):
    #     try:
    #         with self.get_session() as session:
    #             notification_orm_ = session.query(NotificationsORM).filter(NotificationsORM.email == notification.email).first()
    #             if notification_orm_:
    #                 return None
    #             notification_orm = NotificationsORM(**notification.dict())
    #
    #             session.add(notification_orm)
    #             session.commit()
    #
    #             return notification
    #     except OperationalError as e:
    #         self.logger.info("Operational Error on create_notification_email")
    #
    # @staticmethod
    # def generate_verification_link(notification):
    #     return url_for('home.verify_email', _external=True, verification_id=notification.verification_id, email=notification.email)
    #
    # async def send_notification_verification_email(self, notification):
    #     link_with_params = self.generate_verification_link(notification)
    #     context = {'verification_link': link_with_params}
    #     email_html = render_template("email/welcome.html", **context)
    #     subject = "JobFinders.site Job Alert - Email Verification"
    #     msg = EmailModel(subject_=subject, to_=notification.email, html_=email_html)
    #     self.logger.info(f"Welcome Email Sent to: {notification.email}")
    #     await get_service('send_mail').send_mail_resend(email=msg)
    #
    # async def check_verification(self, verification_id: str, email: str) -> bool:
    #     with self.get_session() as session:
    #         notification_orm: NotificationsORM = session.query(NotificationsORM).filter(
    #             NotificationsORM.email == email).first()
    #         if notification_orm and notification_orm.verification_id == verification_id:
    #             notification_orm.is_verified = True
    #             session.commit()
    #
    #         return notification_orm and notification_orm.verification_id == verification_id
    #
    #
    # async def send_job_alert_email(self, notification: Notifications, jobs: list, category: str):
    #     """
    #     Send a job alert email with a list of job postings.
    #
    #     :param notification: Notifications instance with user details.
    #     :param jobs: List of dicts with keys: title, company, location, link
    #     :param category: Category of the job alert, e.g., "nursing"
    #     """
    #     try:
    #         context = {
    #             "user_name": "Job Seeker",  # fallback name
    #             "jobs": jobs,
    #             "more_jobs_link": f"https://jobfinders.site/jobs/{category}"
    #         }
    #
    #         email_html = render_template("email/job_alert.html", **context)
    #         subject = f"New {category.title()} Jobs Available on JobFinders.site"
    #
    #         msg = EmailModel(
    #             subject_=subject,
    #             to_=notification.email,
    #             html_=email_html
    #         )
    #
    #         self.logger.info(f"Job Alert Email sent to: {notification.email} | Category: {category}")
    #         await get_service('send_mail').send_mail_resend(email=msg)
    #
    #     except Exception as e:
    #         self.logger.error(f"Failed to send job alert email to {notification.email}: {e}")
    #
    # async def job_alert_daemon(self):
    #     """
    #     Runs a background loop that sends job alerts periodically based on user preferences.
    #     Operates on +2 Pretoria timezone (use system time, assumed to be in +2 or handled externally).
    #     """
    #
    #     while True:
    #         try:
    #             self.logger.info(f"[{datetime.now()}] Job Alert Daemon running...")
    #
    #             with self.get_session() as session:
    #                 verified_notifications = session.query(NotificationsORM).filter(
    #                     NotificationsORM.is_verified == True
    #                 ).all()
    #
    #             if not verified_notifications:
    #                 self.logger.info("No verified users found for job alerts.")
    #             else:
    #                 for n in verified_notifications:
    #                     topic = n.topic
    #
    #                     # Grab up to 5 jobs matching user's topic
    #                     jobs = [
    #                                {
    #                                    "title": job.title,
    #                                    "company": job.company_name,
    #                                    "location": job.location,
    #                                    "link": url_for('home.job_detail', reference=job.reference, _external=True)
    #                                }
    #                                for job in get_service('scraper').jobs_cache.values()
    #                                if job.search_term.casefold() == topic.casefold()
    #                            ][:5]
    #
    #                     if not jobs:
    #                         self.logger.info(f"No matching jobs for topic '{topic}'")
    #                         continue
    #
    #                     notification_model = Notifications(
    #                         email=n.email,
    #                         topic=n.topic,
    #                         verification_id=n.verification_id
    #                     )
    #
    #                     await self.send_job_alert_email(
    #                         notification=notification_model,
    #                         jobs=jobs,
    #                         category=topic
    #                     )
    #
    #             self.logger.info("Job Alert Daemon sleeping for 6 hours.")
    #             await asyncio.sleep(6 * 60 * 60)  # Wait 6 hours
    #
    #         except Exception as e:
    #             self.logger.error(f"Job Alert Daemon encountered an error: {e}")
    #             self.logger.info("Retrying in 10 minutes...")
    #             await asyncio.sleep(10 * 60)  # Wait 10 minutes before retrying
