# src/faker/fakeresume.py

import uuid
import random
from datetime import date, timedelta
from faker import Faker

from src.database.models import (
    JobSeekerCV, Experience, Education, Certification, Language, Project,
    Award, CustomSection
)
from src.database.constants import utc_time

faker = Faker()


def generate_fake_cv(user_uid: str, is_primary: bool = False) -> JobSeekerCV:
    def rand_date(start_year=2015, end_year=2023):
        start = date(start_year, 1, 1)
        end = date(end_year, 12, 31)
        return faker.date_between(start, end)

    def random_date_range():
        start = rand_date()
        end = start + timedelta(days=random.randint(180, 1000))
        return start, end if end < date.today() else None

    experience = []
    for _ in range(random.randint(1, 3)):
        start, end = random_date_range()
        experience.append(Experience(
            job_title=faker.job(),
            company=faker.company(),
            start_date=start,
            end_date=end,
            location=faker.city(),
            description=faker.text(max_nb_chars=300)
        ))

    education = []
    for _ in range(random.randint(1, 2)):
        start, end = random_date_range()
        education.append(Education(
            institution=faker.company() + " University",
            qualification=random.choice(["BSc", "MSc", "PhD"]),
            field_of_study=random.choice(["Computer Science", "Information Systems", "Engineering"]),
            start_date=start,
            end_date=end,
            description=faker.sentence()
        ))

    certifications = [
        Certification(
            name="Certified Kubernetes Admin",
            issuer="CNCF",
            issue_date=rand_date(2020, 2023),
            expiry_date=None,
            credential_url="https://example.com/cert"
        )
    ]

    languages = [
        Language(name="English", proficiency="Fluent"),
        Language(name="German", proficiency="Intermediate")
    ]

    projects = [
        Project(
            title="Portfolio Website",
            description="A personal website showcasing my projects.",
            technologies=["React", "Tailwind", "Vite"],
            link="https://github.com/example"
        )
    ]

    awards = [
        Award(
            title="Employee of the Year",
            issuer="TechCorp",
            date=rand_date(2022, 2023),
            description="Awarded for outstanding performance."
        )
    ]

    custom_sections = [
        CustomSection(
            title="Volunteer Experience",
            content=["Mentor at Code Club", "Organizer of DevCon"]
        )
    ]

    skills = random.sample([
        "Python", "JavaScript", "Docker", "Kubernetes", "React", "FastAPI",
        "PostgreSQL", "CI/CD", "AWS", "Linux"
    ], k=6)

    return JobSeekerCV(
        user_uid=user_uid,
        is_primary=is_primary,
        professional_title=faker.job(),
        summary=faker.text(max_nb_chars=150),
        location=faker.city(),
        phone=faker.phone_number(),
        website=faker.url(),
        linkedin="https://linkedin.com/in/" + faker.user_name(),
        github="https://github.com/" + faker.user_name(),
        skills=skills,
        experience=experience,
        education=education,
        certifications=certifications,
        languages=languages,
        projects=projects,
        publications=[],
        awards=awards,
        custom_sections=custom_sections,
        portfolio_links=[faker.url()],
        resume_file_url=faker.url(),
        profile_image_url=faker.image_url()
    )
