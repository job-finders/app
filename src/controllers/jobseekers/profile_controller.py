from datetime import datetime, timezone
import uuid

from flask import Flask
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from src.controllers.controller import Controllers, error_handler
from src.database.sql.config import ConfigurationORM
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.database.models.config import Configuration
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

    @error_handler
    async def create_profile(self, profile_data: JobSeekerProfile) -> JobSeekerProfile:
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
            data = profile_data.model_dump()
            profile_orm = JobSeekerProfileORM(
                **data,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
            session.add(profile_orm)

            # on commit, session context manager will flush & commit
            return JobSeekerProfile(**profile_orm.to_dict())

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
                .first()
            )
            return JobSeekerProfile(**seeker_orm.to_dict()) if orm else None

    @error_handler
    async def update_profile(
        self, user_uid: str, update_data: dict
    ) -> JobSeekerProfile | None:
        """Partially update profile fields and return the updated model."""

        if not(isinstance(user_uid, str) and user_uid.strip()):
            return None

        if not update_data:
            return None

        with self.get_session() as session:
            orm = (
                session
                .query(JobSeekerProfileORM)
                .filter_by(user_uid=user_uid)
                .first()
            )
            if not orm:
                return None

            # Only update provided keys
            for field, value in update_data.items():
                if value is None:
                    continue
                if hasattr(orm, field):
                    setattr(orm, field, value)

            orm.last_updated = datetime.now(timezone.utc)
            session.flush()
            return JobSeekerProfile.model_validate(orm)

    @error_handler
    async def delete_profile(self, user_uid: str) -> dict | None:
        """Soft-delete and anonymize personal fields for GDPR compliance."""
        if not(isinstance(user_uid, str) and user_uid.strip()):
            return None

        with self.get_session() as session:
            orm = (
                session
                .query(JobSeekerProfileORM)
                .filter_by(user_uid=user_uid)
                .first()
            )
            if not orm:
                return None

            orm.bio = None
            orm.phone = None
            orm.website = None
            orm.linkedin = None
            orm.github = None
            orm.visibility = False
            orm.last_updated = datetime.now(timezone.utc)
            session.flush()
            return {"message": "Profile anonymized and hidden successfully."}

    @error_handler
    async def search_profiles(
        self, query: str, role: str = None
    ) -> list[JobSeekerProfile]:
        """
        Search across name, bio, location, and list-fields.
        Filters by role if provided.
        """
        if not(isinstance(query, str) and query.strip()):
            return []
        # I do not really need role here -         
        # if not(isinstance(role, str) and role.strip()):
        #     return []


        with self.get_session() as session:
            term = f"%{query.lower()}%"

            q = session.query(JobSeekerProfileORM).filter(
                or_(
                    JobSeekerProfileORM.first_name.ilike(term),
                    JobSeekerProfileORM.last_name.ilike(term),
                    JobSeekerProfileORM.bio.ilike(term),
                    JobSeekerProfileORM.location.ilike(term),
                    JobSeekerProfileORM.job_titles_of_interest.any(query),
                    JobSeekerProfileORM.industries_of_interest.any(query),
                    JobSeekerProfileORM.locations_of_interest.any(query),
                )
            )
            if role:
                q = q.filter(JobSeekerProfileORM.role == role)

            seeker_orm_list = q.all()
            return [JobSeekerProfile(**orm.to_dict()) for orm in seeker_orm_list if orm] if seeker_orm_list else []

    @error_handler
    async def upload_profile_picture(
        self, user_uid: str, file_storage, subfolder: str = "profile_pics"
    ) -> dict | None:
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
        url = save_file_to_storage(
            file=f, filename=filename, subfolder=subfolder
        )

        with self.get_session() as session:
            orm = (
                session
                .query(JobSeekerProfileORM)
                .filter_by(user_uid=user_uid)
                .first()
            )
            if not orm:
                return {"error": "Profile not found"}

            orm.profile_image_url = url
            session.flush()

        return {"message": "Image uploaded", "url": url}

    @error_handler
    async def list_profiles_by_role(
        self, role: str
    ) -> list[JobSeekerProfile]:
        """Fetch all profiles matching a given role."""
        if not (isinstance(role, str) and role.strip()):
            return []

        with self.get_session() as session:
            job_seeker_orm_list: list[JobSeekerProfileORM] = session.query(JobSeekerProfileORM).filter_by(role=role).limit(100).all()

            # Do Not Include Relationships in Lists only on Specific User Profile request -
            # Will only list profiles that are marked Visible.
            return [JobSeekerProfile(**profile_orm.to_dict()) for profile_orm in job_seeker_orm_list 
            if profile_orm.visibility] if job_seeker_orm_list else []

    @error_handler
    async def get_default_work_locations(self) -> list[Configuration]:
        with self.get_session() as session:
            orm = (
                session
                .query(ConfigurationORM)
                .filter_by(type='location')
                .all()
            )
            return [Configuration.model_validate(x.to_dict()) for x in orm]

    @error_handler
    async def get_industries_of_interest(self) -> list[Configuration]:
        with self.get_session() as session:
            orm = (
                session
                .query(ConfigurationORM)
                .filter_by(type='industry')
                .all()
            )
            return [Configuration.model_validate(x.to_dict()) for x in orm]

    @error_handler
    async def get_job_titles_of_interest(self) -> list[Configuration]:
        with self.get_session() as session:
            orm = (
                session
                .query(ConfigurationORM)
                .filter_by(type='job_title')
                .all()
            )
            return [Configuration.model_validate(x.to_dict()) for x in orm]
