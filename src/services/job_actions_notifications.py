"""
Job Actions Notification Service

Handles notifications related to job actions, specifically:
- Saved job status changes (job closed, expired, updated)
- Job application deadlines
- Company updates for saved jobs
- Job matching notifications
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

from src.database.models.notifications import (
    BaseNotification, NotificationChannel, NotificationType, NotificationPayload
)
from src.database.models import Job, JobSeekerProfile, Company
from src.database import (
    SavedJobORM, JobsORM, JobSeekerProfileORM, CompanyORM, NotificationsORM
)
from src.database.constants import utc_time
from src.controllers.controller import Controllers
from src.logger import init_logger


class JobActionNotificationType(str, Enum):
    """Extended notification types for job actions"""
    SAVED_JOB_CLOSED = "saved_job_closed"
    SAVED_JOB_EXPIRED = "saved_job_expired"
    SAVED_JOB_UPDATED = "saved_job_updated"
    SAVED_JOB_DEADLINE_REMINDER = "saved_job_deadline_reminder"
    COMPANY_NEW_JOB = "company_new_job"
    COMPANY_PROFILE_UPDATED = "company_profile_updated"


class JobActionsNotificationService(Controllers):
    """Service for managing job actions related notifications"""

    def __init__(self, factory):
        super().__init__(factory)
        self.logger = init_logger(self.__class__.__name__)

        # Notification preferences
        self.notification_settings = {
            'deadline_reminder_days': [7, 3, 1],  # Days before deadline to send reminders
            'batch_size': 100,  # Number of notifications to process at once
            'retry_attempts': 3,  # Number of retry attempts for failed notifications
        }

    async def notify_saved_job_status_change(self, job_id: str, status_change: str,
                                             additional_data: Dict[str, Any] = None) -> None:
        """
        Notify users who saved a job about status changes
        
        Args:
            job_id: ID of the job that changed
            status_change: Type of change (closed, expired, updated)
            additional_data: Additional context about the change
        """
        with self.get_session() as session:
            try:
                # Get job details
                job_orm = session.query(JobsORM).filter_by(job_id=job_id).first()
                if not job_orm:
                    self.logger.warning(f"Job {job_id} not found for status change notification")
                    return

                job = Job(**job_orm.to_dict())

                # Get all users who saved this job
                saved_jobs = (
                    session.query(SavedJobORM)
                    .options(joinedload(SavedJobORM.jobseeker_profile))
                    .filter_by(job_id=job_id)
                    .all()
                )

                if not saved_jobs:
                    self.logger.info(f"No saved jobs found for job {job_id}")
                    return

                # Create notifications for each user
                notifications = []
                for saved_job in saved_jobs:
                    if not saved_job.jobseeker_profile:
                        continue

                    # Check user notification preferences
                    if not self._should_send_notification(
                            saved_job.jobseeker_profile, status_change
                    ):
                        continue

                    notification = await self._create_job_status_notification(
                        saved_job.jobseeker_profile, job, status_change, additional_data
                    )

                    if notification:
                        notifications.append(notification)

                # Send notifications in batches
                if notifications:
                    await self._send_notifications_batch(notifications)
                    self.logger.info(
                        f"Sent {len(notifications)} notifications for job {job_id} "
                        f"status change: {status_change}"
                    )

            except Exception as e:
                self.logger.error(f"Error sending job status change notifications: {e}")

    async def notify_application_deadline_reminder(self, days_before: int = 7) -> None:
        """
        Send deadline reminders for saved jobs
        
        Args:
            days_before: Number of days before deadline to send reminder
        """
        with self.get_session() as session:
            try:
                # Calculate target date
                target_date = utc_time() + timedelta(days=days_before)

                # Find jobs with deadlines approaching
                jobs_with_deadlines = (
                    session.query(JobsORM)
                    .filter(
                        JobsORM.application_deadline.isnot(None),
                        JobsORM.application_deadline <= target_date,
                        JobsORM.application_deadline > utc_time(),
                        JobsORM.status == 'active'
                    )
                    .all()
                )

                notifications = []

                for job_orm in jobs_with_deadlines:
                    job = Job(**job_orm.to_dict())

                    # Get users who saved this job
                    saved_jobs = (
                        session.query(SavedJobORM)
                        .options(joinedload(SavedJobORM.jobseeker_profile))
                        .filter_by(job_id=job.job_id)
                        .all()
                    )

                    for saved_job in saved_jobs:
                        if not saved_job.jobseeker_profile:
                            continue

                        # Check if user wants deadline reminders
                        if not saved_job.jobseeker_profile.receive_deadline_reminders:
                            continue

                        # Check if we already sent a reminder for this deadline
                        if self._already_sent_deadline_reminder(
                                saved_job.jobseeker_profile.user_uid, job.job_id, days_before
                        ):
                            continue

                        notification = await self._create_deadline_reminder_notification(
                            saved_job.jobseeker_profile, job, days_before
                        )

                        if notification:
                            notifications.append(notification)

                # Send notifications
                if notifications:
                    await self._send_notifications_batch(notifications)
                    self.logger.info(
                        f"Sent {len(notifications)} deadline reminder notifications "
                        f"for {days_before} days before deadline"
                    )

            except Exception as e:
                self.logger.error(f"Error sending deadline reminders: {e}")

    async def notify_company_updates(self, company_id: str, update_type: str,
                                     update_data: Dict[str, Any] = None) -> None:
        """
        Notify users about company updates for companies they follow or have saved jobs from
        
        Args:
            company_id: ID of the company that was updated
            update_type: Type of update (new_job, profile_updated)
            update_data: Additional data about the update
        """
        with self.get_session() as session:
            try:
                # Get company details
                company_orm = session.query(CompanyORM).filter_by(company_id=company_id).first()
                if not company_orm:
                    self.logger.warning(f"Company {company_id} not found for update notification")
                    return

                company = Company(**company_orm.to_dict())

                # Get users who have saved jobs from this company
                users_to_notify = set()

                # Users with saved jobs from this company
                saved_jobs = (
                    session.query(SavedJobORM)
                    .join(JobsORM, SavedJobORM.job_id == JobsORM.job_id)
                    .options(joinedload(SavedJobORM.jobseeker_profile))
                    .filter(JobsORM.company_id == company_id)
                    .all()
                )

                for saved_job in saved_jobs:
                    if (saved_job.jobseeker_profile and
                            saved_job.jobseeker_profile.receive_company_updates):
                        users_to_notify.add(saved_job.jobseeker_profile)

                # Create notifications
                notifications = []
                for user_profile in users_to_notify:
                    notification = await self._create_company_update_notification(
                        user_profile, company, update_type, update_data
                    )

                    if notification:
                        notifications.append(notification)

                # Send notifications
                if notifications:
                    await self._send_notifications_batch(notifications)
                    self.logger.info(
                        f"Sent {len(notifications)} company update notifications "
                        f"for company {company_id}: {update_type}"
                    )

            except Exception as e:
                self.logger.error(f"Error sending company update notifications: {e}")

    async def _create_job_status_notification(self, user_profile: JobSeekerProfileORM,
                                              job: Job, status_change: str,
                                              additional_data: Dict[str, Any] = None) -> Optional[BaseNotification]:
        """Create a job status change notification"""
        try:
            # Determine notification type
            notification_type_map = {
                'closed': JobActionNotificationType.SAVED_JOB_CLOSED,
                'expired': JobActionNotificationType.SAVED_JOB_EXPIRED,
                'updated': JobActionNotificationType.SAVED_JOB_UPDATED,
            }

            notification_type = notification_type_map.get(status_change)
            if not notification_type:
                return None

            # Create email content
            subject, body = self._generate_job_status_email_content(
                user_profile, job, status_change, additional_data
            )

            payload = NotificationPayload(
                subject=subject,
                body=body,
                data={
                    'job_id': job.job_id,
                    'job_title': job.title,
                    'company_name': job.company.name if job.company else 'Unknown Company',
                    'status_change': status_change,
                    'additional_data': additional_data or {}
                }
            )

            return BaseNotification(
                user_id=user_profile.user_uid,
                email=user_profile.email,
                notification_type=notification_type,
                channel=NotificationChannel.email,
                payload=payload
            )

        except Exception as e:
            self.logger.error(f"Error creating job status notification: {e}")
            return None

    async def _create_deadline_reminder_notification(self, user_profile: JobSeekerProfileORM,
                                                     job: Job, days_before: int) -> Optional[BaseNotification]:
        """Create a deadline reminder notification"""
        try:
            subject = f"Application Deadline Reminder: {job.title}"

            deadline_str = job.application_deadline.strftime('%B %d, %Y') if job.application_deadline else 'soon'
            company_name = job.company.name if job.company else 'the company'

            body = f"""
            Hi {user_profile.first_name or 'there'},
            
            This is a friendly reminder that the application deadline for the job you saved is approaching:
            
            Job Title: {job.title}
            Company: {company_name}
            Application Deadline: {deadline_str}
            
            Don't miss out on this opportunity! You can apply directly through our platform.
            
            View Job: [Job Link]
            
            Best regards,
            The Job Finders Team
            """

            payload = NotificationPayload(
                subject=subject,
                body=body.strip(),
                data={
                    'job_id': job.job_id,
                    'job_title': job.title,
                    'company_name': company_name,
                    'deadline': job.application_deadline.isoformat() if job.application_deadline else None,
                    'days_before': days_before
                }
            )

            return BaseNotification(
                user_id=user_profile.user_uid,
                email=user_profile.email,
                notification_type=JobActionNotificationType.SAVED_JOB_DEADLINE_REMINDER,
                channel=NotificationChannel.email,
                payload=payload
            )

        except Exception as e:
            self.logger.error(f"Error creating deadline reminder notification: {e}")
            return None

    async def _create_company_update_notification(self, user_profile: JobSeekerProfileORM,
                                                  company: Company, update_type: str,
                                                  update_data: Dict[str, Any] = None) -> Optional[BaseNotification]:
        """Create a company update notification"""
        try:
            if update_type == 'new_job':
                subject = f"New Job Posted at {company.name}"
                job_title = update_data.get('job_title', 'a new position') if update_data else 'a new position'

                body = f"""
                Hi {user_profile.first_name or 'there'},
                
                Great news! {company.name} has posted a new job that might interest you:
                
                Job Title: {job_title}
                Company: {company.name}
                
                Since you've shown interest in this company by saving their jobs, we thought you'd like to know about this new opportunity.
                
                View Job: [Job Link]
                
                Best regards,
                The Job Finders Team
                """

                notification_type = JobActionNotificationType.COMPANY_NEW_JOB

            elif update_type == 'profile_updated':
                subject = f"Company Update: {company.name}"

                body = f"""
                Hi {user_profile.first_name or 'there'},
                
                {company.name} has updated their company profile. Since you've saved jobs from this company, 
                you might want to check out their latest information.
                
                View Company Profile: [Company Link]
                
                Best regards,
                The Job Finders Team
                """

                notification_type = JobActionNotificationType.COMPANY_PROFILE_UPDATED
            else:
                return None

            payload = NotificationPayload(
                subject=subject,
                body=body.strip(),
                data={
                    'company_id': company.company_id,
                    'company_name': company.name,
                    'update_type': update_type,
                    'update_data': update_data or {}
                }
            )

            return BaseNotification(
                user_id=user_profile.user_uid,
                email=user_profile.email,
                notification_type=notification_type,
                channel=NotificationChannel.email,
                payload=payload
            )

        except Exception as e:
            self.logger.error(f"Error creating company update notification: {e}")
            return None

    def _generate_job_status_email_content(self, user_profile: JobSeekerProfileORM,
                                           job: Job, status_change: str,
                                           additional_data: Dict[str, Any] = None) -> tuple[str, str]:
        """Generate email subject and body for job status changes"""
        company_name = job.company.name if job.company else 'the company'
        user_name = user_profile.first_name or 'there'

        if status_change == 'closed':
            subject = f"Job Closed: {job.title} at {company_name}"
            body = f"""
            Hi {user_name},
            
            We wanted to let you know that a job you saved has been closed:
            
            Job Title: {job.title}
            Company: {company_name}
            
            While this opportunity is no longer available, we encourage you to:
            - Check out other jobs at {company_name}
            - Explore similar positions from other companies
            - Set up job alerts for similar roles
            
            Keep looking - your perfect job is out there!
            
            Best regards,
            The Job Finders Team
            """

        elif status_change == 'expired':
            subject = f"Job Expired: {job.title} at {company_name}"
            body = f"""
            Hi {user_name},
            
            A job you saved has expired:
            
            Job Title: {job.title}
            Company: {company_name}
            
            The application deadline has passed, but don't worry! We have many other opportunities available.
            
            Browse Similar Jobs: [Search Link]
            
            Best regards,
            The Job Finders Team
            """

        elif status_change == 'updated':
            subject = f"Job Updated: {job.title} at {company_name}"
            body = f"""
            Hi {user_name},
            
            Good news! A job you saved has been updated:
            
            Job Title: {job.title}
            Company: {company_name}
            
            The job details may have changed, so we recommend reviewing the updated posting.
            
            View Updated Job: [Job Link]
            
            Best regards,
            The Job Finders Team
            """
        else:
            subject = f"Job Update: {job.title}"
            body = f"Hi {user_name},\n\nA job you saved has been updated.\n\nBest regards,\nThe Job Finders Team"

        return subject, body.strip()

    def _should_send_notification(self, user_profile: JobSeekerProfileORM,
                                  notification_type: str) -> bool:
        """Check if we should send a notification to this user"""
        # Check if user has notifications enabled
        if not user_profile.alerts_enabled:
            return False

        # Check specific notification preferences
        if notification_type in ['closed', 'expired', 'updated']:
            return user_profile.receive_company_updates

        return True

    def _already_sent_deadline_reminder(self, user_id: str, job_id: str,
                                        days_before: int) -> bool:
        """Check if we already sent a deadline reminder for this job and timeframe"""
        with self.get_session() as session:
            try:
                # Check for existing notification
                existing = (
                    session.query(NotificationsORM)
                    .filter_by(
                        user_id=user_id,
                        notification_type=JobActionNotificationType.SAVED_JOB_DEADLINE_REMINDER
                    )
                    .filter(NotificationsORM.payload.contains(f'"job_id": "{job_id}"'))
                    .filter(NotificationsORM.payload.contains(f'"days_before": {days_before}'))
                    .first()
                )

                return existing is not None

            except Exception as e:
                self.logger.error(f"Error checking deadline reminder history: {e}")
                return False

    async def _send_notifications_batch(self, notifications: List[BaseNotification]) -> None:
        """Send a batch of notifications"""
        try:
            # Store notifications in database
            with self.get_session() as session:
                for notification in notifications:
                    notification_orm = NotificationsORM(
                        id=notification.id,
                        user_id=notification.user_id,
                        company_id=notification.company_id,
                        email=notification.email,
                        notification_type=notification.notification_type,
                        channel=notification.channel.value,
                        payload=notification.payload.model_dump(),
                        is_sent=False,
                        created_at=notification.created_at
                    )
                    session.add(notification_orm)

                session.commit()

            # Send emails (this would integrate with your email service)
            await self._send_email_notifications(notifications)

        except Exception as e:
            self.logger.error(f"Error sending notification batch: {e}")

    async def _send_email_notifications(self, notifications: List[BaseNotification]) -> None:
        """Send email notifications (placeholder for email service integration)"""
        try:
            # This would integrate with your email service (Resend, etc.)
            # For now, just log the notifications
            for notification in notifications:
                if notification.channel == NotificationChannel.email:
                    self.logger.info(
                        f"Email notification sent to {notification.email}: "
                        f"{notification.payload.subject}"
                    )

                    # Mark as sent in database
                    with self.get_session() as session:
                        notification_orm = session.query(NotificationsORM).filter_by(
                            id=notification.id
                        ).first()

                        if notification_orm:
                            notification_orm.is_sent = True
                            notification_orm.sent_at = utc_time()
                            session.commit()

        except Exception as e:
            self.logger.error(f"Error sending email notifications: {e}")

    async def cleanup_old_notifications(self, days_old: int = 30) -> None:
        """Clean up old notifications to prevent database bloat"""
        with self.get_session() as session:
            try:
                cutoff_date = utc_time() - timedelta(days=days_old)

                deleted_count = (
                    session.query(NotificationsORM)
                    .filter(NotificationsORM.created_at < cutoff_date)
                    .delete()
                )

                session.commit()

                self.logger.info(f"Cleaned up {deleted_count} old notifications")

            except Exception as e:
                self.logger.error(f"Error cleaning up old notifications: {e}")


# Background task functions that can be scheduled
async def send_deadline_reminders():
    """Background task to send deadline reminders"""
    from src.utils.route_helpers import get_controller

    notification_service = get_controller('job_actions_notifications')

    # Send reminders for different timeframes
    for days in [7, 3, 1]:
        await notification_service.notify_application_deadline_reminder(days)


async def cleanup_old_notifications():
    """Background task to cleanup old notifications"""
    from src.utils.route_helpers import get_controller

    notification_service = get_controller('job_actions_notifications')
    await notification_service.cleanup_old_notifications()
