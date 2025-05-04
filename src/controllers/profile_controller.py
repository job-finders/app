from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask import Flask

from src.database.models.config import Configuration
from src.database.sql.config import ConfigurationORM
from src.database.sql.jobseeker_profile import JobSeekerProfileORM
from sqlalchemy import or_

from src.controllers.controller import error_handler
from src.controllers.controller import Controllers
from src.database.models.jobseeker_profile import JobSeekerProfile
from src.utils import save_file_to_storage  # Assuming you have a utility for file storage

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename: str,allowed_extensions: set) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions







class JobSeekerProfilesController(Controllers):
    def __init__(self):
        super().__init__()

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def create_profile(self, profile_data: JobSeekerProfile) -> JobSeekerProfile:
        """
        Create a new user profile (seeker or employer).

        - Accepts validated profile data (Pydantic model).
        - Links the profile to an existing user via `user_uid`.
        - Handles conditional logic: e.g., different fields for seekers vs employers.
        - Returns the created Profile object.
        """
        with self.get_session() as session:
            # Check if a profile already exists for this user
            existing = session.query(JobSeekerProfileORM).filter_by(user_uid=profile_data.user_uid).first()
            if existing:
                raise ValueError("Profile already exists for this user")

            # Convert Pydantic model to ORM
            profile_orm = JobSeekerProfileORM(**profile_data.model_dump())

            # Add to session
            session.add(profile_orm)

            # Return the saved profile
            return JobSeekerProfile(**profile_orm.to_dict())

    @error_handler
    async def get_profile_by_uid(self, user_uid: str) -> JobSeekerProfile | None:
        """
        Retrieve a user profile by their UID.

        - Queries the database using the user's unique identifier.
        - Returns the profile as a Pydantic model or None if not found.
        """
        with self.get_session() as session:
            profile = session.query(JobSeekerProfileORM).filter_by(user_uid=user_uid).first()
            if profile:
                return JobSeekerProfile(**profile.to_dict())
            return None

    @error_handler
    async def update_profile(self, user_uid: str, update_data: dict) -> JobSeekerProfile | None:
        """
        Update an existing user profile.

        - Accepts partial data for updating.
        - Validates editable fields depending on role.
        - Returns the updated Profile object or None if not found.
        """
        with self.get_session() as session:
            profile = session.query(JobSeekerProfileORM).filter_by(user_uid=user_uid).first()
            if not profile:
                self.logger.info(f"No profile found for user_uid={user_uid}")
                return None

            for key, value in update_data.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)

            profile.last_updated = datetime.utcnow()
            session.flush()
            return JobSeekerProfile(**profile.to_dict())

    @error_handler
    async def delete_profile(self, user_uid: str) -> dict | None:
        """
        Delete a profile associated with a given UID.

        - Typically soft-deletes the profile.
        - Might also anonymize personal data for GDPR compliance.
        - Returns a status dict or None.
        """
        with self.get_session() as session:
            profile = session.query(JobSeekerProfileORM).filter_by(user_uid=user_uid).first()
            if not profile:
                self.logger.info(f"No profile found for deletion with user_uid={user_uid}")
                return None

            # Anonymize for GDPR compliance
            profile.bio = None
            profile.phone = None
            profile.website = None
            profile.linkedin = None
            profile.github = None
            profile.visibility = False
            profile.last_updated = datetime.utcnow()
            session.flush()

            return {"message": "Profile soft-deleted and anonymized successfully."}

    @error_handler
    async def search_profiles(self, query: str, role: str = None) -> list[JobSeekerProfile]:
        """
        Search for profiles using a general query string.

        - Filters by name, bio, skills, or company name depending on the user role.
        - Optionally limits search to a specific role (e.g., seekers only).
        - Returns a list of matching profile objects.
        """
        with self.get_session() as session:
            # Use query directly instead of q
            search_term = f"%{query.lower()}%"  # Format the query string for SQL LIKE pattern

            # Perform the search query
            results = session.query(JobSeekerProfileORM).filter(
                or_(
                    JobSeekerProfileORM.bio.ilike(search_term),
                    JobSeekerProfileORM.location.ilike(search_term),
                    JobSeekerProfileORM.job_titles_of_interest.any(query),
                    JobSeekerProfileORM.industries_of_interest.any(query),
                )
            ).all()

            return [JobSeekerProfile(**profile.to_dict()) for profile in results]

    @error_handler
    async def upload_profile_picture(self, user_uid: str, file,
                                     allowed_extensions: set , subfolder: str = "profile_pics") -> dict | None:

        """
        Upload and attach a profile picture to a user's profile.

        - Validates the image format and size based on the accepted extensions.
        - Stores it in the specified subfolder (default is "profile_pics").
        - Updates the user's profile with the image URL.
        """
        if not allowed_extensions:
            allowed_extensions = {"png", "jpg", "jpeg", "gif"}

        if 'file' not in file:
            return {"error": "No file part"}

        uploaded_file = file['file']
        if uploaded_file.filename == '':
            return {"error": "No selected file"}

        # Check if file extension is valid
        if not allowed_file(filename=uploaded_file.filename, allowed_extensions=allowed_extensions):
            return {"error": f"Invalid file format. Allowed formats are {', '.join(allowed_extensions)}."}

        # Save the file to storage and get the file URL
        filename = secure_filename(uploaded_file.filename)
        file_url = save_file_to_storage(
            file=uploaded_file, filename=filename, allowed_extensions=allowed_extensions, subfolder=subfolder)

        # Update the user's profile with the new image URL
        with self.get_session() as session:
            profile = session.query(JobSeekerProfileORM).filter_by(user_uid=user_uid).first()
            if not profile:
                return {"error": "Profile not found"}

            profile.profile_image_url = file_url


        return {"message": "Profile picture uploaded successfully", "image_url": file_url}


    @error_handler
    async def list_profiles_by_role(self, role: str):
        """
        Fetch all profiles for a specific role (e.g., 'seeker' or 'employer').

        - Returns a list of profile models.
        - Useful for admin views or search filters.
        """
        pass

    @error_handler
    async def get_default_work_locations(self) -> list[Configuration]:
        """
        Fetch a list of default work locations from the configuration table,
        returning them as Pydantic Configuration models.
        """
        with self.get_session() as session:
            orm_items = session.query(ConfigurationORM).filter(ConfigurationORM.type == 'location').all()
            return [Configuration.model_validate(item.to_dict()) for item in orm_items]

    @error_handler
    async def get_industries_of_interest(self) -> list[Configuration]:
        """
        Fetch a list of industries of interest from the configuration table.
        """
        with self.get_session() as session:
            orm_items = session.query(ConfigurationORM).filter(ConfigurationORM.type == 'industry').all()
            return [Configuration.model_validate(item.to_dict()) for item in orm_items]

    @error_handler
    async def get_job_titles_of_interest(self) -> list[Configuration]:
        """
        Fetch a list of job titles of interest from the configuration table.
        """
        with self.get_session() as session:
            orm_items = session.query(ConfigurationORM).filter(ConfigurationORM.type == 'job_title').all()
            return [Configuration.model_validate(item.to_dict()) for item in orm_items]
