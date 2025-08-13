# Standard Library
from datetime import datetime, timezone
import uuid


# Flask & Third-Party
from flask import Flask
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from src.cache.cache_redis import cached
# Controllers
from src.controllers.controller import Controllers, error_handler

# Domain Models
from src.database.models import Configuration, JobSeekerProfile
from src.database.models.referral_tracking import ReferralStatus

# SQL Models (ORMs)
from src.database import ConfigurationORM, JobSeekerProfileORM, SavedJobORM, JobReferralORM


# Utilities
from src.utils import save_file_to_storage

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in allowed_extensions
    )


class JobSeekerProfilesController(Controllers):
    __dict__ = """
        This Controller manages job seeker profiles, including creation,
        retrieval, updating, deletion, and searching.
    """
    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app: Flask):
        super().init_app(app=app)


    async def create_profile(self, profile_data: JobSeekerProfile) -> JobSeekerProfile | None:
        """Create a new JobSeekerProfile."""
        if not isinstance(profile_data,JobSeekerProfile):
            return None

        with self.get_session() as session:
            existing = (
                session
                .query(JobSeekerProfileORM)
                .filter_by(user_uid=profile_data.user_uid)
                .first()
            )
            if existing:
                raise ValueError("Profile already exists for this user")

            # Merge Pydantic → ORM fields (lists become JSON arrays)
            # exclude fields that are not needed in the ORM model
            exclude_fields = {'applications', 'interested_companies', 'following_companies', 'resumes_list',
                              'saved_jobs'}

            data = profile_data.model_dump(exclude_unset=True, exclude=exclude_fields)
            self.logger.info(f"Creating profile for user_uid: {data.get('user_uid', 'unknown')}")
            profile_orm = JobSeekerProfileORM(
                **data,
                last_updated=datetime.now(timezone.utc))
            session.add(profile_orm)
            self.logger.info(f"Profile created for user_uid: {profile_orm.user_uid}")
            # on commit, session context manager will flush & commit
            return JobSeekerProfile(**profile_orm.to_dict()) if profile_data else None

    @error_handler
    async def get_profile_by_uid(self, user_uid: str) -> JobSeekerProfile | None:
        """Fetch a profile or return None if missing."""
        if not (isinstance(user_uid, str) and user_uid.strip()):
            return None
        with self.get_session() as session:
            seeker_orm = (
                session
                .query(JobSeekerProfileORM)
                .filter_by(user_uid=user_uid)
                .first())
            return JobSeekerProfile(**seeker_orm.to_dict()) if seeker_orm else None

    @error_handler
    async def get_complete_profile_by_uid(self, user_uid: str) -> JobSeekerProfile | None:
        """Fetch a profile with saved jobs or return None if missing."""
        if not (isinstance(user_uid, str) and user_uid.strip()):
            self.logger.warning("Invalid user_uid provided for get_complete_profile_by_uid")
            return None

        with self.get_session() as session:
            seeker_orm = (
                session
                .query(JobSeekerProfileORM)
                .options(
                    joinedload(JobSeekerProfileORM.resumes_list),
                    joinedload(JobSeekerProfileORM.saved_jobs)
                    .joinedload(SavedJobORM.job)
                )
                .filter_by(user_uid=user_uid)
                .first())

            if not seeker_orm:
                return None
                
            job_seeker_profile = JobSeekerProfile(
                **seeker_orm.to_dict(include_relationships=True))

            # Add saved jobs count to profile
            self.logger.info(f"Found Job Seeker Profile with {job_seeker_profile.saved_jobs_count} saved jobs")
            
            return job_seeker_profile


    @error_handler
    async def update_profile(self, user_uid: str, update_data: dict) -> JobSeekerProfile | None:
        """Partially update profile fields and return the updated model."""
        if not(isinstance(user_uid, str) and user_uid.strip()):
            return None
        if not update_data:
            return None

        with self.get_session() as session:
            profile_orm = session.query(JobSeekerProfileORM).filter_by(user_uid=user_uid).first()
            if not profile_orm:
                return None

            # Only update provided keys
            for field, value in update_data.items():
                if value is None:
                    continue
                if hasattr(profile_orm, field):
                    setattr(profile_orm, field, value)

            profile_orm.last_updated = datetime.now(timezone.utc)
            session.flush()
            return JobSeekerProfile(**profile_orm.to_dict())

    @error_handler
    async def delete_profile(self, user_uid: str) -> dict | None:
        """Soft-delete and anonymize personal fields for GDPR compliance."""
        if not(isinstance(user_uid, str) and user_uid.strip()):
            return None

        with self.get_session() as session:
            profile_orm = session.query(JobSeekerProfileORM).filter_by(user_uid=user_uid).first()
            if not profile_orm:
                return None
            profile_orm.bio = None
            profile_orm.phone = None
            profile_orm.website = None
            profile_orm.linkedin = None
            profile_orm.github = None
            profile_orm.visibility = False
            profile_orm.last_updated = datetime.now(timezone.utc)
            session.flush()
            return {"message": "Profile anonymized and hidden successfully."}

    @error_handler
    async def search_profiles(self, query: str, role: str = None) -> list[JobSeekerProfile]:
        """
        Search across name, bio, location, and list-fields.
        Filters by role if provided.
        """
        if not(isinstance(query, str) and query.strip()):
            return []
        with self.get_session() as session:
            term = f"Search Query : {query}"
            q = session.query(JobSeekerProfileORM).filter(
                or_(
                    JobSeekerProfileORM.first_name.ilike(term),
                    JobSeekerProfileORM.last_name.ilike(term),
                    JobSeekerProfileORM.bio.ilike(term),
                    JobSeekerProfileORM.location.ilike(term),
                    JobSeekerProfileORM.job_titles_of_interest.any(term),
                    JobSeekerProfileORM.industries_of_interest.any(term),
                    JobSeekerProfileORM.locations_of_interest.any(term),
                ))
            seeker_orm_list = q.all()
            return [JobSeekerProfile(**orm.to_dict()) for orm in seeker_orm_list if orm] if seeker_orm_list else []

    @error_handler
    async def upload_profile_picture(self, user_uid: str, file_storage, subfolder: str = "profile_pics") -> dict | None:
        """Validate, save, and attach a profile image."""

        if not (isinstance(user_uid, str) and user_uid.strip()):
            return None

        if 'file' not in file_storage:
            return {"error": "No file part"}

        f = file_storage['file']
        if not f or f.filename == "":
            return {"error": "No selected file"}

        if not allowed_file(f.filename, ALLOWED_IMAGE_EXTENSIONS):
            exts = ", ".join(ALLOWED_IMAGE_EXTENSIONS)
            return {"error": f"Invalid format; allowed: {exts}"}
        filename = secure_filename(f.filename)
        # Actually Saving to FileStorage and Returning the URL to the File.
        url = save_file_to_storage(file=f, filename=filename, subfolder=subfolder)
        with self.get_session() as session:
            orm = session.query(JobSeekerProfileORM).filter_by(user_uid=user_uid).first()
            if not orm:
                return {"error": "Profile not found"}
            orm.profile_image_url = url
            session.flush()
        return {"message": "Image uploaded", "url": url}

    @error_handler
    async def list_profiles_by_role(self, role: str) -> list[JobSeekerProfile]:
        """Fetch all profiles matching a given role."""
        # TODO - needs to include ways to browse through the profiles using page and page size

        with self.get_session() as session:
            job_seeker_orm_list = session.query(JobSeekerProfileORM).filter_by(visibility=True).limit(100).all()
            # Do Not Include Relationships in Lists only on Specific User Profile request -
            # Will only list profiles that are marked Visible.
            return [JobSeekerProfile(**profile_orm.to_dict()) for profile_orm in job_seeker_orm_list
                    if profile_orm] if job_seeker_orm_list else []

    @error_handler
    async def get_default_work_locations(self) -> list[Configuration]:
        """returns a list of default locations"""
        with self.get_session() as session:
            locations_orm_list = session.query(ConfigurationORM).filter_by(type='location').all()
            return [Configuration(**loc.to_dict()) for loc in locations_orm_list if loc] if locations_orm_list else []

    @error_handler
    async def get_industries_of_interest(self) -> list[Configuration]:
        """returns a list of default industries"""
        with self.get_session() as session:
            industry_orm_list = session.query(ConfigurationORM).filter_by(type='industry').all()
            return [Configuration(**indus.to_dict()) for indus in industry_orm_list] if industry_orm_list else []

    @error_handler
    async def get_job_titles_of_interest(self) -> list[Configuration]:
        with self.get_session() as session:
            orm = session.query(ConfigurationORM).filter_by(type='job_title').all()
            return [Configuration.model_validate(x.to_dict()) for x in orm]

    # --- Referral Methods ---
    @error_handler
    async def create_referral(self, referrer_uid: str, job_id: str, referred_email: str, referral_code: str) -> dict:
        """Create a new job referral."""
        with self.get_session() as session:
            # Check if referral already exists
            existing = session.query(JobReferralORM).filter_by(
                referrer_id=referrer_uid,
                job_id=job_id,
                referred_email=referred_email
            ).first()
            if existing:
                return {"error": "Referral already exists"}

            referral = JobReferralORM(
                referral_id=uuid.uuid4(),
                referrer_id=referrer_uid,
                job_id=job_id,
                referred_email=referred_email,
                referral_code=referral_code,
                shared_at=datetime.now(timezone.utc),
                status=ReferralStatus.PENDING,
                created_at=datetime.now(timezone.utc)
            )
            session.add(referral)
            return {"message": "Referral created successfully"}

    @error_handler
    async def get_referrals_by_referrer(self, user_uid: str, active_only: bool = False) -> list[dict]:
        """Get all referrals made by a user."""
        with self.get_session() as session:
            query = session.query(JobReferralORM).filter_by(referrer_id=user_uid)
            # Note: JobReferralORM doesn't have is_active field, using status instead
            if active_only:
                query = query.filter(JobReferralORM.status.in_([ReferralStatus.PENDING, ReferralStatus.APPLIED]))
            return [ref.to_dict() for ref in query.all()]

    @error_handler
    async def get_referrals_by_referee(self, user_uid: str) -> list[dict]:
        """Get referral info for a referred user."""
        with self.get_session() as session:
            return [
                ref.to_dict()
                for ref in session.query(JobReferralORM)
                .filter_by(referred_email=user_uid)  # Note: JobReferralORM uses referred_email
                .all()
            ]

    @error_handler
    async def update_referral_status(self, referral_id: int, status: ReferralStatus) -> dict:
        """Update a referral's status."""
        with self.get_session() as session:
            referral = session.query(JobReferralORM).get(referral_id)
            if not referral:
                return {"error": "Referral not found"}

            referral.status = status
            referral.updated_at = datetime.now(timezone.utc)
            if status == ReferralStatus.HIRED:  # JobReferralORM uses HIRED instead of COMPLETED
                # Update referrer's stats
                referrer = session.query(JobSeekerProfileORM).get(referral.referrer_id)
                if referrer:
                    # Note: JobSeekerProfileORM may not have referral_count field
                    # This would need to be added to the model or handled differently
                    pass
            return {"message": "Referral status updated"}

    @error_handler
    async def get_referral_stats(self, user_uid: str) -> dict:
        """Get statistics about a user's referrals."""
        with self.get_session() as session:
            total = session.query(JobReferralORM).filter_by(referrer_id=user_uid).count()
            completed = session.query(JobReferralORM).filter_by(
                referrer_id=user_uid,
                status=ReferralStatus.HIRED  # Using HIRED instead of COMPLETED
            ).count()

            return {
                "total_referrals": total,
                "completed_referrals": completed,
                "completion_rate": (completed / total * 100) if total else 0
            }
