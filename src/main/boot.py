import time

def boot():
    # Import ORM classes for jobs, users, and resumes
    from src.database.sql.jobs import JobsORM
    from src.database.sql.users import UserORM
    from src.database.sql.resume import (JobSeekerCVORM, ExperienceORM, EducationORM, CertificationORM, LanguageORM,
                                         ProjectORM, PublicationORM, AwardORM, CustomSectionORM, SavedCVORM)

    # Ensure that jobseeker_cvs is created first
    classes_to_create = [JobsORM, UserORM, JobSeekerCVORM, ExperienceORM, EducationORM, CertificationORM, LanguageORM,
                         ProjectORM, PublicationORM, AwardORM, CustomSectionORM, SavedCVORM]

    # Loop through the classes and ensure the tables are created in order
    for cls in classes_to_create:
        try:
            cls.create_if_not_table()
            print(f"Table for {cls.__tablename__} created or already exists.")
        except Exception as e:
            print(f"Error creating table for {cls.__tablename__}: {str(e)}")

        # Sleep for 2 seconds to avoid overwhelming the database
        time.sleep(2)
