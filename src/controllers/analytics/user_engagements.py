import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template
from sqlalchemy import exists

from src.database.sql.company import CompanyFollowingORM, CompanyORM
from src.controllers.controller import Controllers, error_handler
from src.database.models.jobs_model import Job, JobApplication, JobApplicationStatusEnum
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.sql.analytics import (UserSearchActivityORM, JobViewActivityORM, ApplicationStepORM,
                                        RedisActivityClient, ActivityProcessor)
from src.database.sql.jobs_sql import JobApplicationORM, SavedJobORM, JobsORM
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.emailer import EmailModel
from src.utils.route_helpers import get_service, get_controller


class UserEngagementController(Controllers):
    """
    to improve user Engagement this class will
        1. create job alerts - for matching jobs.
        2. will send application status updates for applied jobs.
        3. send emails informing employers and jobseekers of coming deadlines.
        4. send updates in case jobseekers are following certain companies.
    """
    def __init__(self, factory):
        super().__init__(factory)
        self.redis = RedisActivityClient()
        self.processor = ActivityProcessor(get_session=self.get_session,redis_client=self.redis)

    def init_app(self, app: Flask):
        super().init_app(app=app)
        self.processor.run()

    @staticmethod
    async def _send_alert(email: EmailModel):
        """
        :param email:
        :return:
        """
        await get_service('send_mail')().send_mail_resend(email=email)

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
                'salary': await self._format_salary(job),
                'description': job.description[:200] + '...' if job.description else "",
                'url': job.application_url,
                'deadline': job.application_deadline.strftime('%Y-%m-%d') if job.application_deadline else "ASAP"
            } for job in matching_jobs if job.is_active]
            context = dict(first_name=profile.first_name, jobs=job_data, count=len(job_data))
            return render_template('jobseekers/email/job_alert.html', **context)

    @staticmethod
    async def _format_salary(job: Job) -> str:
        """Helper for salary formatting"""
        if job.salary_confidential:
            return "Competitive Salary"
        if job.salary_min and job.salary_max:
            return f"{job.salary_currency} {job.salary_min:,.0f} - {job.salary_max:,.0f}"
        return "Salary Not Disclosed"
    
    @error_handler
    async def send_job_alert_notifications(self) -> dict:
        """
        # TODO - remove from here Moved to Services
        Send personalized job alerts in batches of 50
        Returns status dictionary with success/failure counts
        """
        results = {'success': 0, 'failures': 0}

        with self.get_session() as session:
            profiles = session.query(JobSeekerProfileORM).filter_by(alerts_enabled=True).all()

            for i in range(0, len(profiles), 50):
                # Sending Job Alerts 50 Profiles at a time.
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

            jobs_search_controller = get_controller("jobs_search")
            jobs = await jobs_search_controller.get_personalized_job_recommendations(profile.user_id)

            if not jobs:
                return None

            html = await self._compose_matching_jobs_email_body(jobs, profile)
            email = EmailModel(
                to_=profile.email,
                subject_=f"👋 {profile.first_name.title()}, {len(jobs)} New Job Matches - on Jobfinders.site waiting for you!",
                html_=html)
            await self._send_alert(email)
            return True

        except Exception as e:
            self.logger.error(f"Failed profile {profile_orm.user_uid}: {str(e)}")
            return e

    @error_handler
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
    
    @error_handler
    async def _process_status_update(self, application_orm: JobApplicationORM):
        """Process individual status update"""
        try:
            job_seeker_profile_controller = get_controller('job_seeker_profile')
            job_search_controller = get_controller('jobs_search')
            job_application = JobApplication(**application_orm.to_dict())
            user_profile = await job_seeker_profile_controller.get_profile_by_uid(user_uid=job_application.user_id)

            if not job_application.job:
                job_application.job = await job_search_controller.get_job_by_id(job_id=job_application.job_id)

            email_content = await self._compose_status_email(
                job_application,
                user_profile
            )

            await self._send_alert(email_content)
            return True

        except Exception as e:
            self.logger.error(f"Status update failed for {application_orm.application_id}: {str(e)}")
            return e
    
    @error_handler
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

    # noinspection DuplicatedCode
    @error_handler
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
                tasks = [await self._process_user_reminders(user) for user in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                results['sent'] += sum(1 for res in batch_results if not isinstance(res, Exception))
                results['errors'] += sum(1 for res in batch_results if isinstance(res, Exception))

                session.commit()
                await asyncio.sleep(1)

        return results

    @error_handler
    async def _process_user_reminders(self, user_profile_orm: JobSeekerProfileORM):
        """Process reminders for a single user"""
        try:
            with self.get_session() as session:
                # Get pending deadlines

                # 1. Saved Jobs without applications
                saved_jobs = session.query(SavedJobORM).filter(
                    SavedJobORM.user_id == user_profile_orm.user_uid,
                    ~exists().where(JobApplicationORM.job_id == SavedJobORM.job_id)
                ).join(JobsORM).filter(
                    JobsORM.application_deadline >= datetime.now(timezone.utc),
                    JobsORM.application_deadline <= await self._reminder_cutoff(user_profile_orm)
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
                    JobsORM.application_deadline <= await self._reminder_cutoff(user_profile_orm)
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

    @staticmethod
    async def _reminder_cutoff(profile: JobSeekerProfileORM) -> datetime:
        """Calculate deadline cutoff date based on user preference"""
        return datetime.now(timezone.utc) + timedelta(days=profile.reminder_days_before)

    
    @error_handler
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
                html_=html_content)

    # noinspection DuplicatedCode
    @error_handler
    async def send_company_updates(self) -> dict:
        """Notify users about new jobs from followed companies"""
        results = {'sent': 0, 'errors': 0}

        with self.get_session() as session:
            # Get all users who want company updates
            users = session.query(JobSeekerProfileORM).filter(
                JobSeekerProfileORM.receive_company_updates == True
            ).all()

            for i in range(0, len(users), 50):
                batch = users[i:i + 50]
                tasks = [self._process_company_updates(user) for user in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                results['sent'] += sum(1 for res in batch_results if not isinstance(res, Exception))
                results['errors'] += sum(1 for res in batch_results if isinstance(res, Exception))

                session.commit()
                await asyncio.sleep(1)

        return results

    async def _process_company_updates(self, user_profile: JobSeekerProfileORM):
        """Process company updates for a single user"""
        try:
            with self.get_session() as session:
                # Get followed companies with new jobs
                updates = session.query(CompanyFollowingORM).filter(
                    CompanyFollowingORM.user_id == user_profile.user_uid,
                    CompanyFollowingORM.last_notified_at < JobsORM.posted_at
                ).join(CompanyORM).join(JobsORM).filter(
                    JobsORM.posted_at >= datetime.now(timezone.utc) - timedelta(days=1)  # Daily digest
                ).all()

                if not updates:
                    return None

                # Group jobs by company
                company_jobs = defaultdict(list)
                for follow in updates:
                    jobs = session.query(JobsORM).filter(
                        JobsORM.company_id == follow.company_id,
                        JobsORM.posted_at > follow.last_notified_at
                    ).limit(10).all()
                    company_jobs[follow.company] = jobs
                    follow.last_notified_at = datetime.now(timezone.utc)

                # Compose and send email
                email = await self._compose_company_update_email(
                    profile=JobSeekerProfile(**user_profile.to_dict()),
                    company_jobs=company_jobs
                )
                await self._send_alert(email)
                return True

        except Exception as e:
            self.logger.error(f"Company updates failed for {user_profile.user_uid}: {str(e)}")
            return e

    async def _compose_company_update_email(self, profile: JobSeekerProfile,
                                            company_jobs: dict[CompanyORM, list[JobsORM]]) -> EmailModel:
        """Create company update email"""
        with self.app.app_context():

            context= dict(
                user=profile,
                companies=company_jobs,
                utcnow=datetime.now(timezone.utc)
            )

            html_content = render_template('jobseekers/email/company_updates.html', **context)
            return EmailModel(
                to_=profile.email,
                subject_=f"🏢 New Jobs from Companies You Follow",
                html_=html_content
            )

    # ANALYTICS -------------------------------------------------------------------------------------------
    @error_handler
    async def log_search(self, user_id: str, search_term: str, filters: dict, result_count: int):
        """Log search activity to Redis"""
        self.redis.log_activity('search', {
            'user_id': user_id,
            'search_term': search_term[:255],
            'filters': json.dumps(filters),
            'result_count': result_count
        })

    
    @error_handler
    async def log_view(self, user_id: str, job_id: str, duration: int, application_started: bool):
        """Log job view activity"""
        self.redis.log_activity('view', {
            'user_id': user_id,
            'job_id': job_id,
            'view_start': (datetime.now(timezone.utc) - timedelta(seconds=duration)).isoformat(),
            'view_end': datetime.now(timezone.utc).isoformat(),
            'duration': duration,
            'application_started': application_started
        })

    @error_handler
    async def log_application_step(self, application_id: str, step_name: str):
        """Log Application progress step"""
        self.redis.log_activity('step', {
            'application_id': application_id,
            'step_name': step_name,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @error_handler
    async def track_job_search_activity(self, user_id: str) -> dict:
        """
        use this endpoint in the admin dashboard to track user search terms
        Get job search metrics with Redis caching

        to log views use the following
            '''python
                        # Log a search
                controller.log_search(
                    user_id=current_user.id,
                    search_term="Python Developer",
                    filters={"remote": True, "salary_min": 50000},
                    result_count=42
                )

                # Log a job view
                controller.log_view(
                    user_id=current_user.id,
                    job_id=job.id,
                    duration=45,  # seconds
                    application_started=True
                )
            '''

        """
        if cached := self.redis.get_cached_metrics(user_id):
            return cached

        metrics = await self._calculate_metrics(user_id)
        self.redis.cache_metrics(user_id, metrics)
        return metrics

    async def _calculate_metrics(self, user_id: str) -> dict:
        """Calculate search metrics from MySQL data"""
        with self.get_session() as session:
            return {
                'searches': await self._search_metrics(session, user_id),
                'views': await self._view_metrics(session, user_id),
                'applications': await self._application_metrics(session, user_id)
            }

    async def _search_metrics(self, session, user_id: str):
        """Calculate search-related metrics"""
        searches = session.query(UserSearchActivityORM).filter(
            UserSearchActivityORM.user_id == user_id
        ).order_by(UserSearchActivityORM.timestamp.desc()).limit(1000).all()

        return {
            'total': len(searches),
            'common_terms': await self._frequency_count([s.search_term for s in searches]),
            'popular_filters': await self._frequency_count(
                [list(json.loads(s.filters).keys() for s in searches if s.filters)]
            ),
            'avg_results': sum(s.result_count for s in searches) / len(searches) if searches else 0
        }

    @staticmethod
    async def _view_metrics(session, user_id: str):
        """Calculate view-related metrics"""
        views = session.query(JobViewActivityORM).filter(
            JobViewActivityORM.user_id == user_id
        ).limit(1000).all()

        return {
            'total': len(views),
            'avg_duration': sum(v.duration for v in views) / len(views) if views else 0,
            'application_rate': sum(1 for v in views if v.application_started) / len(views) if views else 0
        }

    async def _application_metrics(self, session, user_id: str):
        """Calculate application-related metrics"""
        apps = session.query(JobApplicationORM).filter(
            JobApplicationORM.user_id == user_id
        ).all()

        steps = session.query(ApplicationStepORM).filter(
            ApplicationStepORM.application_id.in_([a.application_id for a in apps])
        ).all()

        return {
            'total': len(apps),
            'completion_rate': sum(1 for a in apps if a.application_stage == 'SUBMITTED') / len(
                apps) if apps else 0,
            'dropoff_points': await self._frequency_count(
                [s.step_name for s in steps if s.step_name != 'SUBMITTED']
            )
        }

    @staticmethod
    async def _frequency_count(items: list) -> dict:
        counts = defaultdict(int)
        for item in items:
            if isinstance(item, list):
                for subitem in item:
                    counts[subitem] += 1
            else:
                counts[item] += 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))



