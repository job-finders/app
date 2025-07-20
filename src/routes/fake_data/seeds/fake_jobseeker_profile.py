# fake_jobseeker_profile.py

import uuid
import random
from datetime import timedelta
from faker import Faker

from src.database.constants import utc_time
from src.database.models import JobSeekerProfile, JobSeekerCV

fake = Faker()


def generate_fake_jobseeker_profile(user_uid: str = None, include_resume: bool = True) -> JobSeekerProfile:
    """
    Generate a realistic JobSeekerProfile object with optional fake resume.
    """
    if not user_uid:
        user_uid = user_uid or str(uuid.uuid4())
    cv = None

    if include_resume:
        from .fake_resume import generate_fake_cv
        cv = generate_fake_cv(user_uid=user_uid, is_primary=True)

    return JobSeekerProfile(
        user_uid=user_uid,
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        bio=fake.sentence(nb_words=20),
        profile_image_url=fake.image_url(),
        verified_email=random.choice([True, False]),
        verified_phone=random.choice([True, False]),
        verified_linkedin=random.choice([True, False]),
        verified_github=random.choice([True, False]),
        phone=fake.phone_number(),
        location=fake.city(),
        website=fake.url(),
        linkedin=f"https://linkedin.com/in/{fake.user_name()}",
        github=f"https://github.com/{fake.user_name()}",
        job_titles_of_interest=random.sample(["Frontend Developer", "Backend Engineer", "Data Analyst", "DevOps"], k=2),
        industries_of_interest=random.sample(["Tech", "Finance", "Healthcare"], k=2),
        locations_of_interest=random.sample(["Remote", "New York", "London"], k=2),
        remote_preference=random.choice([True, False]),
        availability=random.choice(["Immediate", "2 weeks", "1 month"]),
        is_freelancer=random.choice([True, False]),
        freelance_skills=["Python", "React", "Docker"] if random.choice([True, False]) else [],
        hourly_rate=random.uniform(20.0, 120.0),
        freelance_experience=fake.paragraph() if random.choice([True, False]) else None,
        freelance_availability=random.choice(["Weekends", "Evenings", "Full-time"]),
        alerts_enabled=True,
        receive_deadline_reminders=True,
        reminder_days_before=7,
        receive_company_updates=True,
        visibility=True,
        last_updated=utc_time(),
        ip_address=fake.ipv4(),
        device_finger_print=uuid.uuid4().hex,
        resumes_list=[cv] if cv else [],
    )
