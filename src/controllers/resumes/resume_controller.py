# Standard Library
import uuid
from datetime import timedelta, datetime
from typing import Type

# Flask Core
from flask import url_for

# SQLAlchemy ORM
from sqlalchemy.orm import joinedload

from src.database.models import (
    Certification,
    Education,
    Language,
    Experience,
    Project,
    Publication,
    Award,
    CustomSection,
    JobSeekerCV,
    SavedCV,
)
from src.database.sql import Session

# Controllers
from src.controllers.controller import Controllers, error_handler

# Constants
from src.database.constants import utc_time

# SQL Models (ORMs)
from src.database import (
    JobApplicationORM,
    JobSeekerCVORM,
    ExperienceORM,
    EducationORM,
    CertificationORM,
    LanguageORM,
    ProjectORM,
    PublicationORM,
    AwardORM,
    CustomSectionORM,
    SavedCVORM,
    UserORM,
)

# Email
from src.emailer import EmailModel, settings

# Utilities
from src.utils.route_helpers import get_service


class ResumeController(Controllers):
    SECTION_MODELS: dict[str, Type] = {
        'experience': ExperienceORM,
        'education': EducationORM,
        'certifications': CertificationORM,
        'languages': LanguageORM,
        'projects': ProjectORM,
        'publications': PublicationORM,
        'awards': AwardORM,
        'custom_sections': CustomSectionORM
    }
    def __init__(self, factory):
        super().__init__(factory)

    def init_app(self, app):
        super().init_app(app)

    @error_handler
    async def create_cv(self, user_uid: str, data: JobSeekerCV) -> JobSeekerCV:
        # Create a new Resume with related entries (experience, education, etc.)
        if not (isinstance(user_uid, str) and user_uid.strip()):
            return {}
        if not isinstance(data, JobSeekerCV):
            return {}

        with self.get_session() as session:
            # Excluding - all items which will be saved later through save related items.
            _excluded_items = {'experience', 'education', 'certifications',
                               'languages', 'projects', 'publications', 'awards', 'custom_sections',
                               'jobseeker_profile'}

            self.logger.info(f"will now attempt to build the model")

            # Convert Pydantic model data to SQLAlchemy model instance
            # The field_serializer decorators will automatically handle HttpUrl conversion
            cv_data = data.model_dump(exclude=_excluded_items)

            cv_orm = JobSeekerCVORM(**cv_data)
            self.logger.info(
                f"CV model built successfully (Without Relationships): {cv_orm.to_dict(include_relationships=True)}")

            session.add(cv_orm)
            session.commit()  # Commit the session to persist the CV
            session.refresh(cv_orm)  # Refresh to get the generated cv_id

            self.logger.info(f"CV added to session: {data}")

            # Pass the cv_id to save_related_entries
            await self._save_related_entries(session=session, data=data, cv_id=cv_orm.cv_id)

            # Refresh the CV with all relationships
            session.refresh(cv_orm)
            return JobSeekerCV(**cv_orm.to_dict(include_relationships=True))

    @error_handler
    async def _save_related_entries(self, session: Session, data: JobSeekerCV, cv_id: str):
        # Save nested resume data like experience, education, etc.
        # Explicitly retrieve and save each section
        sections = [
            ('experience', data.experience if data.experience else []),
            ('education', data.education if data.education else []),
            ('certifications', data.certifications if data.certifications else []),
            ('languages', data.languages if data.languages else []),
            ('projects', data.projects if data.projects else []),
            ('publications', data.publications if data.publications else []),
            ('awards', data.awards if data.awards else []),
            ('custom_sections', data.custom_sections if data.custom_sections else [])
        ]

        for section_name, section_items in sections:
            if section_items:
                await self.save_section(
                    session=session,
                    section_name=section_name,
                    section_data=section_items,
                    cv_id=cv_id  # Pass the cv_id to save_section
                )

    @error_handler
    async def save_section(self, session: Session, section_name: str, section_data, cv_id: str):
        # Save a specific section's data to the database
        if section_name not in self.SECTION_MODELS.keys():
            raise ValueError(f"Unknown section name: {section_name}")

        model_class = self.SECTION_MODELS[section_name]

        try:
            for item in section_data:
                # Convert Pydantic model to dictionary
                # The field_serializer decorators will automatically handle HttpUrl conversion
                item_data = item.model_dump(exclude={'cv'})

                # Set the cv_id for the foreign key relationship
                item_data['cv_id'] = cv_id

                # Generate a unique ID if not present or empty
                if not item_data.get('id') or item_data['id'] == '':
                    import uuid
                    item_data['id'] = str(uuid.uuid4())

                self.logger.info(f"Adding {section_name} item with cv_id: {cv_id}")
                session.add(model_class(**item_data))

            session.commit()  # Commit the session to persist the section data
            self.logger.info(f"Successfully saved {len(section_data)} items for section: {section_name}")

        except Exception as e:
            self.logger.error(f"Error saving {section_name}: {str(e)}")
            session.rollback()  # Rollback on error
            raise

    @error_handler
    async def get_cv_by_id(self, cv_id: str) -> JobSeekerCV | None:
        """return cv / resume with all its related fields"""
        if not (isinstance(cv_id, str) and cv_id.strip()):
            return None

        with self.get_session() as session:
            # Load the CV ORM object with all related fields
            cv_orm: JobSeekerCVORM = (
                session.query(JobSeekerCVORM)
                .options(
                    joinedload(JobSeekerCVORM.experience),
                    joinedload(JobSeekerCVORM.education),
                    joinedload(JobSeekerCVORM.certifications),
                    joinedload(JobSeekerCVORM.languages),
                    joinedload(JobSeekerCVORM.projects),
                    joinedload(JobSeekerCVORM.publications),
                    joinedload(JobSeekerCVORM.awards),
                    joinedload(JobSeekerCVORM.custom_sections),
                )
                .filter(JobSeekerCVORM.cv_id == cv_id)
                .first()
            )
            if not cv_orm:
                return None

            # Log the retrieved CV ORM object
            self.logger.info(f"Retrieved CV ORM: {cv_orm.to_dict(include_relationships=True)}")

            # Convert the CV ORM object to a Pydantic model
            jobseeker_cv = JobSeekerCV(**cv_orm.to_dict(include_relationships=True))

            # Log the Pydantic model to ensure it is correctly populated
            self.logger.info(f"PYDANTIC MODEL ================================")
            self.logger.info(f"{jobseeker_cv}")

            return jobseeker_cv


    @error_handler
    async def get_successful_resumes_by_job(
        self,
        *,
        job_id: str,
            outcome: list[str] | None = None,
        min_ats_score: int = 0,
        limit: int = 20,
    ) -> list[JobSeekerCV]:
        """
        Return JobSeekerCV instances whose applications to `job_id` are successful.

        Success = JobApplicationORM.application_stage IN (`outcome`)
                  AND JobApplicationORM.validation_score >= min_ats_score
        """
        if outcome is None:
            outcome = ["interviewed", "hired", "shortlisted"]

        if not isinstance(job_id, str) or not job_id.strip():
            return []

        with self.get_session() as session:
            # 1. Grab the CV IDs that meet the success criteria
            cv_ids_subquery = (
                session.query(JobApplicationORM.cv_id)
                .filter(
                    JobApplicationORM.job_id == job_id,
                    JobApplicationORM.application_stage.in_(outcome),
                    JobApplicationORM.validation_score >= min_ats_score,
                )
                .limit(limit)
                .subquery()
            )

            # 2. Fetch full JobSeekerCV objects with eager-loaded relationships
            cvs_orm = (
                session.query(JobSeekerCVORM)
                .options(
                    joinedload(JobSeekerCVORM.experience),
                    joinedload(JobSeekerCVORM.education),
                    joinedload(JobSeekerCVORM.certifications),
                    joinedload(JobSeekerCVORM.languages),
                    joinedload(JobSeekerCVORM.projects),
                    joinedload(JobSeekerCVORM.publications),
                    joinedload(JobSeekerCVORM.awards),
                    joinedload(JobSeekerCVORM.custom_sections),
                )
                .filter(JobSeekerCVORM.cv_id.in_(cv_ids_subquery))
                .all()
            )

            return [
                JobSeekerCV(**cv.to_dict(include_relationships=True))
                for cv in cvs_orm
            ]

    @error_handler
    async def get_primary_resume(self, user_id: str) -> JobSeekerCV| None:
        """
        Retrieves the primary resume for a given user using ORM to_dict() methods

        Args:
            user_id: The ID of the user to retrieve the resume for

        Returns:
            JobSeekerCV: The primary resume for the user

        Raises:
            ValueError: If no primary resume is found for the user
        """
        if not(isinstance(user_id, str) and user_id.strip()):
            return None

        with self.get_session() as session:
            # Query for the primary resume with eager loading
            resume_orm = session.query(JobSeekerCVORM).filter(
                JobSeekerCVORM.user_uid == user_id,
                JobSeekerCVORM.is_primary == True
            ).options(
                joinedload(JobSeekerCVORM.experience),
                joinedload(JobSeekerCVORM.education),
                joinedload(JobSeekerCVORM.certifications),
                joinedload(JobSeekerCVORM.languages),
                joinedload(JobSeekerCVORM.projects),
                joinedload(JobSeekerCVORM.publications),
                joinedload(JobSeekerCVORM.awards),
                joinedload(JobSeekerCVORM.custom_sections)
            ).first()

            if not resume_orm:
                raise ValueError(f"No primary resume found for user {user_id}")

            # Convert main resume using its to_dict method
            resume_data = resume_orm.to_dict(include_relationships=True)

            # Convert relationships using their to_dict methods
            # resume_data["experience"] = [exp.to_dict() for exp in resume_orm.experience]
            # resume_data["education"] = [edu.to_dict() for edu in resume_orm.education]
            # resume_data["certifications"] = [cert.to_dict() for cert in resume_orm.certifications]
            # resume_data["languages"] = [lang.to_dict() for lang in resume_orm.languages]
            # resume_data["projects"] = [proj.to_dict() for proj in resume_orm.projects]
            # resume_data["publications"] = [pub.to_dict() for pub in resume_orm.publications]
            # resume_data["awards"] = [award.to_dict() for award in resume_orm.awards]
            # resume_data["custom_sections"] = [cs.to_dict() for cs in resume_orm.custom_sections]

            # Create the Pydantic model from the combined dictionary
            return JobSeekerCV(**resume_data)

    @error_handler
    async def list_cvs_for_user(self, user_uid: str) -> list[JobSeekerCV]:
        # Get all resumes for a specific job seeker
        if not (isinstance(user_uid, str) and user_uid.strip()):
            return []

        with self.get_session() as session:
            # Query for all CVs for the given user
            cvs = session.query(JobSeekerCVORM).filter(JobSeekerCVORM.user_uid == user_uid).all()

            # If no CVs found, return an empty list
            if not cvs:
                return []

            # Retrieve all related data for each CV (experience, education, certifications, etc.)
            result = []
            for cv in cvs:
                _cv = await self.get_cv_by_id(cv_id=cv.cv_id)
                result.append(_cv)

            return result

    # noinspection DuplicatedCode
    @error_handler
    async def delete_cv(self, cv_id: str) -> bool:
        # Delete a specific CV and its related entries
        if not(isinstance(cv_id, str) and cv_id.strip()):
            return False

        with self.get_session() as session:
            # Query the main CV entry
            cv = session.query(JobSeekerCVORM).filter(JobSeekerCVORM.cv_id == cv_id).first()

            if not cv:
                return False  # If CV is not found, return False

            # Delete all related entries (experience, education, etc.)
            session.query(ExperienceORM).filter(ExperienceORM.cv_id == cv_id).delete()
            session.query(EducationORM).filter(EducationORM.cv_id == cv_id).delete()
            session.query(CertificationORM).filter(CertificationORM.cv_id == cv_id).delete()
            session.query(LanguageORM).filter(LanguageORM.cv_id == cv_id).delete()
            session.query(ProjectORM).filter(ProjectORM.cv_id == cv_id).delete()
            session.query(PublicationORM).filter(PublicationORM.cv_id == cv_id).delete()
            session.query(AwardORM).filter(AwardORM.cv_id == cv_id).delete()
            session.query(CustomSectionORM).filter(CustomSectionORM.cv_id == cv_id).delete()

            # Finally, delete the main CV entry
            session.delete(cv)

            # Commit the changes (this is handled by your session controller)
            return True  # Return True to indicate successful deletion

    @error_handler
    async def search_cvs(self, query: str, limit: int = 10) -> list[JobSeekerCV]:
        # Search for resumes using professional title or keyword
        if not(isinstance(query, str) and query.strip()):
            return []

        if not isinstance(limit, int):
            return []
        
        upper_limit = min(1 , max(limit, 100))
        
        with self.get_session() as session:
            # Query for CVs where the professional title or summary contains the search query (case-insensitive)
            cvs = session.query(JobSeekerCVORM).filter(
                (JobSeekerCVORM.professional_title.ilike(f"%{query}%")) |
                (JobSeekerCVORM.summary.ilike(f"%{query}%"))
            ).limit(upper_limit).all()

            # If no CVs found, return an empty list
            if not cvs:
                return []

            # Retrieve all related data for each CV (experience, education, certifications, etc.)
            result = []
            for cv in cvs:
                _cv = await self.get_cv_by_id(cv_id=cv.cv_id)
                result.append(_cv)

            return result

    @error_handler
    async def notify_admin_of_new_cv(self, user_email: str, cv_id: str) -> bool:
        # Notify admin via email when a new resume is submitted
        if not(isinstance(user_email, str) and user_email.strip()):
            return False
        if not(isinstance(cv_id, str) and cv_id.strip()):
            return False

        with self.get_session() as session:
            # Fetch the CV and user details
            cv = session.query(JobSeekerCVORM).filter(JobSeekerCVORM.cv_id == cv_id).first()
            if not cv:
                return False  # If CV is not found, return False

            user = session.query(UserORM).filter(UserORM.uid == user_email).first()
            if not user:
                return False  # If user is not found, return False

            # Prepare email content - TODO - please use proper templates
            subject = f"New CV Submitted by {user.name}"
            html_content = f"""
            <p>Hello Admin,</p>
            <p>A new resume has been submitted by {user.name}.</p>
            <p><strong>CV Details:</strong></p>
            <p><strong>Professional Title:</strong> {cv.professional_title}</p>
            <p><strong>Location:</strong> {cv.location}</p>
            <p><strong>Summary:</strong> {cv.summary}</p>
            <p><strong>View CV:</strong> <a href="{url_for('cv.view', cv_id=cv_id, _external=True)}">Click Here</a></p>
            <p><strong>Contact:</strong> {user.email}</p>
            <p>Best regards,<br>JobFinders</p>
            """

            # Send the email to the admin
            email = EmailModel(
                from_=user.email,
                to_=settings.ADMIN_EMAIL,  # Make sure the admin email is defined in the settings
                subject_=subject,
                html_=html_content
            )

            await get_service('send_mail')().send_mail_resend(email=email)
            return True  # Return True to indicate email was sent successfully

    @error_handler
    async def update_cv(self, cv_id: str, data: JobSeekerCV) -> bool:
        """
            Update an existing CV and all its associated sections.

            This method performs the following steps:
            1. Retrieves the existing CV record by its `cv_id`.
            2. If the CV is not found, returns `False`.
            3. Updates the core CV fields (title, summary, contact info, etc.).
            4. Deletes all previously associated entries (experience, education, certifications, etc.)
            to ensure outdated data is removed.
            5. Inserts the new associated data from the provided `JobSeekerCV` model.
            6. Returns `True` to indicate the update process was successfully initiated.

            Note:
            - This is a full replacement update, not a partial update.
            - Database commit is handled externally by the session manager.
            - This method is marked `async` to support compatibility with async routes or controllers.

            :param cv_id: The unique identifier of the CV to update.
            :param data: A fully populated `JobSeekerCV` Pydantic model with updated CV information.
            :return: Boolean indicating success or failure of the update.
        """
        # Update an existing CV and its related entries
        if not(isinstance(cv_id, str) and cv_id.strip()):
            return False
        if not isinstance(data, JobSeekerCV):
            return False

        with self.get_session() as session:
            existing_cv = session.query(JobSeekerCVORM).filter_by(cv_id=cv_id).first()
            if not existing_cv:
                return False

            # Update main CV fields
            existing_cv.professional_title = data.professional_title
            existing_cv.summary            = data.summary
            existing_cv.phone              = data.phone

            existing_cv.location = data.location
            existing_cv.contact_number = data.contact_number
            existing_cv.website = data.website
            existing_cv.github = data.github
            existing_cv.linkedin = data.linkedin
            existing_cv.updated_at = utc_time()

            # Delete old related entries
            for orm_class in [
                ExperienceORM, EducationORM, CertificationORM, LanguageORM,
                ProjectORM, PublicationORM, AwardORM, CustomSectionORM
            ]:
                session.query(orm_class).filter_by(cv_id=cv_id).delete()

            # Add updated related entries
            # noinspection DuplicatedCode
            for exp in data.experience:
                session.add(ExperienceORM(cv_id=cv_id, **exp.model_dump()))
            for edu in data.education:
                session.add(EducationORM(cv_id=cv_id, **edu.model_dump()))
            for cert in data.certifications:
                session.add(CertificationORM(cv_id=cv_id, **cert.model_dump()))
            for lang in data.languages:
                session.add(LanguageORM(cv_id=cv_id, **lang.model_dump()))
            for proj in data.projects:
                session.add(ProjectORM(cv_id=cv_id, **proj.model_dump()))
            for pub in data.publications:
                session.add(PublicationORM(cv_id=cv_id, **pub.model_dump()))
            for award in data.awards:
                session.add(AwardORM(cv_id=cv_id, **award.model_dump()))
            for custom in data.custom_sections:
                session.add(CustomSectionORM(cv_id=cv_id, **custom.model_dump()))

            return True

    @error_handler
    async def get_cvs_by_skill(self, skill: str) -> list[JobSeekerCV]:
        """
        Retrieve CVs that mention a specific skill in the 'skills' field.

        This method filters JobSeekerCV records where the 'skills' field includes
        the given skill string, using case-insensitive partial matching.
        Only CVs that have the skill included will be returned.

        :param skill: A keyword to search within the skills field.
        :return: A list of JobSeekerCV Pydantic models matching the skill.
        """
        if not(isinstance(skill, str) and skill.strip()):
            return []

        with self.get_session() as session:
            query = session.query(JobSeekerCVORM).filter(JobSeekerCVORM.skills.ilike(f"%{skill}%").limit(100).all())
            return [JobSeekerCV(**cv.to_dict()) for cv in query.all()]

    @error_handler
    async def get_cvs_by_location(self, location: str) -> list[JobSeekerCV]:
        """
            Retrieve CVs where the job seeker is located in a specific city or region.

            This method filters JobSeekerCV records using a case-insensitive partial match
            on the `location` field. Useful for employers or admins looking for local candidates.

        :param location: The city, province, or region to filter CVs by.
        :return: A list of JobSeekerCV Pydantic models whose location matches the input.
        """
        if not(isinstance(location, str) and location.strip()):
            return []

        with self.get_session() as session:
            query = session.query(JobSeekerCVORM).filter(
                JobSeekerCVORM.location.ilike(f"%{location}%")
            ).limit(100).all()
            return [JobSeekerCV(**cv.to_dict()) for cv in query.all()]

    @error_handler
    async def get_recent_cvs(self, limit: int = 10) -> list[JobSeekerCV]:
        """
        Fetch the most recently created CVs.

        This method retrieves CVs ordered by the `created_at` timestamp in descending order.
        It limits the number of returned records based on the `limit` parameter.
        Primarily used for admin or employer dashboards to show the latest submissions.

        :param limit: Maximum number of recent CVs to return. Default is 10.
        :return: A list of the most recent JobSeekerCV Pydantic models.
        """
        if not isinstance(limit, int):
            return []
        upper_limit = min(100, max(1, limit))

        with self.get_session() as session:
            query = (session.query(JobSeekerCVORM).order_by(JobSeekerCVORM.created_at.desc()).limit(upper_limit).all())
            resume_orm_list = query.all()
            return [JobSeekerCV(**resume_orm.to_dict()) for resume_orm in resume_orm_list] if resume_orm_list else []

    @error_handler
    async def flag_cv_for_review(self, cv_id: str, reason: str) -> bool:
        """
        Mark a CV for admin review by setting the `is_flagged` flag and storing the reason.

        This method is used by administrators to mark CVs that may require further attention,
        such as potential policy violations, suspicious content, or incomplete data.

        :param cv_id: The unique identifier of the CV to flag.
        :param reason: A short description or reason for flagging the CV.
        :return: True if the CV was flagged successfully, False otherwise.
        """

        if not(isinstance(cv_id, str) and cv_id.strip()):
            return False
        if not (isinstance(reason, str) and reason.strip()):
            return False

        with self.get_session() as session:
            cv = session.query(JobSeekerCVORM).filter_by(id=cv_id).first()
            if not cv:
                return False
            # We need to create a solid detection algorithm for resumes which should be flagged
            cv.is_flagged = True
            cv.flag_reason = reason
            return True

    @error_handler
    async def mark_cv_as_verified(self, cv_id: str) -> bool:
        """
        Mark a CV as verified by setting the `is_verified` flag.

        This method is typically used by administrators after reviewing a CV and confirming its
        authenticity and completeness.

        :param cv_id: The unique identifier of the CV to verify.
        :return: True if the CV was successfully marked as verified, False if not found.
        """
        if not(isinstance(cv_id, str) and cv_id.strip()):
            return False

        with self.get_session() as session:
            cv_orm = session.query(JobSeekerCVORM).filter_by(id=cv_id).first()
            if not cv_orm:
                return False
            cv_orm.is_verified = True
            return True

    @error_handler
    async def employer_save_cv(self, employer_id: str, save_cv_model: SavedCV) -> bool:
        """
        Allows an employer to bookmark or save a specific CV for later viewing.

        This creates a record linking the employer to the CV they are interested in,
        preventing duplicate saves if already bookmarked.

        :param save_cv_model:
        :param employer_id: The unique identifier of the employer.
        :return: True if saved successfully or already exists, False if CV does not exist.
        """
        if not(isinstance(employer_id, str) and employer_id.strip()):
            return False
        
        if not isinstance(save_cv_model, SavedCV):
            return False

        with self.get_session() as session:
            # Ensure the CV exists

            cv = session.query(JobSeekerCVORM).filter_by(cv_id=save_cv_model.cv_id).first()
            if not cv:
                return False

            # Check if already saved
            exists = session.query(SavedCVORM).filter_by(
                employer_id=save_cv_model.employer_id,
                cv_id=save_cv_model.cv_id
            ).first()
            if exists:
                return True

            # Create new save record 
            saved_cv_orm = SavedCVORM(**save_cv_model.model_dump())
            session.add(saved_cv_orm)
            return True

    @error_handler
    async def employer_saved_cvs(self, employer_id: str) -> list[JobSeekerCV]:
        """
        Get a list of CVs saved/bookmarked by a specific employer.

        This method retrieves the full CV details that the given employer has saved for later review.

        :param employer_id: The unique identifier of the employer.
        :return: A list of JobSeekerCV Pydantic models representing the saved CVs.
        """
        if not(isinstance(employer_id, str) and employer_id.strip()):
            return []

        with self.get_session() as session:
            # Get the saved CV records for the employer
            saved_cvs = session.query(SavedCVORM).filter_by(employer_uid=employer_id).all()
            cv_ids = [saved_cv.cv_id for saved_cv in saved_cvs]

            # Fetch the actual CV details using get_cv_by_id method, which should also handle ORM conversion
            cv_details = []
            for cv_id in cv_ids:
                _cv = await self.get_cv_by_id(cv_id=cv_id)
                cv_details.append(_cv)
            return cv_details

    @error_handler
    async def get_cv_statistics(self) -> dict:
        """
        Admin stats: Retrieve various statistics about the CVs in the system.

        This method collects the following stats:
        - Total number of CVs
        - Number of flagged CVs
        - Number of verified CVs
        - Number of recent CVs (optional, based on creation date)

        :return: A dictionary containing CV statistics.
        """
        with self.get_session() as session:
            # Total number of CVs
            total_cvs = session.query(JobSeekerCVORM).count()

            # Number of flagged CVs (flagged could be a column in your model)
            flagged_cvs = session.query(JobSeekerCVORM).filter_by(is_flagged=True).count()

            # Number of verified CVs (verified could be another column in your model)
            verified_cvs = session.query(JobSeekerCVORM).filter_by(is_verified=True).count()

            # Number of recent CVs (e.g., CVs created in the last 30 days)
            recent_cvs = session.query(JobSeekerCVORM).filter(
                JobSeekerCVORM.created_at > utc_time() - timedelta(days=30)).count()

            # You can also add other stats like the number of CVs in each category or skill, etc.

            return {"total_cvs": total_cvs, "flagged_cvs": flagged_cvs,
                    "verified_cvs": verified_cvs, "recent_cvs": recent_cvs}

    @error_handler
    async def get_cvs_by_certification(self, cert_name: str) -> list[JobSeekerCV]:
        """
        Filter CVs by a specific certification name.

        This method retrieves all CVs that have the specified certification.

        :param cert_name: The name of the certification to filter by.
        :return: A list of JobSeekerCV Pydantic models representing the CVs with the given certification.
        """
        if not(isinstance(cert_name, str) and cert_name.strip()):
            return []

        with self.get_session() as session:
            # Find the certifications matching the provided cert_name
            cert_list = session.query(CertificationORM).filter(CertificationORM.name == cert_name).limit(100).all()
            # Get the unique CV IDs associated with the matching certifications
            cv_ids = [cert.cv_id for cert in cert_list] if cert_list else []
            # Return the full CV details for each CV ID
            return [await self.get_cv_by_id(cv_id=cv_id) for cv_id in cv_ids] if cv_ids else []

    @error_handler
    async def get_cvs_by_language(self, language: str) -> list[JobSeekerCV]:
        """
        Filter CVs by known languages.

        This method retrieves all CVs that list the specified language.

        :param language: The name of the language to filter by.
        :return: A list of JobSeekerCV Pydantic models representing the CVs that include the given language.
        """
        if not(isinstance(language, str) and language.strip()):
            return []

        with self.get_session() as session:
            # Find the languages matching the provided language
            language = language.strip()
            languages_orm = session.query(LanguageORM).filter(LanguageORM.name.casefold() == language.casefold()).all()
            # Get the unique CV IDs associated with the matching languages
            cv_ids = [lang.cv_id for lang in languages_orm if lang] if languages_orm else []
            # Return the full CV details for each CV ID
            return [await self.get_cv_by_id(cv_id=cv_id) for cv_id in cv_ids] if cv_ids else []

    @error_handler
    async def get_resume_versions(self, cv_id: int):
        """Return all versions for a given resume ID."""
        pass

    async def set_default_resume(self, user_id: int, cv_id: int):
        """Mark one resume as default for the user."""
        pass

    @error_handler
    async def download_resume_pdf(self, cv_id: int):
        """Generate and return the PDF download of a resume."""
        pass

    @error_handler
    async def add_experience(self, user_uid: str, experience_data: Experience) -> Experience | None:
        if not (isinstance(user_uid, str) and user_uid.strip()):
            self.logger.error("Invalid user_uid ")
            return None

        if not isinstance(experience_data, Experience):
            self.logger.error("Experience data is required")
            return None

        with self.get_session() as session:
            # Create a new Experience object
            experience_orm = ExperienceORM(**experience_data.model_dump(exclude={'cv'}))
            # Add the experience to the session
            session.add(experience_orm)
            # Log the added experience
            self.logger.info(f"Experience added: {experience_data}")
            return experience_data

    @error_handler
    async def update_experience(self, exp_id: str, experience_data: Experience) -> Experience | None:
        if not (isinstance(exp_id, str) and exp_id.strip()):
            self.logger.error("Invalid exp_id")
            return None

        if not experience_data:
            self.logger.error("Experience data is required")
            return None

        with self.get_session() as session:
            # Retrieve the experience by ID
            experience_orm = (
                session.query(ExperienceORM)
                .filter(ExperienceORM.id == exp_id)
                .first()
            )
            if not experience_orm:
                self.logger.error("Experience not found for the given exp_id")
                return None
            # Update the experience fields
            experience_data = experience_data.model_dump(exclude={'cv'}, exclude_unset=True)
            for key, value in experience_data.items():
                setattr(experience_orm, key, value)
            # Log the updated experience
            self.logger.info(f"Experience updated for exp_id: {exp_id}")
            return experience_data

    @error_handler
    async def add_education(self, user_uid: str, education_data: Education) -> Education | None:
        if not (isinstance(user_uid, str) and user_uid.strip()):
            self.logger.error("Invalid user_uid")
            return None
        if not isinstance(education_data, Education):
            self.logger.error("Education data is required")
            return None

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = session.query(JobSeekerCVORM).filter(JobSeekerCVORM.user_uid == user_uid).first()
            if not cv_orm:
                self.logger.error("CV not found for the given user_uid")
                return None
            # Create a new Education object
            education_orm = EducationORM(**education_data.model_dump(exclude={'cv'}))
            # Add the education to the session
            session.add(education_orm)
            # Log the added education
            self.logger.info(f"Education added: {education_data}")
            return education_data

    @error_handler
    async def update_education(self, edu_id: str, education_data: Education) -> Education | None:
        if not (isinstance(edu_id, str) and edu_id.strip()):
            self.logger.error("Invalid edu_id")
            return None
        if not education_data:
            self.logger.error("Education data is required")
            return None

        with self.get_session() as session:
            # Retrieve the education by ID
            education_orm = session.query(EducationORM).filter(EducationORM.id == edu_id).first()
            if not education_orm:
                self.logger.error("Education not found for the given edu_id")
                return None
            # Update the education fields
            # Update the education fields
            education_orm_data = education_data.model_dump(exclude={'cv'}, exclude_unset=True)
            for key, value in education_orm_data.items():
                setattr(education_orm, key, value)

            # Log the updated education
            self.logger.info(f"Education updated: {education_data}")
            return education_data

    @error_handler
    async def add_certification(self, user_uid: str, certification_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not certification_data:
            raise ValueError("Certification data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Create a new Certification object
            certification = Certification(
                cv_id=cv_orm.cv_id,
                name=certification_data['name'],
                issuer=certification_data['issuer'],
                issue_date=certification_data['issue_date'],
                expiry_date=certification_data.get('expiry_date'),
                credential_url=certification_data.get('credential_url')
            )

            # Add the certification to the session
            session.add(certification)
            session.commit()
            session.refresh(certification)

            # Log the added certification
            self.logger.info(f"Certification added: {certification}")

    @error_handler
    async def update_certification(self, cert_id: str, certification_data: dict):
        if not (isinstance(cert_id, str) and cert_id.strip()):
            raise ValueError("Invalid cert_id")

        if not certification_data:
            raise ValueError("Certification data is required")

        with self.get_session() as session:
            # Retrieve the certification by ID
            certification = (
                session.query(CertificationORM)
                .filter(CertificationORM.id == cert_id)
                .first()
            )
            if not certification:
                raise ValueError("Certification not found for the given cert_id")

            # Update the certification fields
            certification.name = certification_data['name']
            certification.issuer = certification_data['issuer']
            certification.issue_date = certification_data['issue_date']
            certification.expiry_date = certification_data.get('expiry_date')
            certification.credential_url = certification_data.get('credential_url')

            # Commit the changes
            session.commit()

            # Log the updated certification
            self.logger.info(f"Certification updated: {certification}")

    @error_handler
    async def add_language(self, user_uid: str, language_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not language_data:
            raise ValueError("Language data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Create a new Language object
            language = Language(
                cv_id=cv_orm.cv_id,
                name=language_data['name'],
                proficiency=language_data['proficiency']
            )

            # Add the language to the session
            session.add(language)
            session.commit()
            session.refresh(language)

            # Log the added language
            self.logger.info(f"Language added: {language}")

    @error_handler
    async def update_language(self, lang_id: str, language_data: dict):
        if not (isinstance(lang_id, str) and lang_id.strip()):
            raise ValueError("Invalid lang_id")

        if not language_data:
            raise ValueError("Language data is required")

        with self.get_session() as session:
            # Retrieve the language by ID
            language = (
                session.query(LanguageORM)
                .filter(LanguageORM.id == lang_id)
                .first()
            )
            if not language:
                raise ValueError("Language not found for the given lang_id")

            # Update the language fields
            language.name = language_data['name']
            language.proficiency = language_data['proficiency']

            # Commit the changes
            session.commit()

            # Log the updated language
            self.logger.info(f"Language updated: {language}")

    @error_handler
    async def add_project(self, user_uid: str, project_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not project_data:
            raise ValueError("Project data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Create a new Project object
            project = Project(
                cv_id=cv_orm.cv_id,
                title=project_data['title'],
                description=project_data['description'],
                technologies=project_data['technologies'],
                link=project_data.get('link')
            )

            # Add the project to the session
            session.add(project)
            session.commit()
            session.refresh(project)

            # Log the added project
            self.logger.info(f"Project added: {project}")

    @error_handler
    async def update_project(self, project_id: str, project_data: dict):
        if not (isinstance(project_id, str) and project_id.strip()):
            raise ValueError("Invalid project_id")

        if not project_data:
            raise ValueError("Project data is required")

        with self.get_session() as session:
            # Retrieve the project by ID
            project = (
                session.query(ProjectORM)
                .filter(ProjectORM.id == project_id)
                .first()
            )
            if not project:
                raise ValueError("Project not found for the given project_id")

            # Update the project fields
            project.title = project_data['title']
            project.description = project_data['description']
            project.technologies = project_data['technologies']
            project.link = project_data.get('link')

            # Commit the changes
            session.commit()

            # Log the updated project
            self.logger.info(f"Project updated: {project}")

    @error_handler
    async def add_publication(self, user_uid: str, publication_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not publication_data:
            raise ValueError("Publication data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Create a new Publication object
            publication = Publication(
                cv_id=cv_orm.cv_id,
                title=publication_data['title'],
                publisher=publication_data['publisher'],
                date=publication_data['date'],
                link=publication_data.get('link')
            )

            # Add the publication to the session
            session.add(publication)
            session.commit()
            session.refresh(publication)

            # Log the added publication
            self.logger.info(f"Publication added: {publication}")

    @error_handler
    async def update_publication(self, pub_id: str, publication_data: dict):
        if not (isinstance(pub_id, str) and pub_id.strip()):
            raise ValueError("Invalid pub_id")

        if not publication_data:
            raise ValueError("Publication data is required")

        with self.get_session() as session:
            # Retrieve the publication by ID
            publication = (
                session.query(PublicationORM)
                .filter(PublicationORM.id == pub_id)
                .first()
            )
            if not publication:
                raise ValueError("Publication not found for the given pub_id")

            # Update the publication fields
            publication.title = publication_data['title']
            publication.publisher = publication_data['publisher']
            publication.date = publication_data['date']
            publication.link = publication_data.get('link')

            # Commit the changes
            session.commit()

            # Log the updated publication
            self.logger.info(f"Publication updated: {publication}")

    @error_handler
    async def add_award(self, user_uid: str, award_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not award_data:
            raise ValueError("Award data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Create a new Award object
            award = Award(
                cv_id=cv_orm.cv_id,
                title=award_data['title'],
                issuer=award_data['issuer'],
                date=award_data['date'],
                description=award_data.get('description')
            )

            # Add the award to the session
            session.add(award)
            session.commit()
            session.refresh(award)

            # Log the added award
            self.logger.info(f"Award added: {award}")

    @error_handler
    async def update_award(self, award_id: str, award_data: dict):
        if not (isinstance(award_id, str) and award_id.strip()):
            raise ValueError("Invalid award_id")

        if not award_data:
            raise ValueError("Award data is required")

        with self.get_session() as session:
            # Retrieve the award by ID
            award = (
                session.query(AwardORM)
                .filter(AwardORM.id == award_id)
                .first()
            )
            if not award:
                raise ValueError("Award not found for the given award_id")

            # Update the award fields
            award.title = award_data['title']
            award.issuer = award_data['issuer']
            award.date = award_data['date']
            award.description = award_data.get('description')

            # Commit the changes
            session.commit()

            # Log the updated award
            self.logger.info(f"Award updated: {award}")

    @error_handler
    async def add_custom_section(self, user_uid: str, custom_section_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not custom_section_data:
            raise ValueError("Custom section data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Create a new CustomSection object
            custom_section = CustomSection(
                cv_id=cv_orm.cv_id,
                title=custom_section_data['title'],
                content=custom_section_data['content']
            )

            # Add the custom section to the session
            session.add(custom_section)
            session.commit()
            session.refresh(custom_section)

            # Log the added custom section
            self.logger.info(f"Custom section added: {custom_section}")

    @error_handler
    async def update_custom_section(self, section_id: str, custom_section_data: dict):
        if not (isinstance(section_id, str) and section_id.strip()):
            raise ValueError("Invalid section_id")

        if not custom_section_data:
            raise ValueError("Custom section data is required")

        with self.get_session() as session:
            # Retrieve the custom section by ID
            custom_section = (
                session.query(CustomSectionORM)
                .filter(CustomSectionORM.id == section_id)
                .first()
            )
            if not custom_section:
                raise ValueError("Custom section not found for the given section_id")

            # Update the custom section fields
            custom_section.title = custom_section_data['title']
            custom_section.content = custom_section_data['content']

            # Commit the changes
            session.commit()

            # Log the updated custom section
            self.logger.info(f"Custom section updated: {custom_section}")

    @error_handler
    async def add_skills(self, user_uid: str, skills_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not skills_data or not skills_data['skills']:
            raise ValueError("Skills data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Add new skills to the existing skills list
            existing_skills = set(cv_orm.skills)
            new_skills = [skill for skill in skills_data['skills'] if
                          skill.strip() and skill.strip() not in existing_skills]

            if new_skills:
                cv_orm.skills.extend(new_skills)
                session.commit()
                self.logger.info(f"Skills added: {new_skills}")
            else:
                self.logger.info("No new skills to add.")

    @error_handler
    async def update_skills(self, user_uid: str, skills_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not skills_data or not skills_data['skills']:
            raise ValueError("Skills data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Update the skills field in the CV ORM
            cv_orm.skills = skills_data['skills']

            session.commit()

            # Log the updated skills
            self.logger.info(f"Skills updated: {skills_data['skills']}")

    @error_handler
    async def add_portfolio_links(self, user_uid: str, portfolio_links_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not portfolio_links_data or not portfolio_links_data['portfolio_links']:
            raise ValueError("Portfolio links data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Add new portfolio links to the existing portfolio links list
            existing_portfolio_links = set(cv_orm.portfolio_links)
            new_portfolio_links = [
                link for link in portfolio_links_data['portfolio_links']
                if link.strip() and link.strip() not in existing_portfolio_links
            ]

            if new_portfolio_links:
                cv_orm.portfolio_links.extend(new_portfolio_links)
                session.commit()
                self.logger.info(f"Portfolio links added: {new_portfolio_links}")
            else:
                self.logger.info("No new portfolio links to add.")

    @error_handler
    async def update_portfolio_links(self, user_uid: str, portfolio_links_data: dict):
        if not (isinstance(user_uid, str) and user_uid.strip()):
            raise ValueError("Invalid user_uid")

        if not portfolio_links_data or not portfolio_links_data['portfolio_links']:
            raise ValueError("Portfolio links data is required")

        with self.get_session() as session:
            # Retrieve the user's CV
            cv_orm = (
                session.query(JobSeekerCVORM)
                .filter(JobSeekerCVORM.user_uid == user_uid)
                .first()
            )
            if not cv_orm:
                raise ValueError("CV not found for the given user_uid")

            # Update the portfolio links field in the CV ORM
            cv_orm.portfolio_links = portfolio_links_data['portfolio_links']

            session.commit()

            # Log the updated portfolio links
            self.logger.info(f"Portfolio links updated: {portfolio_links_data['portfolio_links']}")
