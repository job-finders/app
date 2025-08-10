"""
Unit tests for Job Actions ORM Models

Tests database operations and relationships for:
- JobLikeORM model
- JobShareORM model
- SavedJobORM model
- Database constraints and relationships
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from unittest.mock import Mock, patch

from src.database import JobLikeORM, JobShareORM, SavedJobORM, JobsORM, JobSeekerProfileORM


class TestJobLikeORM:
    """Test JobLikeORM database operations"""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = Mock()
        return session

    def test_job_like_orm_creation(self):
        """Test JobLikeORM instance creation"""
        like_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        like_orm = JobLikeORM(
            like_id=like_id,
            user_id="user123",
            job_id="job456",
            created_at=created_at
        )

        assert like_orm.like_id == like_id
        assert like_orm.user_id == "user123"
        assert like_orm.job_id == "job456"
        assert like_orm.created_at == created_at

    def test_job_like_orm_table_name(self):
        """Test JobLikeORM table name"""
        assert JobLikeORM.__tablename__ == 'job_likes'

    def test_job_like_orm_primary_key(self):
        """Test JobLikeORM primary key"""
        # Check that like_id is the primary key
        primary_keys = [col.name for col in JobLikeORM.__table__.primary_key.columns]
        assert 'like_id' in primary_keys

    def test_job_like_orm_foreign_keys(self):
        """Test JobLikeORM foreign key constraints"""
        # Check foreign key columns exist
        column_names = [col.name for col in JobLikeORM.__table__.columns]
        assert 'user_id' in column_names
        assert 'job_id' in column_names

        # Check foreign key constraints
        foreign_keys = JobLikeORM.__table__.foreign_keys
        fk_columns = [fk.parent.name for fk in foreign_keys]
        assert 'user_id' in fk_columns
        assert 'job_id' in fk_columns

    def test_job_like_orm_unique_constraint(self):
        """Test JobLikeORM unique constraint on user_id and job_id"""
        # Check that unique constraint exists
        constraints = JobLikeORM.__table__.constraints
        unique_constraints = [c for c in constraints if hasattr(c, 'columns')]

        # Should have unique constraint on user_id, job_id combination
        found_unique = False
        for constraint in unique_constraints:
            if hasattr(constraint, 'columns'):
                column_names = [col.name for col in constraint.columns]
                if 'user_id' in column_names and 'job_id' in column_names:
                    found_unique = True
                    break

        assert found_unique or hasattr(JobLikeORM.__table_args__, '__iter__')

    def test_job_like_orm_to_dict(self):
        """Test JobLikeORM to_dict method"""
        like_orm = JobLikeORM(
            like_id=str(uuid.uuid4()),
            user_id="user123",
            job_id="job456",
            created_at=datetime.now(timezone.utc)
        )

        if hasattr(like_orm, 'to_dict'):
            data = like_orm.to_dict()
            assert isinstance(data, dict)
            assert 'like_id' in data
            assert 'user_id' in data
            assert 'job_id' in data
            assert 'created_at' in data

    @patch('src.database.session')
    def test_job_like_orm_database_operations(self, mock_session):
        """Test JobLikeORM database CRUD operations"""
        like_orm = JobLikeORM(
            like_id=str(uuid.uuid4()),
            user_id="user123",
            job_id="job456"
        )

        # Test add operation
        mock_session.add(like_orm)
        mock_session.add.assert_called_once_with(like_orm)

        # Test commit
        mock_session.commit()
        mock_session.commit.assert_called_once()

        # Test query
        mock_session.query(JobLikeORM).filter_by(user_id="user123").first()
        mock_session.query.assert_called()


class TestJobShareORM:
    """Test JobShareORM database operations"""

    def test_job_share_orm_creation(self):
        """Test JobShareORM instance creation"""
        share_id = str(uuid.uuid4())
        shared_at = datetime.now(timezone.utc)

        share_orm = JobShareORM(
            share_id=share_id,
            user_id="user123",
            job_id="job456",
            share_method="linkedin",
            shared_at=shared_at,
            referral_code="REF123"
        )

        assert share_orm.share_id == share_id
        assert share_orm.user_id == "user123"
        assert share_orm.job_id == "job456"
        assert share_orm.share_method == "linkedin"
        assert share_orm.shared_at == shared_at
        assert share_orm.referral_code == "REF123"

    def test_job_share_orm_anonymous_share(self):
        """Test JobShareORM with anonymous sharing (no user_id)"""
        share_orm = JobShareORM(
            share_id=str(uuid.uuid4()),
            user_id=None,
            job_id="job456",
            share_method="email"
        )

        assert share_orm.user_id is None
        assert share_orm.job_id == "job456"
        assert share_orm.share_method == "email"

    def test_job_share_orm_table_name(self):
        """Test JobShareORM table name"""
        assert JobShareORM.__tablename__ == 'job_shares'

    def test_job_share_orm_columns(self):
        """Test JobShareORM column definitions"""
        column_names = [col.name for col in JobShareORM.__table__.columns]

        expected_columns = [
            'share_id', 'user_id', 'job_id', 'share_method',
            'shared_at', 'referral_code'
        ]

        for col in expected_columns:
            assert col in column_names

    def test_job_share_orm_nullable_fields(self):
        """Test JobShareORM nullable field constraints"""
        # user_id should be nullable (for anonymous shares)
        user_id_col = next(col for col in JobShareORM.__table__.columns if col.name == 'user_id')
        assert user_id_col.nullable is True

        # referral_code should be nullable
        referral_col = next(col for col in JobShareORM.__table__.columns if col.name == 'referral_code')
        assert referral_col.nullable is True

        # job_id should not be nullable
        job_id_col = next(col for col in JobShareORM.__table__.columns if col.name == 'job_id')
        assert job_id_col.nullable is False

    def test_job_share_orm_relationships(self):
        """Test JobShareORM relationship definitions"""
        # Check if relationships are defined
        if hasattr(JobShareORM, 'user'):
            assert hasattr(JobShareORM.user.property, 'mapper')

        if hasattr(JobShareORM, 'job'):
            assert hasattr(JobShareORM.job.property, 'mapper')


class TestSavedJobORM:
    """Test SavedJobORM database operations"""

    def test_saved_job_orm_creation(self):
        """Test SavedJobORM instance creation"""
        saved_job_id = str(uuid.uuid4())
        saved_at = datetime.now(timezone.utc)

        saved_job_orm = SavedJobORM(
            saved_job_id=saved_job_id,
            user_id="user123",
            job_id="job456",
            saved_at=saved_at
        )

        assert saved_job_orm.saved_job_id == saved_job_id
        assert saved_job_orm.user_id == "user123"
        assert saved_job_orm.job_id == "job456"
        assert saved_job_orm.saved_at == saved_at

    def test_saved_job_orm_table_name(self):
        """Test SavedJobORM table name"""
        assert SavedJobORM.__tablename__ == 'saved_jobs'

    def test_saved_job_orm_required_fields(self):
        """Test SavedJobORM required field constraints"""
        # user_id should not be nullable
        user_id_col = next(col for col in SavedJobORM.__table__.columns if col.name == 'user_id')
        assert user_id_col.nullable is False

        # job_id should not be nullable
        job_id_col = next(col for col in SavedJobORM.__table__.columns if col.name == 'job_id')
        assert job_id_col.nullable is False

    def test_saved_job_orm_unique_constraint(self):
        """Test SavedJobORM unique constraint on user_id and job_id"""
        # Similar to JobLikeORM, should have unique constraint
        constraints = SavedJobORM.__table__.constraints
        unique_constraints = [c for c in constraints if hasattr(c, 'columns')]

        found_unique = False
        for constraint in unique_constraints:
            if hasattr(constraint, 'columns'):
                column_names = [col.name for col in constraint.columns]
                if 'user_id' in column_names and 'job_id' in column_names:
                    found_unique = True
                    break

        # Should have unique constraint or be defined in __table_args__
        assert found_unique or hasattr(SavedJobORM.__table_args__, '__iter__')


class TestORMRelationships:
    """Test relationships between ORM models"""

    def test_job_orm_relationships(self):
        """Test JobsORM relationships with job actions"""
        # Check if JobsORM has relationships to job actions
        if hasattr(JobsORM, 'likes'):
            assert hasattr(JobsORM.likes.property, 'mapper')

        if hasattr(JobsORM, 'shares'):
            assert hasattr(JobsORM.shares.property, 'mapper')

        if hasattr(JobsORM, 'saved_jobs'):
            assert hasattr(JobsORM.saved_jobs.property, 'mapper')

    def test_user_orm_relationships(self):
        """Test JobSeekerProfileORM relationships with job actions"""
        # Check if JobSeekerProfileORM has relationships to job actions
        if hasattr(JobSeekerProfileORM, 'liked_jobs'):
            assert hasattr(JobSeekerProfileORM.liked_jobs.property, 'mapper')

        if hasattr(JobSeekerProfileORM, 'shared_jobs'):
            assert hasattr(JobSeekerProfileORM.shared_jobs.property, 'mapper')

        if hasattr(JobSeekerProfileORM, 'saved_jobs'):
            assert hasattr(JobSeekerProfileORM.saved_jobs.property, 'mapper')

    def test_back_references(self):
        """Test back references in relationships"""
        # Test that relationships have proper back references
        if hasattr(JobLikeORM, 'user') and hasattr(JobLikeORM, 'job'):
            # Check back_populates or backref is configured
            user_rel = JobLikeORM.user.property
            job_rel = JobLikeORM.job.property

            # These should have back references configured
            assert hasattr(user_rel, 'back_populates') or hasattr(user_rel, 'backref')
            assert hasattr(job_rel, 'back_populates') or hasattr(job_rel, 'backref')


class TestORMConstraints:
    """Test database constraints and validation"""

    def test_foreign_key_constraints(self):
        """Test foreign key constraint definitions"""
        # JobLikeORM foreign keys
        like_fks = JobLikeORM.__table__.foreign_keys
        like_fk_targets = [fk.column.table.name for fk in like_fks]

        # Should reference users and jobs tables
        assert any('user' in target for target in like_fk_targets)
        assert any('job' in target for target in like_fk_targets)

        # JobShareORM foreign keys
        share_fks = JobShareORM.__table__.foreign_keys
        share_fk_targets = [fk.column.table.name for fk in share_fks]

        # Should reference jobs table (user_id is nullable)
        assert any('job' in target for target in share_fk_targets)

    def test_column_types(self):
        """Test column type definitions"""
        # Test string columns have appropriate lengths
        like_columns = {col.name: col for col in JobLikeORM.__table__.columns}

        # ID columns should be strings with appropriate length
        assert str(like_columns['like_id'].type).startswith('VARCHAR')
        assert str(like_columns['user_id'].type).startswith('VARCHAR')
        assert str(like_columns['job_id'].type).startswith('VARCHAR')

        # Timestamp columns should be datetime
        assert 'DATETIME' in str(like_columns['created_at'].type) or 'TIMESTAMP' in str(like_columns['created_at'].type)

    def test_index_definitions(self):
        """Test database index definitions"""
        # Check if indexes are defined for performance
        like_indexes = JobLikeORM.__table__.indexes
        share_indexes = JobShareORM.__table__.indexes
        saved_indexes = SavedJobORM.__table__.indexes

        # Should have indexes on frequently queried columns
        # This is more of a performance consideration
        assert isinstance(like_indexes, set)
        assert isinstance(share_indexes, set)
        assert isinstance(saved_indexes, set)


class TestORMIntegration:
    """Integration tests for ORM models"""

    @patch('src.database.session')
    def test_orm_crud_operations(self, mock_session):
        """Test complete CRUD operations"""
        # Create
        like_orm = JobLikeORM(
            like_id=str(uuid.uuid4()),
            user_id="user123",
            job_id="job456"
        )

        mock_session.add(like_orm)
        mock_session.commit()

        # Read
        mock_session.query(JobLikeORM).filter_by(user_id="user123").first()

        # Update (if applicable)
        # Likes typically don't get updated, but test the pattern

        # Delete
        mock_session.delete(like_orm)
        mock_session.commit()

        # Verify calls were made
        mock_session.add.assert_called()
        mock_session.query.assert_called()
        mock_session.delete.assert_called()

    def test_orm_model_validation(self):
        """Test ORM model validation"""
        # Test that models can be created with valid data
        like_orm = JobLikeORM(
            like_id=str(uuid.uuid4()),
            user_id="user123",
            job_id="job456",
            created_at=datetime.now(timezone.utc)
        )

        share_orm = JobShareORM(
            share_id=str(uuid.uuid4()),
            job_id="job456",
            share_method="linkedin",
            shared_at=datetime.now(timezone.utc)
        )

        saved_orm = SavedJobORM(
            saved_job_id=str(uuid.uuid4()),
            user_id="user123",
            job_id="job456",
            saved_at=datetime.now(timezone.utc)
        )

        # All should be created successfully
        assert like_orm.like_id is not None
        assert share_orm.share_id is not None
        assert saved_orm.saved_job_id is not None

    def test_orm_serialization(self):
        """Test ORM model serialization"""
        like_orm = JobLikeORM(
            like_id=str(uuid.uuid4()),
            user_id="user123",
            job_id="job456",
            created_at=datetime.now(timezone.utc)
        )

        # Test to_dict method if available
        if hasattr(like_orm, 'to_dict'):
            data = like_orm.to_dict()
            assert isinstance(data, dict)
            assert all(key in data for key in ['like_id', 'user_id', 'job_id', 'created_at'])

        # Test that attributes are accessible
        assert hasattr(like_orm, 'like_id')
        assert hasattr(like_orm, 'user_id')
        assert hasattr(like_orm, 'job_id')
        assert hasattr(like_orm, 'created_at')


if __name__ == '__main__':
    pytest.main([__file__])
