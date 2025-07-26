from src.database import *
from src.database.sql import Base, engine
def boot():
    try:

        # PromptMutationLogORM.delete_table()
        # # PromptORM.delete_table()
        # # BlogPromptORM.delete_table()
        # BlogTopicORM.delete_table()
        # ArticleORM.delete_table()
        # ScheduledPostORM.delete_table()
        # PerformanceORM.delete_table()
        #

        # run once, before anything else
        # BlogPromptORM.delete_table()  # drops if it exists
        # BlogPromptORM.create_if_not_table()  # re-creates with the correct columns
        # PromptMutationLogORM.create_if_not_table()

        Base.metadata.drop_all(bind=engine, checkfirst=True)
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