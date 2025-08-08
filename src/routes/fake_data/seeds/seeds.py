import uuid
from datetime import datetime, timedelta
import random
from faker import Faker
from typing import Dict, List

from src.database.models import (
    Job,
    Company,
    JobSeekerCV,
    ATSReport,
    JobApplication,
    JobSeekerProfile,
    JobApplicationStatusEnum
)
from src.routes.fake_data import store
from src.database.constants import utc_time

fake = Faker()

class FakeDataGenerator:
    def __init__(self):
        self.clear_store()
        
    def clear_store(self):
        """Clear all existing fake data"""
        store.clear_store()
        
    def generate_company(self) -> Company:
        """Generate a fake company"""
        company_id = str(uuid.uuid4())
        company = Company(
            company_id=company_id,
            name=fake.company(),
            description=fake.catch_phrase(),
            website=fake.url(),
            logo_url=fake.image_url(),
            industry=random.choice(["Tech", "Finance", "Healthcare", "Education"]),
            founded_year=random.randint(1990, 2020),
            employee_count=random.randint(10, 10000),
            hq_location=f"{fake.city()}, {fake.country()}",
            is_active=True
        )
        store.companies[company_id] = company
        return company
        
    def generate_job(self, company_id: str) -> Job:
        """Generate a fake job for given company"""
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            company_id=company_id,
            title=fake.job(),
            description=fake.paragraph(nb_sentences=5),
            requirements="\n".join(fake.sentences(nb=3)),
            responsibilities="\n".join(fake.sentences(nb=3)),
            location=f"{fake.city()}, {fake.country()}",
            salary_min=random.randint(20000, 100000),
            salary_max=random.randint(100000, 200000),
            salary_currency="ZAR",
            posted_at=utc_time() - timedelta(days=random.randint(0, 30)),
            expires_at=utc_time() + timedelta(days=random.randint(30, 90)),
            is_active=True,
            application_count=random.randint(0, 50),
            view_count=random.randint(10, 200)
        )
        store.jobs[job_id] = job
        return job
        
    def generate_jobseeker_profile(self) -> JobSeekerProfile:
        """Generate a fake job seeker profile"""
        user_uid = str(uuid.uuid4())
        
        profile = JobSeekerProfile(
            user_uid=user_uid,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            phone=fake.phone_number(),
            location=f"{fake.city()}, {fake.country()}",
            bio=fake.paragraph(nb_sentences=2),
            skills=[fake.word() for _ in range(5)],
            experience_years=random.randint(0, 20),
            education=fake.sentence(),
            is_active=True
        )
        store.jobseekers[user_uid] = profile
        return profile
        
    def generate_resume(self, user_uid: str) -> JobSeekerCV:
        """Generate a fake resume for given user"""
        cv_id = str(uuid.uuid4())
        
        resume = JobSeekerCV(
            cv_id=cv_id,
            user_uid=user_uid,
            content=fake.paragraph(nb_sentences=10),
            skills=[fake.word() for _ in range(10)],
            experience=[fake.sentence() for _ in range(3)],
            education=fake.sentence(),
            is_primary=True
        )
        store.resumes[cv_id] = resume
        return resume
        
    def generate_ats_report(self, job_id: str, cv_id: str) -> ATSReport:
        """Generate a fake ATS report for job application"""
        ats_id = str(uuid.uuid4())
        
        report = ATSReport(
            ats_report_id=ats_id,
            job_id=job_id,
            cv_id=cv_id,
            score=random.randint(50, 100),
            keywords_matched=random.randint(5, 15),
            missing_keywords=random.randint(0, 5),
            summary=fake.paragraph(nb_sentences=2),
            created_at=utc_time()
        )
        store.ats_reports[ats_id] = report
        return report
        
    def generate_job_application(self, job_id: str, user_uid: str, cv_id: str, ats_id: str) -> JobApplication:
        """Generate a fake job application"""
        application_id = str(uuid.uuid4())
        
        application = JobApplication(
            application_id=application_id,
            job_id=job_id,
            user_id=user_uid,
            cv_id=cv_id,
            ats_report_id=ats_id,
            cover_letter=fake.paragraph(nb_sentences=5),
            status=random.choice(list(JobApplicationStatusEnum)).value,
            applied_date=utc_time() - timedelta(days=random.randint(0, 30)),
            updated_at=utc_time()
        )
        store.job_applications[application_id] = application
        return application
        
    def generate_full_pipeline(self, count: int = 5) -> Dict[str, List]:
        """Generate complete set of related fake data"""
        results = {
            'companies': [],
            'jobs': [],
            'profiles': [],
            'resumes': [],
            'ats_reports': [],
            'applications': []
        }
        
        for _ in range(count):
            # Generate company and jobs
            company = self.generate_company()
            job = self.generate_job(company.company_id)
            
            # Generate job seeker profile and resume
            profile = self.generate_jobseeker_profile()
            resume = self.generate_resume(profile.user_uid)
            
            # Generate ATS report and application
            ats_report = self.generate_ats_report(job.job_id, resume.cv_id)
            application = self.generate_job_application(
                job.job_id,
                profile.user_uid,
                resume.cv_id,
                ats_report.ats_report_id
            )
            
            # Store references
            results['companies'].append(company)
            results['jobs'].append(job)
            results['profiles'].append(profile)
            results['resumes'].append(resume)
            results['ats_reports'].append(ats_report)
            results['applications'].append(application)
            
        return results

# Singleton instance for easy access
fake_data_generator = FakeDataGenerator()
