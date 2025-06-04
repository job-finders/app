from src.database.sql import Base, engine


def boot():
    try:
        # Drop all existing tables first
        print("Dropping all existing database tables...")
        Base.metadata.drop_all(bind=engine)

        # Create all tables from scratch
        print("Creating new database schema...")
        Base.metadata.create_all(bind=engine)

        print("Database reset complete!")
    except Exception as e:
        print(f"Database reset failed: {str(e)}")