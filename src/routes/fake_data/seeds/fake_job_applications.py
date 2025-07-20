from src.database.constants import utc_time
from src.database.models import JobApplication, JobApplicationStatusEnum
import uuid
import random
from datetime import timedelta

def generate_fake_job_application(job_id: str, user_id: str = None, stage: str = None) -> JobApplication:
    """
    Generate a fake JobApplication with a realistic CV and an ATS Report.
    If no user_id is provided, a new JobSeekerProfile will be created.
    """
    from .fake_jobseeker_profile import generate_fake_jobseeker_profile
    from .fake_resume import generate_fake_cv
    from .fake_ats_report import generate_fake_ats_report

    profile = None
    fake_cv = None

    # Create or load a fake JobSeekerProfile
    if not user_id:
        profile = generate_fake_jobseeker_profile()
        user_id = profile.user_uid
    else:
        # If a user_id is provided but no profile, you might want to retrieve one here in real scenarios.
        profile = None  # Placeholder — fetch logic if needed

    # Generate or reuse a fake CV
    if not profile or not profile.resumes_list:
        fake_cv = generate_fake_cv(user_uid=user_id)
    else:
        fake_cv = profile.resumes_list[-1]

    cv_id = fake_cv.cv_id

    # Generate ATS Report for the selected CV
    ats_report = generate_fake_ats_report(job_id=job_id, cv_id=cv_id)

    applied_days_ago = random.randint(1, 10)
    application_stage = stage or random.choice(list(JobApplicationStatusEnum.__members__.values())).value

    return JobApplication(
        application_id=str(uuid.uuid4()),
        user_id=user_id,
        job_id=job_id,
        cv_id=cv_id,
        ats_report_id=ats_report.ats_report_id,
        ats_report=ats_report,
        applied_date=utc_time() - timedelta(days=applied_days_ago),
        updated_at=utc_time(),
        application_stage=application_stage,
        expected_salary=random.randint(60000, 120000),
        preferred_location=random.choice(["Remote", "New York", "Berlin", "Toronto", None]),
        required_documents=random.sample(["resume", "cover_letter", "portfolio"], k=random.randint(1, 2)),
        questionnaire_answers={
            "q1": [random.choice(["Yes", "No"])],
            "q2": [random.choice(["Yes", "No"])]
        },
        validation_score=random.randint(40, 100),
        review_summary=random.choice([
            "Excellent React developer",
            "Strong backend profile",
            "Junior-level candidate",
            "Limited experience but promising"
        ]),

        cover_letter=generate_cover_letters(),
        jobseeker_profile=profile  # ✅ Include the full profile
    )


def generate_cover_letters() -> str:
    """Generate long-form cover letters for job applications."""
    openings = [
        "Dear Hiring Team,",
        "To whom it may concern,",
        "Dear [Company Name] Recruitment Team,",
        "Hello and thank you for considering my application,",
    ]

    intros = [
        "I am writing to express my strong interest in the [Job Title] role at your company. "
        "With a passion for building scalable web applications and a deep understanding of modern development practices, "
        "I believe I can make an immediate and meaningful contribution to your team.",

        "As a dedicated software engineer with experience in Python, JavaScript, and cloud-native technologies, "
        "I was excited to see the opening for the [Job Title] position. I am confident that my background in both frontend and backend systems "
        "makes me a strong candidate for this opportunity.",

        "Having followed your company's work on innovation and product excellence, I am eager to apply for the [Job Title] role. "
        "My technical background and passion for clean, maintainable code align well with your mission and values."
    ]

    bodies = [
        "In my previous role, I led the migration of a monolithic application to a microservices architecture, reducing deployment time by 60%. "
        "I’ve also built real-time data processing pipelines using Kafka and Spark, and am comfortable navigating both startup and enterprise-scale environments. "
        "Beyond technical contributions, I actively mentor junior developers and advocate for inclusive team cultures.",

        "I have worked on multiple projects involving RESTful APIs, modern UI libraries like React and Vue, and cloud platforms such as AWS and GCP. "
        "I'm a strong believer in testing, automation, and continuous delivery, and have experience implementing CI/CD pipelines using GitHub Actions and Jenkins. "
        "Collaboration, ownership, and adaptability are values I bring to every team I join.",

        "What excites me most about this opportunity is the chance to work on impactful products that reach a broad audience. "
        "I thrive in fast-paced environments and enjoy solving problems that require both technical rigor and creative thinking. "
        "I am continuously learning and staying up-to-date with trends in distributed systems, security, and developer tooling."
    ]

    closings = [
        "I would welcome the opportunity to speak with you further about how I can contribute to your engineering team. "
        "Thank you for considering my application.",

        "Please find my resume attached. I look forward to the possibility of contributing to your team’s success.",

        "Thank you for your time and consideration. I’m eager to discuss how my experience can help your company thrive."
    ]

    sign_offs = [
        "Sincerely,\nJane Doe",
        "Best regards,\nJohn Applicant",
        "Kindly,\nA Passionate Engineer",
    ]

    import random
    def random_paragraph(paragraphs):
        return random.choice(paragraphs)

    # Construct the final cover letter
    letter = "\n\n".join([
        random_paragraph(openings),
        random_paragraph(intros).replace("[Job Title]", random.choice(
            ["Software Engineer", "Backend Developer", "Full Stack Engineer"])),
        random_paragraph(bodies),
        random_paragraph(closings),
        random_paragraph(sign_offs)
    ])

    return letter
