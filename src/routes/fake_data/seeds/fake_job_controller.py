import uuid
from datetime import timezone, datetime, timedelta
import random

from src.database.models import Job
from src.routes.fake_data import store


def generate_mock_jobs(keyword: str, count: int = 5) -> list[Job]:
    """Generate mock job listings for demonstration purposes""
    # Check if we already have mock jobs for this keyword
    """

    titles = [
        f"Senior {keyword} Developer",
        f"{keyword} Specialist",
        f"Junior {keyword} Engineer",
        f"{keyword} Team Lead",
        f"{keyword} Product Manager"
    ]

    companies = [
        "Tech Innovations Inc.",
        "Digital Solutions Ltd.",
        "Future Systems Corp.",
        "Global Tech Partners",
        "InnovateX Technologies"
    ]

    cities = ["Cape Town", "Johannesburg", "Durban", "Pretoria", "Port Elizabeth"]
    provinces = ["Western Cape", "Gauteng", "KwaZulu-Natal", "Eastern Cape"]
    job_types = ["FULL_TIME", "PART_TIME", "CONTRACT"]
    remote_policies = ["REMOTE", "HYBRID", "ONSITE"]
    experience_levels = ["ENTRY", "MID", "SENIOR"]

    for i in range(count):
        posted_at = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))
        salary_min = random.randint(20000, 50000)
        salary_max = salary_min + random.randint(10000, 30000)

        job = Job(**{
            "job_id": str(uuid.uuid4()),
            "title": random.choice(titles),
            "company": {
                "name": random.choice(companies),
                "logo_url": None
            },
            "position_type": random.choice(job_types),
            "remote_policy": random.choice(remote_policies),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "ZAR",
            "city": random.choice(cities),
            "province": random.choice(provinces),
            "country": "South Africa",
            "posted_at": posted_at,
            "expires_at": posted_at + timedelta(days=60),
            "experience_level": random.choice(experience_levels),
            "description": f"We're looking for a talented {keyword} professional to join our team. "
                           f"You'll work on cutting-edge {keyword} solutions and collaborate with "
                           "a team of passionate engineers. Apply now!",
            "application_count": random.randint(0, 50),
            "view_count": random.randint(10, 200),
            "is_featured": i == 0,
            "location": f"{random.choice(cities)}, {random.choice(provinces)}, South Africa",
            "salary": f"ZAR {salary_min} - {salary_max}",
            "is_active": True,
            "status": "active",
            "application_instructions": "Apply online through our portal."
        })
        store.jobs[job.job_id] = job

    return job
