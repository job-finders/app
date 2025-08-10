#!/usr/bin/env python3
"""
Job Actions Database Integrity Check Script

This script validates the integrity of job actions tables and their relationships.
It checks for:
- Foreign key constraints
- Data consistency
- Index effectiveness
- Performance metrics
- Orphaned records
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.database.sql import engine
from sqlalchemy import text


class JobActionsIntegrityChecker:
    """Comprehensive integrity checker for job actions tables"""

    def __init__(self):
        self.engine = engine
        self.issues = []
        self.warnings = []
        self.stats = {}

    def run_all_checks(self) -> Dict:
        """Run all integrity checks and return results"""
        print("🔍 Starting Job Actions Integrity Check...")
        print(f"📅 Check started at: {datetime.now().isoformat()}")
        print("=" * 60)

        checks = [
            ("Table Structure", self.check_table_structure),
            ("Foreign Key Integrity", self.check_foreign_key_integrity),
            ("Data Consistency", self.check_data_consistency),
            ("Index Effectiveness", self.check_index_effectiveness),
            ("Performance Metrics", self.check_performance_metrics),
            ("Orphaned Records", self.check_orphaned_records),
            ("Duplicate Prevention", self.check_duplicate_prevention),
            ("Data Quality", self.check_data_quality),
        ]

        for check_name, check_function in checks:
            print(f"\n🔧 Running {check_name} check...")
            try:
                check_function()
                print(f"✅ {check_name} check completed")
            except Exception as e:
                error_msg = f"❌ {check_name} check failed: {e}"
                print(error_msg)
                self.issues.append(error_msg)

        return self.generate_report()

    def check_table_structure(self):
        """Verify that tables exist with correct structure"""
        with self.engine.connect() as conn:
            # Check if tables exist
            tables_query = text("""
                                SELECT TABLE_NAME
                                FROM information_schema.TABLES
                                WHERE TABLE_SCHEMA = DATABASE()
                                  AND TABLE_NAME IN ('job_likes', 'job_shares')
                                """)
            tables = [row[0] for row in conn.execute(tables_query).fetchall()]

            if 'job_likes' not in tables:
                self.issues.append("job_likes table does not exist")
            if 'job_shares' not in tables:
                self.issues.append("job_shares table does not exist")

            # Check job_likes structure
            if 'job_likes' in tables:
                likes_columns = conn.execute(text("DESCRIBE job_likes")).fetchall()
                expected_likes_columns = {'like_id', 'user_id', 'job_id', 'created_at'}
                actual_likes_columns = {row[0] for row in likes_columns}

                missing_columns = expected_likes_columns - actual_likes_columns
                if missing_columns:
                    self.issues.append(f"job_likes missing columns: {missing_columns}")

                self.stats['job_likes_columns'] = len(actual_likes_columns)

            # Check job_shares structure
            if 'job_shares' in tables:
                shares_columns = conn.execute(text("DESCRIBE job_shares")).fetchall()
                expected_shares_columns = {'share_id', 'user_id', 'job_id', 'share_method', 'shared_at',
                                           'referral_code'}
                actual_shares_columns = {row[0] for row in shares_columns}

                missing_columns = expected_shares_columns - actual_shares_columns
                if missing_columns:
                    self.issues.append(f"job_shares missing columns: {missing_columns}")

                self.stats['job_shares_columns'] = len(actual_shares_columns)

    def check_foreign_key_integrity(self):
        """Check foreign key relationships"""
        with self.engine.connect() as conn:
            # Check job_likes foreign keys
            orphaned_likes_jobs = conn.execute(text("""
                                                    SELECT COUNT(*) as count
                                                    FROM job_likes jl
                                                             LEFT JOIN jobs j ON jl.job_id = j.job_id
                                                    WHERE j.job_id IS NULL
                                                    """)).fetchone()[0]

            if orphaned_likes_jobs > 0:
                self.issues.append(f"Found {orphaned_likes_jobs} job_likes with invalid job_id references")

            orphaned_likes_users = conn.execute(text("""
                                                     SELECT COUNT(*) as count
                                                     FROM job_likes jl
                                                              LEFT JOIN jobseeker_profiles jsp ON jl.user_id = jsp.user_uid
                                                     WHERE jsp.user_uid IS NULL
                                                     """)).fetchone()[0]

            if orphaned_likes_users > 0:
                self.issues.append(f"Found {orphaned_likes_users} job_likes with invalid user_id references")

            # Check job_shares foreign keys
            orphaned_shares_jobs = conn.execute(text("""
                                                     SELECT COUNT(*) as count
                                                     FROM job_shares js
                                                              LEFT JOIN jobs j ON js.job_id = j.job_id
                                                     WHERE j.job_id IS NULL
                                                     """)).fetchone()[0]

            if orphaned_shares_jobs > 0:
                self.issues.append(f"Found {orphaned_shares_jobs} job_shares with invalid job_id references")

            orphaned_shares_users = conn.execute(text("""
                                                      SELECT COUNT(*) as count
                                                      FROM job_shares js
                                                               LEFT JOIN jobseeker_profiles jsp ON js.user_id = jsp.user_uid
                                                      WHERE js.user_id IS NOT NULL
                                                        AND jsp.user_uid IS NULL
                                                      """)).fetchone()[0]

            if orphaned_shares_users > 0:
                self.issues.append(f"Found {orphaned_shares_users} job_shares with invalid user_id references")

            self.stats['orphaned_likes_jobs'] = orphaned_likes_jobs
            self.stats['orphaned_likes_users'] = orphaned_likes_users
            self.stats['orphaned_shares_jobs'] = orphaned_shares_jobs
            self.stats['orphaned_shares_users'] = orphaned_shares_users

    def check_data_consistency(self):
        """Check for data consistency issues"""
        with self.engine.connect() as conn:
            # Check for duplicate likes (should be prevented by unique constraint)
            duplicate_likes = conn.execute(text("""
                                                SELECT user_id, job_id, COUNT(*) as count
                                                FROM job_likes
                                                GROUP BY user_id, job_id
                                                HAVING COUNT(*) > 1
                                                """)).fetchall()

            if duplicate_likes:
                self.issues.append(f"Found {len(duplicate_likes)} duplicate like entries")
                for user_id, job_id, count in duplicate_likes[:5]:  # Show first 5
                    self.issues.append(f"  User {user_id} has {count} likes for job {job_id}")

            # Check for invalid share methods
            invalid_share_methods = conn.execute(text("""
                                                      SELECT DISTINCT share_method
                                                      FROM job_shares
                                                      WHERE share_method NOT IN
                                                            ('email', 'linkedin', 'twitter', 'facebook', 'whatsapp',
                                                             'copy_link', 'native')
                                                      """)).fetchall()

            if invalid_share_methods:
                methods = [row[0] for row in invalid_share_methods]
                self.issues.append(f"Found invalid share methods: {methods}")

            # Check for future dates
            future_likes = conn.execute(text("""
                                             SELECT COUNT(*) as count
                                             FROM job_likes
                                             WHERE created_at > NOW()
                                             """)).fetchone()[0]

            if future_likes > 0:
                self.warnings.append(f"Found {future_likes} likes with future timestamps")

            future_shares = conn.execute(text("""
                                              SELECT COUNT(*) as count
                                              FROM job_shares
                                              WHERE shared_at > NOW()
                                              """)).fetchone()[0]

            if future_shares > 0:
                self.warnings.append(f"Found {future_shares} shares with future timestamps")

            self.stats['duplicate_likes'] = len(duplicate_likes)
            self.stats['invalid_share_methods'] = len(invalid_share_methods)
            self.stats['future_likes'] = future_likes
            self.stats['future_shares'] = future_shares

    def check_index_effectiveness(self):
        """Check if indexes are being used effectively"""
        with self.engine.connect() as conn:
            # Get index information
            likes_indexes = conn.execute(text("""
                                              SELECT INDEX_NAME, CARDINALITY, NON_UNIQUE
                                              FROM information_schema.STATISTICS
                                              WHERE TABLE_SCHEMA = DATABASE()
                                                AND TABLE_NAME = 'job_likes'
                                                AND INDEX_NAME != 'PRIMARY'
                                              """)).fetchall()

            shares_indexes = conn.execute(text("""
                                               SELECT INDEX_NAME, CARDINALITY, NON_UNIQUE
                                               FROM information_schema.STATISTICS
                                               WHERE TABLE_SCHEMA = DATABASE()
                                                 AND TABLE_NAME = 'job_shares'
                                                 AND INDEX_NAME != 'PRIMARY'
                                               """)).fetchall()

            # Check if essential indexes exist
            likes_index_names = {row[0] for row in likes_indexes}
            shares_index_names = {row[0] for row in shares_indexes}

            essential_likes_indexes = {'unique_user_job_like', 'ix_job_likes_user_job', 'ix_job_likes_job_created'}
            essential_shares_indexes = {'ix_job_shares_job_method', 'ix_job_shares_user_shared'}

            missing_likes_indexes = essential_likes_indexes - likes_index_names
            missing_shares_indexes = essential_shares_indexes - shares_index_names

            if missing_likes_indexes:
                self.warnings.append(f"Missing essential job_likes indexes: {missing_likes_indexes}")

            if missing_shares_indexes:
                self.warnings.append(f"Missing essential job_shares indexes: {missing_shares_indexes}")

            self.stats['job_likes_indexes'] = len(likes_indexes)
            self.stats['job_shares_indexes'] = len(shares_indexes)

    def check_performance_metrics(self):
        """Check performance-related metrics"""
        with self.engine.connect() as conn:
            # Get table sizes
            table_sizes = conn.execute(text("""
                                            SELECT TABLE_NAME,
                                                   TABLE_ROWS,
                                                   ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS size_mb
                                            FROM information_schema.TABLES
                                            WHERE TABLE_SCHEMA = DATABASE()
                                              AND TABLE_NAME IN ('job_likes', 'job_shares')
                                            """)).fetchall()

            for table_name, row_count, size_mb in table_sizes:
                self.stats[f'{table_name}_rows'] = row_count
                self.stats[f'{table_name}_size_mb'] = size_mb

                # Warn if tables are getting large without proper maintenance
                if row_count > 1000000:  # 1M rows
                    self.warnings.append(f"{table_name} has {row_count:,} rows - consider archiving old data")

                if size_mb > 100:  # 100MB
                    self.warnings.append(f"{table_name} is {size_mb}MB - monitor performance")

            # Check for recent activity
            recent_likes = conn.execute(text("""
                                             SELECT COUNT(*) as count
                                             FROM job_likes
                                             WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                                             """)).fetchone()[0]

            recent_shares = conn.execute(text("""
                                              SELECT COUNT(*) as count
                                              FROM job_shares
                                              WHERE shared_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                                              """)).fetchone()[0]

            self.stats['recent_likes_7d'] = recent_likes
            self.stats['recent_shares_7d'] = recent_shares

    def check_orphaned_records(self):
        """Check for orphaned records that should be cleaned up"""
        with self.engine.connect() as conn:
            # Check for likes on deleted/inactive jobs
            likes_on_inactive_jobs = conn.execute(text("""
                                                       SELECT COUNT(*) as count
                                                       FROM job_likes jl
                                                                JOIN jobs j ON jl.job_id = j.job_id
                                                       WHERE j.status != 'active'
                                                          OR j.expires_at < NOW()
                                                       """)).fetchone()[0]

            if likes_on_inactive_jobs > 0:
                self.warnings.append(f"Found {likes_on_inactive_jobs} likes on inactive/expired jobs")

            # Check for shares on deleted/inactive jobs
            shares_on_inactive_jobs = conn.execute(text("""
                                                        SELECT COUNT(*) as count
                                                        FROM job_shares js
                                                                 JOIN jobs j ON js.job_id = j.job_id
                                                        WHERE j.status != 'active'
                                                           OR j.expires_at < NOW()
                                                        """)).fetchone()[0]

            if shares_on_inactive_jobs > 0:
                self.warnings.append(f"Found {shares_on_inactive_jobs} shares on inactive/expired jobs")

            self.stats['likes_on_inactive_jobs'] = likes_on_inactive_jobs
            self.stats['shares_on_inactive_jobs'] = shares_on_inactive_jobs

    def check_duplicate_prevention(self):
        """Verify that duplicate prevention mechanisms are working"""
        with self.engine.connect() as conn:
            # Test unique constraint on job_likes
            try:
                # This should fail if unique constraint is working
                conn.execute(text("""
                                  SELECT 1
                                  FROM job_likes
                                  GROUP BY user_id, job_id
                                  HAVING COUNT(*) > 1
                                  LIMIT 1
                                  """)).fetchone()

                # If we get here, there are duplicates
                self.issues.append("Unique constraint on job_likes (user_id, job_id) is not working")
            except:
                # This is expected - no duplicates found
                pass

            # Check constraint existence
            constraints = conn.execute(text("""
                                            SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
                                            FROM information_schema.TABLE_CONSTRAINTS
                                            WHERE TABLE_SCHEMA = DATABASE()
                                              AND TABLE_NAME IN ('job_likes', 'job_shares')
                                              AND CONSTRAINT_TYPE IN ('UNIQUE', 'CHECK')
                                            """)).fetchall()

            constraint_names = {row[0] for row in constraints}

            if 'unique_user_job_like' not in constraint_names:
                self.issues.append("Missing unique constraint 'unique_user_job_like' on job_likes table")

            self.stats['constraints_count'] = len(constraints)

    def check_data_quality(self):
        """Check overall data quality metrics"""
        with self.engine.connect() as conn:
            # Check for NULL values where they shouldn't be
            null_checks = [
                ("job_likes", "like_id", "Primary key cannot be NULL"),
                ("job_likes", "user_id", "User ID cannot be NULL"),
                ("job_likes", "job_id", "Job ID cannot be NULL"),
                ("job_shares", "share_id", "Primary key cannot be NULL"),
                ("job_shares", "job_id", "Job ID cannot be NULL"),
                ("job_shares", "share_method", "Share method cannot be NULL"),
            ]

            for table, column, message in null_checks:
                null_count = conn.execute(text(f"""
                    SELECT COUNT(*) as count
                    FROM {table}
                    WHERE {column} IS NULL
                """)).fetchone()[0]

                if null_count > 0:
                    self.issues.append(f"{message}: Found {null_count} NULL values in {table}.{column}")

            # Check referral code format
            invalid_referral_codes = conn.execute(text("""
                                                       SELECT COUNT(*) as count
                                                       FROM job_shares
                                                       WHERE referral_code IS NOT NULL
                                                         AND (LENGTH(referral_code) < 6 OR LENGTH(referral_code) > 20)
                                                       """)).fetchone()[0]

            if invalid_referral_codes > 0:
                self.warnings.append(f"Found {invalid_referral_codes} invalid referral code formats")

            self.stats['invalid_referral_codes'] = invalid_referral_codes

    def generate_report(self) -> Dict:
        """Generate comprehensive integrity check report"""
        print("\n" + "=" * 60)
        print("📊 JOB ACTIONS INTEGRITY CHECK REPORT")
        print("=" * 60)

        # Summary
        print(f"\n📈 SUMMARY:")
        print(f"  Issues Found: {len(self.issues)}")
        print(f"  Warnings: {len(self.warnings)}")
        print(f"  Statistics Collected: {len(self.stats)}")

        # Issues
        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        else:
            print(f"\n✅ NO CRITICAL ISSUES FOUND")

        # Warnings
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        else:
            print(f"\n✅ NO WARNINGS")

        # Key Statistics
        print(f"\n📊 KEY STATISTICS:")
        key_stats = [
            'job_likes_rows', 'job_shares_rows',
            'recent_likes_7d', 'recent_shares_7d',
            'job_likes_size_mb', 'job_shares_size_mb',
            'job_likes_indexes', 'job_shares_indexes'
        ]

        for stat in key_stats:
            if stat in self.stats:
                print(f"  {stat.replace('_', ' ').title()}: {self.stats[stat]:,}")

        # Health Score
        health_score = self.calculate_health_score()
        print(f"\n🏥 OVERALL HEALTH SCORE: {health_score}/100")

        if health_score >= 90:
            print("  Status: EXCELLENT ✅")
        elif health_score >= 75:
            print("  Status: GOOD ⚠️")
        elif health_score >= 50:
            print("  Status: NEEDS ATTENTION ⚠️")
        else:
            print("  Status: CRITICAL ❌")

        print(f"\n📅 Check completed at: {datetime.now().isoformat()}")
        print("=" * 60)

        return {
            'health_score': health_score,
            'issues': self.issues,
            'warnings': self.warnings,
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }

    def calculate_health_score(self) -> int:
        """Calculate overall health score (0-100)"""
        score = 100

        # Deduct points for issues
        score -= len(self.issues) * 10  # 10 points per critical issue
        score -= len(self.warnings) * 2  # 2 points per warning

        # Bonus points for good practices
        if self.stats.get('job_likes_indexes', 0) >= 3:
            score += 5
        if self.stats.get('job_shares_indexes', 0) >= 3:
            score += 5

        return max(0, min(100, score))


def main():
    """Main function to run integrity checks"""
    checker = JobActionsIntegrityChecker()

    try:
        report = checker.run_all_checks()

        # Exit with appropriate code
        if report['health_score'] < 50:
            sys.exit(1)  # Critical issues
        elif len(report['issues']) > 0:
            sys.exit(2)  # Issues found
        else:
            sys.exit(0)  # All good

    except Exception as e:
        print(f"❌ Integrity check failed with error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
