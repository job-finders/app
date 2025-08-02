
from src.database import *
from src.database.sql import Base, engine


def boot():
    try:
        # InvoiceORM.delete_table()
        # PaymentMethodORM.delete_table()
        # BillingEventORM.delete_table()
        # CompanyBillingProfileORM.delete_table()

        # Create all tables from scratch
        print("Creating new database schema...")
        Base.metadata.create_all(bind=engine)
        print("Database reset complete!")
        print("Tables SQLAlchemy sees:", Base.metadata.tables.keys())

    except Exception as e:
        print(f"Database reset failed: {str(e)}")