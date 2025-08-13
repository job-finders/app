"""
Database migration script for questionnaire system tables

This script creates the necessary tables for the job application workflow
questionnaire system including questionnaires, questions, submissions, and cover letter sessions.
"""

from sqlalchemy import text
from src.database import get_session
from src.logger import init_logger

logger = init_logger(__name__)


def create_questionnaire_tables():
    """Create all questionnaire-related tables"""
    
    # SQL statements for table creation
    create_questionnaires_table = """
    CREATE TABLE IF NOT EXISTS questionnaires (
        questionnaire_id VARCHAR(36) PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        time_limit INT NOT NULL DEFAULT 30,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_questionnaires_active (is_active),
        INDEX idx_questionnaires_created (created_at),
        INDEX idx_questionnaires_title (title)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    create_questionnaire_questions_table = """
    CREATE TABLE IF NOT EXISTS questionnaire_questions (
        question_id VARCHAR(36) PRIMARY KEY,
        questionnaire_id VARCHAR(36) NOT NULL,
        question_text TEXT NOT NULL,
        question_type VARCHAR(20) NOT NULL,
        required BOOLEAN NOT NULL DEFAULT TRUE,
        options JSON,
        max_length INT,
        min_rating INT,
        max_rating INT,
        order_index INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (questionnaire_id) REFERENCES questionnaires(questionnaire_id) ON DELETE CASCADE,
        INDEX idx_questions_questionnaire (questionnaire_id),
        INDEX idx_questions_order (questionnaire_id, order_index),
        INDEX idx_questions_type (question_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    create_cover_letter_sessions_table = """
    CREATE TABLE IF NOT EXISTS cover_letter_sessions (
        session_id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        job_id VARCHAR(36) NOT NULL,
        cv_id VARCHAR(36),
        draft_text TEXT,
        selected_tone VARCHAR(20) NOT NULL DEFAULT 'professional',
        generated_letter TEXT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        INDEX idx_cover_sessions_user_job (user_id, job_id),
        INDEX idx_cover_sessions_active (is_active),
        INDEX idx_cover_sessions_expires (expires_at),
        INDEX idx_cover_sessions_user (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    create_questionnaire_submissions_table = """
    CREATE TABLE IF NOT EXISTS questionnaire_submissions (
        submission_id VARCHAR(36) PRIMARY KEY,
        application_id VARCHAR(36) NOT NULL,
        questionnaire_id VARCHAR(36) NOT NULL,
        user_id VARCHAR(36) NOT NULL,
        started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        submitted_at DATETIME,
        time_spent_seconds INT,
        is_complete BOOLEAN NOT NULL DEFAULT FALSE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (questionnaire_id) REFERENCES questionnaires(questionnaire_id) ON DELETE CASCADE,
        INDEX idx_submissions_application (application_id),
        INDEX idx_submissions_user (user_id),
        INDEX idx_submissions_questionnaire (questionnaire_id),
        INDEX idx_submissions_complete (is_complete),
        INDEX idx_submissions_started (started_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    create_questionnaire_answers_table = """
    CREATE TABLE IF NOT EXISTS questionnaire_answers (
        answer_id VARCHAR(36) PRIMARY KEY,
        submission_id VARCHAR(36) NOT NULL,
        question_id VARCHAR(36) NOT NULL,
        answer_data JSON NOT NULL,
        answered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (submission_id) REFERENCES questionnaire_submissions(submission_id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES questionnaire_questions(question_id) ON DELETE CASCADE,
        INDEX idx_answers_submission (submission_id),
        INDEX idx_answers_question (question_id),
        INDEX idx_answers_answered (answered_at),
        UNIQUE KEY unique_submission_question (submission_id, question_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    tables = [
        ("questionnaires", create_questionnaires_table),
        ("questionnaire_questions", create_questionnaire_questions_table),
        ("cover_letter_sessions", create_cover_letter_sessions_table),
        ("questionnaire_submissions", create_questionnaire_submissions_table),
        ("questionnaire_answers", create_questionnaire_answers_table)
    ]
    
    with get_session() as session:
        try:
            for table_name, create_sql in tables:
                logger.info(f"Creating table: {table_name}")
                session.execute(text(create_sql))
                logger.info(f"Successfully created table: {table_name}")
            
            session.commit()
            logger.info("All questionnaire tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating questionnaire tables: {e}")
            session.rollback()
            raise


def add_sample_questionnaires():
    """Add sample questionnaires for testing"""
    
    sample_questionnaires = [
        {
            'questionnaire_id': 'sample-tech-001',
            'title': 'Technical Skills Assessment',
            'description': 'Basic technical skills evaluation for software development roles',
            'time_limit': 45,
            'questions': [
                {
                    'question_id': 'tech-q1',
                    'question_text': 'How many years of experience do you have with Python?',
                    'question_type': 'multiple_choice',
                    'required': True,
                    'options': ['0-1 years', '2-3 years', '4-5 years', '6+ years'],
                    'order_index': 1
                },
                {
                    'question_id': 'tech-q2',
                    'question_text': 'Describe your experience with database design and optimization.',
                    'question_type': 'text',
                    'required': True,
                    'max_length': 1000,
                    'order_index': 2
                },
                {
                    'question_id': 'tech-q3',
                    'question_text': 'Rate your proficiency with Git version control.',
                    'question_type': 'rating',
                    'required': True,
                    'min_rating': 1,
                    'max_rating': 5,
                    'order_index': 3
                }
            ]
        },
        {
            'questionnaire_id': 'sample-general-001',
            'title': 'General Application Questions',
            'description': 'Standard questions for all job applications',
            'time_limit': 20,
            'questions': [
                {
                    'question_id': 'gen-q1',
                    'question_text': 'Why are you interested in this position?',
                    'question_type': 'text',
                    'required': True,
                    'max_length': 500,
                    'order_index': 1
                },
                {
                    'question_id': 'gen-q2',
                    'question_text': 'Are you available to start immediately?',
                    'question_type': 'boolean',
                    'required': True,
                    'order_index': 2
                }
            ]
        }
    ]
    
    insert_questionnaire_sql = """
    INSERT IGNORE INTO questionnaires 
    (questionnaire_id, title, description, time_limit, is_active, created_at, updated_at)
    VALUES (:questionnaire_id, :title, :description, :time_limit, TRUE, NOW(), NOW())
    """
    
    insert_question_sql = """
    INSERT IGNORE INTO questionnaire_questions 
    (question_id, questionnaire_id, question_text, question_type, required, options, 
     max_length, min_rating, max_rating, order_index, created_at)
    VALUES (:question_id, :questionnaire_id, :question_text, :question_type, :required, 
            :options, :max_length, :min_rating, :max_rating, :order_index, NOW())
    """
    
    with get_session() as session:
        try:
            for questionnaire in sample_questionnaires:
                # Insert questionnaire
                session.execute(text(insert_questionnaire_sql), {
                    'questionnaire_id': questionnaire['questionnaire_id'],
                    'title': questionnaire['title'],
                    'description': questionnaire['description'],
                    'time_limit': questionnaire['time_limit']
                })
                
                # Insert questions
                for question in questionnaire['questions']:
                    import json
                    options_json = json.dumps(question.get('options')) if question.get('options') else None
                    
                    session.execute(text(insert_question_sql), {
                        'question_id': question['question_id'],
                        'questionnaire_id': questionnaire['questionnaire_id'],
                        'question_text': question['question_text'],
                        'question_type': question['question_type'],
                        'required': question['required'],
                        'options': options_json,
                        'max_length': question.get('max_length'),
                        'min_rating': question.get('min_rating'),
                        'max_rating': question.get('max_rating'),
                        'order_index': question['order_index']
                    })
            
            session.commit()
            logger.info("Sample questionnaires added successfully")
            
        except Exception as e:
            logger.error(f"Error adding sample questionnaires: {e}")
            session.rollback()
            raise


def run_migration():
    """Run the complete migration"""
    try:
        logger.info("Starting questionnaire tables migration...")
        create_questionnaire_tables()
        add_sample_questionnaires()
        logger.info("Questionnaire tables migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ Questionnaire tables migration completed successfully")
    else:
        print("❌ Migration failed - check logs for details")
        exit(1)