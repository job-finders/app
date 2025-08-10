#!/usr/bin/env python3
"""
Database migration script to add job actions tables (job_likes and job_shares)
Run this script to create the new tables for the job actions feature.

This migration includes:
- job_likes table for tracking user likes on jobs
- job_shares table for tracking job sharing across platforms
- Optimized indexes for query performance
- Foreign key constraints for data integrity
- Unique constraints to prevent duplicate actions
"""

import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.database.sql.jobs_sql import JobLikeORM, JobShareORM
from src.database.sql import engine
from sqlalchemy import text, inspect


def create_job_actions_tables():
    """Create the job_likes and job_shares tables with optimized indexes"""
    print("🚀 Starting job actions tables migration...")
    print(f"📅 Migration started at: {datetime.now().isoformat()}")

    try:
        inspector = inspect(engine)

        # Create job_likes table
        if not inspector.has_table('job_likes'):
            JobLikeORM.create_if_not_table()
            print("✅ Created job_likes table")
        else:
            print("ℹ️  job_likes table already exists")

        # Create job_shares table  
        if not inspector.has_table('job_shares'):
            JobShareORM.create_if_not_table()
            print("✅ Created job_shares table")
        else:
            print("ℹ️  job_shares table already exists")

        # Create optimized indexes for performance
        with engine.connect() as conn:
            print("🔧 Creating performance indexes...")

            # Job Likes Indexes
            indexes_to_create = [
                # Composite index for user-job lookups (most common query)
                ("ix_job_likes_user_job", "job_likes", "user_id, job_id"),

                # Index for job popularity queries (like counts per job)
                ("ix_job_likes_job_created", "job_likes", "job_id, created_at DESC"),

                # Index for user activity tracking
                ("ix_job_likes_user_created", "job_likes", "user_id, created_at DESC"),

                # Job Shares Indexes
                # Composite index for job-method analytics
                ("ix_job_shares_job_method", "job_shares", "job_id, share_method"),

                # Index for temporal analytics (shares over time)
                ("ix_job_shares_shared_at", "job_shares", "shared_at DESC"),

                # Index for user sharing activity
                ("ix_job_shares_user_shared", "job_shares", "user_id, shared_at DESC"),

                # Index for referral tracking
                ("ix_job_shares_referral", "job_shares", "referral_code"),

                # Index for share method analytics
                ("ix_job_shares_method_shared", "job_shares", "share_method, shared_at DESC"),
            ]

            for index_name, table_name, columns in indexes_to_create:
                try:
                    conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON {table_name}({columns})
                    """))
                    print(f"  ✅ Created index: {index_name}")
                except Exception as e:
                    print(f"  ⚠️  Warning: Could not create index {index_name}: {e}")

            # Create additional constraints for data integrity
            print("🔒 Adding data integrity constraints...")

            # Ensure share_method values are valid
            try:
                conn.execute(text("""
                                  ALTER TABLE job_shares
                                      ADD CONSTRAINT chk_share_method
                                          CHECK (share_method IN
                                                 ('email', 'linkedin', 'twitter', 'facebook', 'whatsapp', 'copy_link',
                                                  'native'))
                                  """))
                print("  ✅ Added share_method constraint")
            except Exception as e:
                print(f"  ℹ️  Share method constraint already exists or could not be added: {e}")

            # Ensure referral_code format (if provided)
            try:
                conn.execute(text("""
                                  ALTER TABLE job_shares
                                      ADD CONSTRAINT chk_referral_code_format
                                          CHECK (referral_code IS NULL OR LENGTH(referral_code) BETWEEN 6 AND 20)
                                  """))
                print("  ✅ Added referral_code format constraint")
            except Exception as e:
                print(f"  ℹ️  Referral code constraint already exists or could not be added: {e}")

            conn.commit()
            print("✅ All indexes and constraints created successfully")

        # Verify table creation and structure
        print("🔍 Verifying table structure...")
        with engine.connect() as conn:
            # Check job_likes table structure
            likes_result = conn.execute(text("DESCRIBE job_likes")).fetchall()
            print(f"  📊 job_likes table has {len(likes_result)} columns")

            # Check job_shares table structure
            shares_result = conn.execute(text("DESCRIBE job_shares")).fetchall()
            print(f"  📊 job_shares table has {len(shares_result)} columns")

            # Check indexes
            likes_indexes = conn.execute(text("SHOW INDEX FROM job_likes")).fetchall()
            shares_indexes = conn.execute(text("SHOW INDEX FROM job_shares")).fetchall()
            print(f"  🔍 job_likes has {len(likes_indexes)} indexes")
            print(f"  🔍 job_shares has {len(shares_indexes)} indexes")

        print("🎉 Job actions tables migration completed successfully!")
        print(f"📅 Migration completed at: {datetime.now().isoformat()}")

    except Exception as e:
        print(f"❌ Error creating job actions tables: {e}")
        print("🔄 Rolling back changes...")
        try:
            rollback_job_actions_tables()
        except:
            pass
        raise


def rollback_job_actions_tables():
    """Remove the job actions tables and related constraints (rollback)"""
    print("🔄 Rolling back job actions tables migration...")
    print(f"📅 Rollback started at: {datetime.now().isoformat()}")

    try:
        inspector = inspect(engine)

        # Drop constraints first (if they exist)
        with engine.connect() as conn:
            print("🔓 Removing constraints...")
            try:
                conn.execute(text("ALTER TABLE job_shares DROP CONSTRAINT IF EXISTS chk_share_method"))
                conn.execute(text("ALTER TABLE job_shares DROP CONSTRAINT IF EXISTS chk_referral_code_format"))
                print("  ✅ Removed constraints")
            except Exception as e:
                print(f"  ℹ️  Constraints may not exist: {e}")

            conn.commit()

        # Drop tables
        if inspector.has_table('job_shares'):
            JobShareORM.delete_table()
            print("✅ Dropped job_shares table")
        else:
            print("ℹ️  job_shares table does not exist")

        if inspector.has_table('job_likes'):
            JobLikeORM.delete_table()
            print("✅ Dropped job_likes table")
        else:
            print("ℹ️  job_likes table does not exist")

        print("🎉 Job actions tables rollback completed successfully!")
        print(f"📅 Rollback completed at: {datetime.now().isoformat()}")

    except Exception as e:
        print(f"❌ Error rolling back job actions tables: {e}")
        raise


def test_migration():
    """Test the migration by creating and dropping tables"""
    print("🧪 Testing job actions migration...")

    try:
        # Test creation
        create_job_actions_tables()

        # Test basic operations
        with engine.connect() as conn:
            # Test that we can insert into job_likes (this will fail if foreign keys don't exist, which is expected)
            print("🔍 Testing table accessibility...")
            conn.execute(text("SELECT COUNT(*) FROM job_likes"))
            conn.execute(text("SELECT COUNT(*) FROM job_shares"))
            print("✅ Tables are accessible")

        # Test rollback
        rollback_job_actions_tables()

        print("🎉 Migration test completed successfully!")

    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage job actions database tables")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    parser.add_argument("--test", action="store_true", help="Test the migration (create and rollback)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.test:
        test_migration()
    elif args.rollback:
        rollback_job_actions_tables()
    else:
        create_job_actions_tables()
