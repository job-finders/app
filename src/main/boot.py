from src.database import *
from src.database.sql import Base, engine
def boot():
    try:
        # JobViewActivityORM.delete_table()
        # JobApprovalRequestORM.delete_table()
        # ApplicationStepORM.delete_table()
        # JobApplicationORM.delete_table()
        # ATSReportORM.delete_table()
        # SavedJobORM.delete_table()
        # JobVersionHistoryORM.delete_table()
        # JobsORM.delete_table()
        # JobCategoryORM.delete_table()

        #
        # Drop all existing tables first
        print("Dropping all existing database tables...")
        # Base.metadata.drop_all(bind=engine)
        # Create all tables from scratch
        print("Creating new database schema...")
        Base.metadata.create_all(bind=engine)
        print("Database reset complete!")
        print("Tables SQLAlchemy sees:", Base.metadata.tables.keys())

    except Exception as e:
        print(f"Database reset failed: {str(e)}")