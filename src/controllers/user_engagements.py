import asyncio
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template
from sqlalchemy import exists

from src.database.models.jobs_model import Job, JobApplication, JobApplicationStatusEnum
from src.database.sql.jobs_sql import JobApplicationORM, SavedJobORM, JobsORM
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.emailer import EmailModel
from src.controllers.controller import Controllers
from src.main import jobs_controller, send_mail, job_seeker_profile_controller


class UserEngagementController(Controllers):
    """
    to improve user engagement this class will
        1. create job alerts - for matching jobs.
        2. will send application status updates for applied jobs.
        3. send emails informing employers and jobseekers of coming deadlines.
        4. send updates in case jobseekers are following certain companies.
    """
    def __init__(self):
        super().__init__()

    def init_app(self, app: Flask):
        super().init_app(app=app)

    async def _send_alert(self, email: EmailModel):
        """

        :param email:
        :return:
        """
        await send_mail.send_mail_resend(email=email)

    async def _compose_matching_jobs_email_body(self, matching_jobs: list[Job], profile: JobSeekerProfile) -> str:
        """
        Generate HTML email body using template and job data
        """
        with self.app.app_context():
            job_data = [{
                'title': job.title,
                'company': job.company.name if job.company else "Confidential",
                'location': job.location,
                'type': job.position_type.replace('_', ' ').title(),
                'remote': job.remote_policy.title(),
                'salary': self._format_salary(job),
                'description': job.description[:200] + '...' if job.description else "",
                'url': job.application_url,
                'deadline': job.application_deadline.strftime('%Y-%m-%d') if job.application_deadline else "ASAP"
            } for job in matching_jobs if job.is_active]
            context = dict(first_name=profile.first_name, jobs=job_data, count=len(job_data))
            return render_template('jobseekers/email/job_alert.html', **context)

    @staticmethod
    def _format_salary(job: Job) -> str:
        """Helper for salary formatting"""
        if job.salary_confidential:
            return "Competitive Salary"
        if job.salary_min and job.salary_max:
            return f"{job.salary_currency} {job.salary_min:,.0f} - {job.salary_max:,.0f}"
        return "Salary Not Disclosed"

    async def send_job_alert_notifications(self) -> dict:
        """
        Send personalized job alerts in batches of 50
        Returns status dictionary with success/failure counts
        """
        results = {'success': 0, 'failures': 0}

        with self.get_session() as session:
            profiles = session.query(JobSeekerProfileORM).filter_by(alerts_enabled=True).all()

            for i in range(0, len(profiles), 50):
                batch = profiles[i:i + 50]
                tasks = [self._process_user_profile(p) for p in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for res in batch_results:
                    if isinstance(res, Exception):
                        results['failures'] += 1
                    else:
                        results['success'] += 1

                await asyncio.sleep(1)  # Rate limiting

        return results

    async def _process_user_profile(self, profile_orm: JobSeekerProfileORM):
        """Process individual user profile"""
        try:
            profile = JobSeekerProfile(**profile_orm.to_dict())
            # TODO - consider integrating the alerts with the Job Match Scores
            jobs = await jobs_controller.get_personalized_job_recommendations(profile.user_id)

            if not jobs:
                return None

            html = await self._compose_matching_jobs_email_body(jobs, profile)
            email = EmailModel(
                to_=profile.email,
                subject_=f"👋 {profile.first_name.title()}, {len(jobs)} New Job Matches - on Jobfinders.site waiting for you!",
                html_=html
            )
            await self._send_alert(email)
            return True

        except Exception as e:
            self.logger.error(f"Failed profile {profile_orm.user_uid}: {str(e)}")
            return e


    async def send_application_status_updates(self) -> dict:
        """
        Notify users about changes in their job application statuses
        Returns dictionary with success/failure counts
        """
        results = {'success': 0, 'failures': 0}

        with self.get_session() as session:
            # Get applications with status changes since last update
            applications_orm_list = session.query(JobApplicationORM).filter(
                JobApplicationORM.application_stage != JobApplicationORM.last_application_stage
            ).all()

            for i in range(0, len(applications_orm_list), 50):
                batch = applications_orm_list[i:i + 50]
                tasks = [self._process_status_update(app) for app in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for app, res in zip(batch, batch_results):
                    if isinstance(res, Exception):
                        results['failures'] += 1
                    else:
                        results['success'] += 1
                        # Update last known status after successful notification
                        app.last_application_stage = app.application_stage
                        session.add(app)

                session.commit()
                await asyncio.sleep(1)

        return results

    async def _process_status_update(self, application_orm: JobApplicationORM):
        """Process individual status update"""
        try:
            job_application = JobApplication(**application_orm.to_dict())
            user_profile = await job_seeker_profile_controller.get_profile_by_uid(user_id=job_application.user_id)

            if not job_application.job:
                job_application.job = await jobs_controller.get_job_by_id(job_id=job_application.job_id)

            email_content = await self._compose_status_email(
                job_application,
                user_profile
            )

            await self._send_alert(email_content)
            return True

        except Exception as e:
            self.logger.error(f"Status update failed for {application_orm.application_id}: {str(e)}")
            return e

    async def _compose_status_email(self, application: JobApplication, profile: JobSeekerProfile) -> EmailModel:
        """Create status update email using template"""
        with self.app.app_context():
            context = {
                'user': profile,
                'job': application.job,
                'old_status': application.last_application_stage,
                'new_status': application.application_stage,
                'update_date': application.updated_at.strftime('%Y-%m-%d %H:%M'),
                'notes': application.review_summary
            }

            html_content = render_template('jobseekers/email/job_status_alert.html', **context)

        return EmailModel(
            to_=profile.email,
            subject_=f"📢 Job Application Update: {application.job.title} - Jobfinders.site",
            html_=html_content
        )


    async def send_deadline_reminders(self) -> dict:
        """
        Send deadline reminders for:
        - Saved jobs with approaching deadlines
        - Applications nearing expiration
        """
        results = {'sent': 0, 'errors': 0}

        with self.get_session() as session:
            # Get users who want reminders
            users = session.query(JobSeekerProfileORM).filter(
                JobSeekerProfileORM.receive_deadline_reminders == True
            ).all()

            for i in range(0, len(users), 50):
                batch = users[i:i + 50]
                tasks = [self._process_user_reminders(user) for user in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                results['sent'] += sum(1 for res in batch_results if not isinstance(res, Exception))
                results['errors'] += sum(1 for res in batch_results if isinstance(res, Exception))

                session.commit()
                await asyncio.sleep(1)

        return results

    async def _process_user_reminders(self, user_profile_orm: JobSeekerProfileORM):
        """Process reminders for a single user"""
        try:
            with self.get_session() as session:
                # Get pending deadlines
                reminders = []

                # 1. Saved Jobs without applications
                saved_jobs = session.query(SavedJobORM).filter(
                    SavedJobORM.user_id == user_profile_orm.user_uid,
                    ~exists().where(JobApplicationORM.job_id == SavedJobORM.job_id)
                ).join(JobsORM).filter(
                    JobsORM.application_deadline >= datetime.now(timezone.utc),
                    JobsORM.application_deadline <= self._reminder_cutoff(user_profile_orm)
                ).all()

                # 2. Applications in progress
                applications = session.query(JobApplicationORM).filter(
                    JobApplicationORM.user_id == user_profile_orm.user_uid,
                    JobApplicationORM.application_stage.in_([
                        JobApplicationStatusEnum.APPLIED.value,
                        JobApplicationStatusEnum.UNDER_REVIEW.value,
                        JobApplicationStatusEnum.INTERVIEWING.value
                    ]),
                    JobsORM.application_deadline >= datetime.now(timezone.utc),
                    JobsORM.application_deadline <= self._reminder_cutoff(user_profile_orm)
                ).join(JobsORM).all()

                # Combine and deduplicate
                all_jobs = {(sj.job_id, sj.job) for sj in saved_jobs}
                all_jobs.update({(app.job_id, app.job) for app in applications})

                if not all_jobs:
                    return None

                # Send reminder
                email = await self._compose_deadline_email(
                    user_profile=JobSeekerProfile(**user_profile_orm.to_dict()),
                    jobs=[job for _, job in all_jobs]
                )
                await self._send_alert(email)
                user_profile_orm.last_reminded_at = datetime.now(timezone.utc)

                return True

        except Exception as e:
            self.logger.error(f"Reminder failed for {user_profile_orm.user_uid}: {str(e)}")
            return e

    def _reminder_cutoff(self, profile: JobSeekerProfileORM) -> datetime:
        """Calculate deadline cutoff date based on user preference"""
        return datetime.now(timezone.utc) + timedelta(days=profile.reminder_days_before)


    async def _compose_deadline_email(self, user_profile: JobSeekerProfile, jobs: list[Job]) -> EmailModel:
        """Create deadline reminder email"""
        with self.app.app_context():
            context = dict(
                user=user_profile,
                jobs=jobs,
                utcnow=datetime.now(timezone.utc)
            )
            html_content = render_template('jobseekers/email/deadline_reminder.html', **context)

            return EmailModel(
                to_=user_profile.email,
                subject_=f"⏳ {len(jobs)} Upcoming Job Deadlines - Jobfinders.site",
                html_=html_content
            )
