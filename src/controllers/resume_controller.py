from datetime import datetime
from flask import Flask
from src.main import send_mail
from src.emailer import EmailModel
from src.database.sql.resume import (
    JobSeekerCVORM, ExperienceORM, EducationORM, CertificationORM, LanguageORM,
    ProjectORM, PublicationORM, AwardORM, CustomSectionORM
)
from src.database.models.resume import (
    Experience, Education, Certification, Language, Publication, Project,
    Award, CustomSection, JobSeekerCV
)
from src.controllers.controller import Controllers

import uuid


class ResumeController(Controllers):
    def __init__(self):
        super().__init__()

    def init_app(self, app: Flask):
        super().init_app(app=app)

    def create_cv(self, user_uid: str, data: JobSeekerCV) -> dict:
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
                created_at=datetime.utcnow(),
            )
            session.add(cv)
            self._save_related_entries(session, cv_id, data)
            return {"cv_id": cv_id, "status": "created"}

    def _save_related_entries(self, session, cv_id: str, data: JobSeekerCV):
        # Save nested resume data like experience, education, etc.
        for exp in data.experience:
            session.add(ExperienceORM(cv_id=cv_id, **exp.dict()))

        for edu in data.education:
            session.add(EducationORM(cv_id=cv_id, **edu.dict()))

        for cert in data.certifications:
            session.add(CertificationORM(cv_id=cv_id, **cert.dict()))

        for lang in data.languages:
            session.add(LanguageORM(cv_id=cv_id, **lang.dict()))

        for proj in data.projects:
            session.add(ProjectORM(cv_id=cv_id, **proj.dict()))

        for pub in data.publications:
            session.add(PublicationORM(cv_id=cv_id, **pub.dict()))

        for award in data.awards:
            session.add(AwardORM(cv_id=cv_id, **award.dict()))

        for section in data.custom_sections:
            session.add(CustomSectionORM(cv_id=cv_id, **section.dict()))

    def get_cv_by_id(self, cv_id: str) -> JobSeekerCV | None:
        # Retrieve full CV details including all related data
        with self.get_session() as session:
            # Query for the main CV data
            cv = session.query(JobSeekerCVORM).filter(JobSeekerCVORM.cv_id == cv_id).first()

            if not cv:
                return None  # If CV not found, return None

            # Retrieve all related data using CV ID
            experience = session.query(ExperienceORM).filter(ExperienceORM.cv_id == cv_id).all()
            education = session.query(EducationORM).filter(EducationORM.cv_id == cv_id).all()
            certifications = session.query(CertificationORM).filter(CertificationORM.cv_id == cv_id).all()
            languages = session.query(LanguageORM).filter(LanguageORM.cv_id == cv_id).all()
            projects = session.query(ProjectORM).filter(ProjectORM.cv_id == cv_id).all()
            publications = session.query(PublicationORM).filter(PublicationORM.cv_id == cv_id).all()
            awards = session.query(AwardORM).filter(AwardORM.cv_id == cv_id).all()
            custom_sections = session.query(CustomSectionORM).filter(CustomSectionORM.cv_id == cv_id).all()

            # Convert all related entries to Pydantic models
            experience_pydantic = [Experience.from_orm(exp) for exp in experience]
            education_pydantic = [Education.from_orm(edu) for edu in education]
            certifications_pydantic = [Certification.from_orm(cert) for cert in certifications]
            languages_pydantic = [Language.from_orm(lang) for lang in languages]
            projects_pydantic = [Project.from_orm(proj) for proj in projects]
            publications_pydantic = [Publication.from_orm(pub) for pub in publications]
            awards_pydantic = [Award.from_orm(award) for award in awards]
            custom_sections_pydantic = [CustomSection.from_orm(section) for section in custom_sections]

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

    def list_cvs_for_user(self, user_uid: str) -> list[JobSeekerCV]:
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
                experience = session.query(ExperienceORM).filter(ExperienceORM.cv_id == cv.cv_id).all()
                education = session.query(EducationORM).filter(EducationORM.cv_id == cv.cv_id).all()
                certifications = session.query(CertificationORM).filter(CertificationORM.cv_id == cv.cv_id).all()
                languages = session.query(LanguageORM).filter(LanguageORM.cv_id == cv.cv_id).all()
                projects = session.query(ProjectORM).filter(ProjectORM.cv_id == cv.cv_id).all()
                publications = session.query(PublicationORM).filter(PublicationORM.cv_id == cv.cv_id).all()
                awards = session.query(AwardORM).filter(AwardORM.cv_id == cv.cv_id).all()
                custom_sections = session.query(CustomSectionORM).filter(CustomSectionORM.cv_id == cv.cv_id).all()

                # Convert all related entries to Pydantic models
                experience_pydantic = [Experience.from_orm(exp) for exp in experience]
                education_pydantic = [Education.from_orm(edu) for edu in education]
                certifications_pydantic = [Certification.from_orm(cert) for cert in certifications]
                languages_pydantic = [Language.from_orm(lang) for lang in languages]
                projects_pydantic = [Project.from_orm(proj) for proj in projects]
                publications_pydantic = [Publication.from_orm(pub) for pub in publications]
                awards_pydantic = [Award.from_orm(award) for award in awards]
                custom_sections_pydantic = [CustomSection.from_orm(section) for section in custom_sections]

                # Create Pydantic model for the CV
                cv_pydantic = JobSeekerCV(
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

                result.append(cv_pydantic)

            return result

    def delete_cv(self, cv_id: str) -> bool:
        # Delete a specific CV and its related entries
        with self.get_session() as session:


    def search_cvs(self, query: str, limit: int = 10) -> list[dict]:
        # Search for resumes using professional title or keyword
        pass

    def notify_admin_of_new_cv(self, user_email: str, cv_id: str):
        # Notify admin via email when a new resume is submitted
        pass

    def update_cv(self, cv_id: str, data: JobSeekerCV) -> bool:
        # Update an existing CV and its related entries
        pass

    def get_cvs_by_skill(self, skill: str) -> list[dict]:
        # Get resumes where the job seeker has a given skill
        pass

    def get_cvs_by_location(self, location: str) -> list[dict]:
        # Get resumes where job seekers are located in a specific city or region
        pass

    def get_recent_cvs(self, limit: int = 10) -> list[dict]:
        # Fetch the most recently created CVs (for admin/employer dashboard)
        pass

    def flag_cv_for_review(self, cv_id: str, reason: str) -> bool:
        # Admin action to flag a CV for further review
        pass

    def mark_cv_as_verified(self, cv_id: str) -> bool:
        # Admin action to mark a CV as verified
        pass

    def employer_save_cv(self, employer_uid: str, cv_id: str) -> bool:
        # Employer action to bookmark/save a CV for later
        pass

    def employer_saved_cvs(self, employer_uid: str) -> list[dict]:
        # Get list of CVs saved/bookmarked by an employer
        pass

    def get_cv_statistics(self) -> dict:
        # Admin stats: total CVs, flagged, verified, recent, etc.
        pass

    def get_cvs_by_certification(self, cert_name: str) -> list[dict]:
        # Filter CVs by a specific certification name
        pass

    def get_cvs_by_language(self, language: str) -> list[dict]:
        # Filter CVs by known languages
        pass
