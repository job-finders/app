from datetime import datetime, timedelta, UTC, timezone
from flask import Flask, url_for
from src.database.sql.users import UserORM
from src.main import send_mail
from src.emailer import EmailModel, settings
from src.database.sql.resume import (JobSeekerCVORM, ExperienceORM, EducationORM, CertificationORM, LanguageORM,
                                     ProjectORM, PublicationORM, AwardORM, CustomSectionORM, SavedCVORM)
from src.database.models.resume import (Experience, Education, Certification, Language, Publication, Project,
                                        Award, CustomSection, JobSeekerCV, SavedCV)
from src.controllers.controller import Controllers, error_handler
import uuid


class ResumeController(Controllers):
    def __init__(self):
        super().__init__()

    def init_app(self, app: Flask):
        super().init_app(app=app)

    @error_handler
    async def create_cv(self, user_uid: str, data: JobSeekerCV) -> dict:
        # Create a new resume with related entries (experience, education, etc.)
        with self.get_session() as session:
            cv_id = str(uuid.uuid4())
            cv = JobSeekerCVORM(
                cv_id=cv_id,
                user_uid=user_uid,
                professional_title=data.professional_title,
                summary=data.summary,
                location=data.location,
                phone=data.phone,
                website=data.website,
                linkedin=data.linkedin,
                github=data.github,
                created_at=datetime.now(UTC),
            )
            session.add(cv)
            await self._save_related_entries(session=session, cv_id=cv_id, data=data)
            return {"cv_id": cv_id, "status": "created"}

    # noinspection DuplicatedCode
    @error_handler
    async def _save_related_entries(self, session, cv_id: str, data: JobSeekerCV):
        # Save nested resume data like experience, education, etc.
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

        for section in data.custom_sections:
            session.add(CustomSectionORM(cv_id=cv_id, **section.model_dump()))

    @error_handler
    async def get_cv_by_id(self, cv_id: str) -> JobSeekerCV | None:
        # Retrieve full CV details including all related data
        with self.get_session() as session:
            # Query for the main CV data
            cv = session.query(JobSeekerCVORM).filter(JobSeekerCVORM.cv_id == cv_id).first()

            if not cv:
                return None  # If CV not found, return None

            # Retrieve all related data using CV ID
            experience_orm_list = session.query(ExperienceORM).filter(ExperienceORM.cv_id == cv_id).all()
            education_orm_list = session.query(EducationORM).filter(EducationORM.cv_id == cv_id).all()
            certifications_orm_list = session.query(CertificationORM).filter(CertificationORM.cv_id == cv_id).all()
            languages_orm_list = session.query(LanguageORM).filter(LanguageORM.cv_id == cv_id).all()
            projects_orm_list = session.query(ProjectORM).filter(ProjectORM.cv_id == cv_id).all()
            publications_orm_list = session.query(PublicationORM).filter(PublicationORM.cv_id == cv_id).all()
            awards_orm_list = session.query(AwardORM).filter(AwardORM.cv_id == cv_id).all()
            custom_sections_orm_list = session.query(CustomSectionORM).filter(CustomSectionORM.cv_id == cv_id).all()

            # Convert all related entries to Pydantic models
            experience_pydantic = [Experience(**exp.to_dict()) for exp in experience_orm_list]
            education_pydantic = [Education(**edu.to_dict()) for edu in education_orm_list]
            certifications_pydantic = [Certification(**cert.to_dict()) for cert in certifications_orm_list]
            languages_pydantic = [Language(**lang.to_dict()) for lang in languages_orm_list]
            projects_pydantic = [Project(**proj.to_dict()) for proj in projects_orm_list]
            publications_pydantic = [Publication(**pub.to_dict()) for pub in publications_orm_list]
            awards_pydantic = [Award(**award.to_dict()) for award in awards_orm_list]
            custom_sections_pydantic = [CustomSection(**section.to_dict()) for section in custom_sections_orm_list]

            # Prepare the result as a Pydantic model for JobSeekerCV
            result = JobSeekerCV(
                cv_id=cv.cv_id,
                user_uid=cv.user_uid,
                professional_title=cv.professional_title,
                summary=cv.summary,
                location=cv.location,
                phone=cv.phone,
                website=cv.website,
                linkedin=cv.linkedin,
                github=cv.github,
                created_at=cv.created_at,
                experience=experience_pydantic,
                education=education_pydantic,
                certifications=certifications_pydantic,
                languages=languages_pydantic,
                projects=projects_pydantic,
                publications=publications_pydantic,
                awards=awards_pydantic,
                custom_sections=custom_sections_pydantic
            )

            return result

    @error_handler
    async def list_cvs_for_user(self, user_uid: str) -> list[JobSeekerCV]:
        # Get all resumes for a specific job seeker
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

    @error_handler
    async def delete_cv(self, cv_id: str) -> bool:
        # Delete a specific CV and its related entries
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
        with self.get_session() as session:
            # Query for CVs where the professional title or summary contains the search query (case-insensitive)
            cvs = session.query(JobSeekerCVORM).filter(
                (JobSeekerCVORM.professional_title.ilike(f"%{query}%")) |
                (JobSeekerCVORM.summary.ilike(f"%{query}%"))
            ).limit(limit).all()

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
    async def notify_admin_of_new_cv(self, user_email: str, cv_id: str):
        # Notify admin via email when a new resume is submitted
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

            await send_mail.send_mail_resend(email=email)
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
            existing_cv.updated_at = datetime.utcnow()

            # Delete old related entries
            for orm_class in [
                ExperienceORM, EducationORM, CertificationORM, LanguageORM,
                ProjectORM, PublicationORM, AwardORM, CustomSectionORM
            ]:
                session.query(orm_class).filter_by(cv_id=cv_id).delete()

            # Add updated related entries
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
        with self.get_session() as session:
            query = session.query(JobSeekerCVORM).filter(
                JobSeekerCVORM.skills.ilike(f"%{skill}%")
            )
            return [JobSeekerCV.model_validate(cv) for cv in query.all()]

    @error_handler
    async def get_cvs_by_location(self, location: str) -> list[JobSeekerCV]:
        """
        Retrieve CVs where the job seeker is located in a specific city or region.

        This method filters JobSeekerCV records using a case-insensitive partial match
        on the `location` field. Useful for employers or admins looking for local candidates.

        :param location: The city, province, or region to filter CVs by.
        :return: A list of JobSeekerCV Pydantic models whose location matches the input.
        """
        with self.get_session() as session:
            query = session.query(JobSeekerCVORM).filter(
                JobSeekerCVORM.location.ilike(f"%{location}%")
            )
            return [JobSeekerCV.model_validate(cv) for cv in query.all()]

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
        with self.get_session() as session:
            query = (
                session.query(JobSeekerCVORM)
                .order_by(JobSeekerCVORM.created_at.desc())
                .limit(limit)
            )
            return [JobSeekerCV.model_validate(cv) for cv in query.all()]

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
        with self.get_session() as session:
            cv = session.query(JobSeekerCVORM).filter_by(id=cv_id).first()
            if not cv:
                return False
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
        with self.get_session() as session:
            cv = session.query(JobSeekerCVORM).filter_by(id=cv_id).first()
            if not cv:
                return False
            cv.is_verified = True
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
            recent_cvs = session.query(JobSeekerCVORM).filter(JobSeekerCVORM.created_at > datetime.now(timezone.utc) - timedelta(days=30)).count()

            # You can also add other stats like the number of CVs in each category or skill, etc.

            return {
                "total_cvs": total_cvs,
                "flagged_cvs": flagged_cvs,
                "verified_cvs": verified_cvs,
                "recent_cvs": recent_cvs
            }

    @error_handler
    async def get_cvs_by_certification(self, cert_name: str) -> list[JobSeekerCV]:
        """
        Filter CVs by a specific certification name.

        This method retrieves all CVs that have the specified certification.

        :param cert_name: The name of the certification to filter by.
        :return: A list of JobSeekerCV Pydantic models representing the CVs with the given certification.
        """
        with self.get_session() as session:
            # Find the certifications matching the provided cert_name
            certifications = session.query(CertificationORM).filter(CertificationORM.name == cert_name).all()

            # Get the unique CV IDs associated with the matching certifications
            cv_ids = [certification.cv_id for certification in certifications]

            # Return the full CV details for each CV ID
            return [await self.get_cv_by_id(cv_id=cv_id) for cv_id in cv_ids]

    @error_handler
    async def get_cvs_by_language(self, language: str) -> list[JobSeekerCV]:
        """
        Filter CVs by known languages.

        This method retrieves all CVs that list the specified language.

        :param language: The name of the language to filter by.
        :return: A list of JobSeekerCV Pydantic models representing the CVs that include the given language.
        """
        with self.get_session() as session:
            # Find the languages matching the provided language
            languages = session.query(LanguageORM).filter(LanguageORM.name == language).all()

            # Get the unique CV IDs associated with the matching languages
            cv_ids = [lang.cv_id for lang in languages]

            # Return the full CV details for each CV ID
            return [await self.get_cv_by_id(cv_id=cv_id) for cv_id in cv_ids]


    async def get_resume_versions(self, cv_id: int):
        """Return all versions for a given resume ID."""
        pass

    async def set_default_resume(self, user_id: int, cv_id: int):
        """Mark one resume as default for the user."""
        pass

    async def download_resume_pdf(self, cv_id: int):
        """Generate and return the PDF download of a resume."""
        pass
