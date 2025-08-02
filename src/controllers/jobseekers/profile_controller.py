# Standard Library
from datetime import datetime, timezone

# Flask & Third-Party
from flask import Flask
from sqlalchemy import or_
from werkzeug.utils import secure_filename

# Controllers
from src.controllers.controller import Controllers, error_handler

# Domain Models
from src.database.models import Configuration, JobSeekerProfile

# SQL Models (ORMs)
from src.database import ConfigurationORM, JobSeekerProfileORM

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
