"""
Database migration script to add workflow fields to job_applications table

This script adds the necessary columns for the job application workflow system
including workflow step tracking, cover letter sessions, and questionnaire timing.
"""

from sqlalchemy import text
from src.database import get_session
from src.logger import init_logger

logger = init_logger(__name__)


def add_workflow_columns():
    """Add workflow columns to job_applications table"""
    
    # SQL statements to add new columns
    add_columns_sql = [
        """
        ALTER TABLE job_applications 
        ADD COLUMN workflow_step VARCHAR(50) NOT NULL DEFAULT 'draft'
        """,
        """
        ALTER TABLE job_applications 
        ADD COLUMN cover_letter_session_id VARCHAR(36) NULL
        """,
        """
        ALTER TABLE job_applications 
        ADD COLUMN questionnaire_start_time DATETIME NULL
        """,
        """
        ALTER TABLE job_applications 
        ADD COLUMN questionnaire_completion_time DATETIME NULL
        """,
        """
        ALTER TABLE job_applications 
        ADD COLUMN time_spent_on_questionnaires INT NULL
        """,
        """
        ALTER TABLE job_applications 
        ADD COLUMN workflow_started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        """,
        """
        ALTER TABLE job_applications 
        ADD COLUMN workflow_completed_at DATETIME NULL
        """
    ]
    
    # SQL statements to add indexes for performance
    add_indexes_sql = [
        """
        CREATE INDEX idx_job_applications_workflow_step 
        ON job_applications(workflow_step)
        """,
        """
        CREATE INDEX idx_job_applications_cover_session 
        ON job_applications(cover_letter_session_id)
        """,
        """
        CREATE INDEX idx_job_applications_workflow_started 
        ON job_applications(workflow_started_at)
        """,
        """
        CREATE INDEX idx_job_applications_workflow_completed 
        ON job_applications(workflow_completed_at)
        """,
        """
        CREATE INDEX idx_job_applications_questionnaire_timing 
        ON job_applications(questionnaire_start_time, questionnaire_completion_time)
        """
    ]
    
    with get_session() as session:
        try:
            # Add columns
            for i, sql in enumerate(add_columns_sql, 1):
                logger.info(f"Adding workflow column {i}/{len(add_columns_sql)}")
                try:
                    session.execute(text(sql))
                    logger.info(f"Successfully added column {i}")
                except Exception as e:
                    if "Duplicate column name" in str(e) or "already exists" in str(e):
                        logger.info(f"Column {i} already exists, skipping")
                    else:
                        raise e
            
            # Add indexes
            for i, sql in enumerate(add_indexes_sql, 1):
                logger.info(f"Adding workflow index {i}/{len(add_indexes_sql)}")
                try:
                    session.execute(text(sql))
                    logger.info(f"Successfully added index {i}")
                except Exception as e:
                    if "Duplicate key name" in str(e) or "already exists" in str(e):
                        logger.info(f"Index {i} already exists, skipping")
                    else:
                        raise e
            
            session.commit()
            logger.info("Job application workflow columns added successfully")
            
        except Exception as e:
            logger.error(f"Error adding workflow columns: {e}")
            session.rollback()
            raise


def update_existing_applications():
    """Update existing applications to have proper workflow state"""
    
    update_sql = """
    UPDATE job_applications 
    SET workflow_step = CASE 
        WHEN application_stage = 'APPLIED' OR application_stage = 'Applied' THEN 'submitted'
        WHEN application_stage = 'DRAFT' OR application_stage = 'Draft' THEN 'draft'
        WHEN cover_letter IS NOT NULL AND cover_letter != '' THEN 'review'
        ELSE 'draft'
    END,
    workflow_started_at = COALESCE(workflow_started_at, applied_date, created_at, NOW()),
    workflow_completed_at = CASE 
        WHEN application_stage = 'APPLIED' OR application_stage = 'Applied' THEN applied_date
        ELSE NULL
    END
    WHERE workflow_step = 'draft' OR workflow_step IS NULL
    """
    
    with get_session() as session:
        try:
            logger.info("Updating existing applications with workflow state")
            result = session.execute(text(update_sql))
            updated_count = result.rowcount
            session.commit()
            logger.info(f"Updated {updated_count} existing applications")
            
        except Exception as e:
            logger.error(f"Error updating existing applications: {e}")
            session.rollback()
            raise


def add_foreign_key_constraints():
    """Add foreign key constraints for new relationships"""
    
    # Note: We can't add FK to cover_letter_sessions table until it exists
    # This will be handled when the questionnaire tables migration runs
    
    constraints_sql = [
        """
        ALTER TABLE job_applications 
        ADD CONSTRAINT fk_job_applications_cover_session 
        FOREIGN KEY (cover_letter_session_id) 
        REFERENCES cover_letter_sessions(session_id) 
        ON DELETE SET NULL
        """
    ]
    
    with get_session() as session:
        try:
            for i, sql in enumerate(constraints_sql, 1):
                logger.info(f"Adding foreign key constraint {i}")
                try:
                    session.execute(text(sql))
                    logger.info(f"Successfully added constraint {i}")
                except Exception as e:
                    if "already exists" in str(e) or "Duplicate" in str(e):
                        logger.info(f"Constraint {i} already exists, skipping")
                    elif "doesn't exist" in str(e) or "Unknown table" in str(e):
                        logger.info(f"Referenced table doesn't exist yet, skipping constraint {i}")
                    else:
                        logger.warning(f"Could not add constraint {i}: {e}")
            
            session.commit()
            logger.info("Foreign key constraints processed")
            
        except Exception as e:
            logger.error(f"Error adding foreign key constraints: {e}")
            session.rollback()
            # Don't raise here as constraints are optional


def run_migration():
    """Run the complete migration"""
    try:
        logger.info("Starting job application workflow migration...")
        add_workflow_columns()
        update_existing_applications()
        add_foreign_key_constraints()
        logger.info("Job application workflow migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def rollback_migration():
    """Rollback the migration (remove added columns)"""
    
    rollback_sql = [
        "ALTER TABLE job_applications DROP COLUMN IF EXISTS workflow_completed_at",
        "ALTER TABLE job_applications DROP COLUMN IF EXISTS workflow_started_at", 
        "ALTER TABLE job_applications DROP COLUMN IF EXISTS time_spent_on_questionnaires",
        "ALTER TABLE job_applications DROP COLUMN IF EXISTS questionnaire_completion_time",
        "ALTER TABLE job_applications DROP COLUMN IF EXISTS questionnaire_start_time",
        "ALTER TABLE job_applications DROP COLUMN IF EXISTS cover_letter_session_id",
        "ALTER TABLE job_applications DROP COLUMN IF EXISTS workflow_step"
    ]
    
    with get_session() as session:
        try:
            logger.info("Rolling back job application workflow migration...")
            for sql in rollback_sql:
                try:
                    session.execute(text(sql))
                except Exception as e:
                    logger.warning(f"Could not execute rollback SQL: {e}")
            
            session.commit()
            logger.info("Rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            session.rollback()
            return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_migration()
        if success:
            print("✅ Job application workflow migration rolled back successfully")
        else:
            print("❌ Rollback failed - check logs for details")
            exit(1)
    else:
        success = run_migration()
        if success:
            print("✅ Job application workflow migration completed successfully")
        else:
            print("❌ Migration failed - check logs for details")
            exit(1)