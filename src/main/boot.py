import time

def boot():
    # Import ORM classes for jobs, users, and resumes
    from src.database.sql.jobs_sql import JobsORM, SavedJobORM,  JobApplicationORM
    from src.database.sql.users import UserORM
    from src.database.sql.resume import (JobSeekerCVORM, ExperienceORM, EducationORM, CertificationORM, LanguageORM,
                                         ProjectORM, PublicationORM, AwardORM, CustomSectionORM, SavedCVORM)
    from src.database.sql.jobseeker_profile import JobSeekerProfileORM
    from src.database.sql.config import ConfigurationORM

    # Ensure that jobseeker_cvs is created first
    classes_to_create = [JobsORM, UserORM, JobSeekerCVORM, ExperienceORM, EducationORM, CertificationORM, LanguageORM,
                         ProjectORM, PublicationORM, AwardORM, CustomSectionORM, SavedCVORM, SavedJobORM,
                         JobApplicationORM, JobSeekerProfileORM, ConfigurationORM]

    create_classes = True
    if create_classes:
    # Loop through the classes and ensure the tables are created in order
        for cls in classes_to_create:
            try:
                cls.create_if_not_table()
                # print(f"Table for {cls.__tablename__} created or already exists.")
            except Exception as e:
                # print(f"Error creating table for {cls.__tablename__}: {str(e)}")
                pass
            # Sleep for 2 seconds to avoid overwhelming the database
