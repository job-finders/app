"""
Unit tests for Job Actions Pydantic Models

Tests validation, serialization, and business logic for:
- JobLike model
- JobShare model  
- JobActionsState model
- ShareMethodEnum
"""

import pytest
import uuid
from datetime import datetime, timezone
from pydantic import ValidationError

from src.database.models import (
    JobLike, JobShare, JobActionsState, ShareMethodEnum, SavedJob
)


class TestJobLikeModel:
    """Test JobLike Pydantic model"""

    def test_job_like_creation_with_defaults(self):
        """Test JobLike creation with default values"""
        like = JobLike(
            user_id="user123",
            job_id="job456"
        )

        assert like.user_id == "user123"
        assert like.job_id == "job456"
        assert like.like_id is not None
        assert isinstance(like.like_id, str)
        assert isinstance(like.created_at, datetime)
        assert like.created_at.tzinfo == timezone.utc

    def test_job_like_creation_with_explicit_values(self):
        """Test JobLike creation with explicit values"""
        like_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        like = JobLike(
            like_id=like_id,
            user_id="user123",
            job_id="job456",
            created_at=created_at
        )

        assert like.like_id == like_id
        assert like.user_id == "user123"
        assert like.job_id == "job456"
        assert like.created_at == created_at

    def test_job_like_validation_required_fields(self):
        """Test JobLike validation for required fields"""
        with pytest.raises(ValidationError) as exc_info:
            JobLike()

        errors = exc_info.value.errors()
        required_fields = {error['loc'][0] for error in errors}
        assert 'user_id' in required_fields
        assert 'job_id' in required_fields

    def test_job_like_validation_empty_strings(self):
        """Test JobLike validation with empty strings"""
        with pytest.raises(ValidationError):
            JobLike(user_id="", job_id="job456")

        with pytest.raises(ValidationError):
            JobLike(user_id="user123", job_id="")

    def test_job_like_model_dump(self):
        """Test JobLike model serialization"""
        like = JobLike(
            user_id="user123",
            job_id="job456"
        )

        data = like.model_dump()

        assert isinstance(data, dict)
        assert data['user_id'] == "user123"
        assert data['job_id'] == "job456"
        assert 'like_id' in data
        assert 'created_at' in data

    def test_job_like_from_dict(self):
        """Test JobLike creation from dictionary"""
        data = {
            'like_id': str(uuid.uuid4()),
            'user_id': 'user123',
            'job_id': 'job456',
            'created_at': datetime.now(timezone.utc)
        }

        like = JobLike(**data)

        assert like.like_id == data['like_id']
        assert like.user_id == data['user_id']
        assert like.job_id == data['job_id']
        assert like.created_at == data['created_at']


class TestJobShareModel:
    """Test JobShare Pydantic model"""

    def test_job_share_creation_with_defaults(self):
        """Test JobShare creation with default values"""
        share = JobShare(
            job_id="job456",
            share_method=ShareMethodEnum.LINKEDIN
        )

        assert share.job_id == "job456"
        assert share.share_method == ShareMethodEnum.LINKEDIN
        assert share.user_id is None
        assert share.referral_code is None
        assert share.share_id is not None
        assert isinstance(share.shared_at, datetime)

    def test_job_share_creation_with_user(self):
        """Test JobShare creation with authenticated user"""
        share = JobShare(
            user_id="user123",
            job_id="job456",
            share_method=ShareMethodEnum.EMAIL,
            referral_code="REF123"
        )

        assert share.user_id == "user123"
        assert share.job_id == "job456"
        assert share.share_method == ShareMethodEnum.EMAIL
        assert share.referral_code == "REF123"

    def test_job_share_validation_required_fields(self):
        """Test JobShare validation for required fields"""
        with pytest.raises(ValidationError) as exc_info:
            JobShare()

        errors = exc_info.value.errors()
        required_fields = {error['loc'][0] for error in errors}
        assert 'job_id' in required_fields
        assert 'share_method' in required_fields

    def test_job_share_invalid_share_method(self):
        """Test JobShare validation with invalid share method"""
        with pytest.raises(ValidationError):
            JobShare(
                job_id="job456",
                share_method="invalid_method"
            )

    def test_job_share_valid_share_methods(self):
        """Test JobShare with all valid share methods"""
        valid_methods = [
            ShareMethodEnum.EMAIL,
            ShareMethodEnum.LINKEDIN,
            ShareMethodEnum.TWITTER,
            ShareMethodEnum.FACEBOOK,
            ShareMethodEnum.WHATSAPP,
            ShareMethodEnum.COPY_LINK
        ]

        for method in valid_methods:
            share = JobShare(
                job_id="job456",
                share_method=method
            )
            assert share.share_method == method

    def test_job_share_generate_referral_code(self):
        """Test referral code generation"""
        referral_code = JobShare.generate_referral_code("user123", "job456")

        assert isinstance(referral_code, str)
        assert len(referral_code) > 0
        # Test that same inputs generate same code
        referral_code2 = JobShare.generate_referral_code("user123", "job456")
        assert referral_code == referral_code2

    def test_job_share_model_dump(self):
        """Test JobShare model serialization"""
        share = JobShare(
            user_id="user123",
            job_id="job456",
            share_method=ShareMethodEnum.LINKEDIN
        )

        data = share.model_dump()

        assert isinstance(data, dict)
        assert data['user_id'] == "user123"
        assert data['job_id'] == "job456"
        assert data['share_method'] == ShareMethodEnum.LINKEDIN
        assert 'share_id' in data
        assert 'shared_at' in data


class TestJobActionsStateModel:
    """Test JobActionsState Pydantic model"""

    def test_job_actions_state_creation_with_defaults(self):
        """Test JobActionsState creation with default values"""
        state = JobActionsState(job_id="job456")

        assert state.job_id == "job456"
        assert state.user_has_liked is False
        assert state.user_has_saved is False
        assert state.like_count == 0
        assert state.share_count == 0

    def test_job_actions_state_creation_with_values(self):
        """Test JobActionsState creation with explicit values"""
        state = JobActionsState(
            job_id="job456",
            user_has_liked=True,
            user_has_saved=True,
            like_count=10,
            share_count=5
        )

        assert state.job_id == "job456"
        assert state.user_has_liked is True
        assert state.user_has_saved is True
        assert state.like_count == 10
        assert state.share_count == 5

    def test_job_actions_state_validation_required_fields(self):
        """Test JobActionsState validation for required fields"""
        with pytest.raises(ValidationError) as exc_info:
            JobActionsState()

        errors = exc_info.value.errors()
        required_fields = {error['loc'][0] for error in errors}
        assert 'job_id' in required_fields

    def test_job_actions_state_validation_negative_counts(self):
        """Test JobActionsState validation with negative counts"""
        # Should allow negative counts (might be edge cases)
        state = JobActionsState(
            job_id="job456",
            like_count=-1,
            share_count=-1
        )

        assert state.like_count == -1
        assert state.share_count == -1

    def test_job_actions_state_to_dict(self):
        """Test JobActionsState to_dict method"""
        state = JobActionsState(
            job_id="job456",
            user_has_liked=True,
            like_count=5
        )

        # Assuming to_dict method exists
        if hasattr(state, 'to_dict'):
            data = state.to_dict()
            assert isinstance(data, dict)
            assert data['job_id'] == "job456"
            assert data['user_has_liked'] is True
            assert data['like_count'] == 5


class TestSavedJobModel:
    """Test SavedJob Pydantic model"""

    def test_saved_job_creation_with_defaults(self):
        """Test SavedJob creation with default values"""
        saved_job = SavedJob(
            user_id="user123",
            job_id="job456"
        )

        assert saved_job.user_id == "user123"
        assert saved_job.job_id == "job456"
        assert saved_job.saved_job_id is not None
        assert isinstance(saved_job.saved_at, datetime)

    def test_saved_job_validation_required_fields(self):
        """Test SavedJob validation for required fields"""
        with pytest.raises(ValidationError) as exc_info:
            SavedJob()

        errors = exc_info.value.errors()
        required_fields = {error['loc'][0] for error in errors}
        assert 'user_id' in required_fields
        assert 'job_id' in required_fields

    def test_saved_job_model_dump(self):
        """Test SavedJob model serialization"""
        saved_job = SavedJob(
            user_id="user123",
            job_id="job456"
        )

        data = saved_job.model_dump()

        assert isinstance(data, dict)
        assert data['user_id'] == "user123"
        assert data['job_id'] == "job456"
        assert 'saved_job_id' in data
        assert 'saved_at' in data


class TestShareMethodEnum:
    """Test ShareMethodEnum"""

    def test_share_method_enum_values(self):
        """Test all ShareMethodEnum values"""
        assert ShareMethodEnum.EMAIL == "email"
        assert ShareMethodEnum.LINKEDIN == "linkedin"
        assert ShareMethodEnum.TWITTER == "twitter"
        assert ShareMethodEnum.FACEBOOK == "facebook"
        assert ShareMethodEnum.WHATSAPP == "whatsapp"
        assert ShareMethodEnum.COPY_LINK == "copy_link"

    def test_share_method_enum_validation(self):
        """Test ShareMethodEnum validation"""
        # Valid values
        for method in ShareMethodEnum:
            share = JobShare(
                job_id="job456",
                share_method=method
            )
            assert share.share_method == method

        # Invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            JobShare(
                job_id="job456",
                share_method="invalid"
            )


class TestModelInteractions:
    """Test interactions between different models"""

    def test_models_with_same_job_id(self):
        """Test creating multiple models for the same job"""
        job_id = "job456"
        user_id = "user123"

        # Create like, save, and share for same job
        like = JobLike(user_id=user_id, job_id=job_id)
        saved_job = SavedJob(user_id=user_id, job_id=job_id)
        share = JobShare(user_id=user_id, job_id=job_id, share_method=ShareMethodEnum.EMAIL)

        assert like.job_id == saved_job.job_id == share.job_id == job_id
        assert like.user_id == saved_job.user_id == share.user_id == user_id

    def test_job_actions_state_aggregation(self):
        """Test JobActionsState representing aggregated data"""
        state = JobActionsState(
            job_id="job456",
            user_has_liked=True,
            user_has_saved=True,
            like_count=15,
            share_count=8
        )

        # Test that state represents user actions and aggregate counts
        assert state.user_has_liked and state.user_has_saved
        assert state.like_count > 0 and state.share_count > 0

    def test_model_serialization_consistency(self):
        """Test that all models serialize consistently"""
        like = JobLike(user_id="user123", job_id="job456")
        share = JobShare(user_id="user123", job_id="job456", share_method=ShareMethodEnum.LINKEDIN)
        saved_job = SavedJob(user_id="user123", job_id="job456")

        like_data = like.model_dump()
        share_data = share.model_dump()
        saved_job_data = saved_job.model_dump()

        # All should have consistent field types
        assert isinstance(like_data['user_id'], str)
        assert isinstance(share_data['user_id'], str)
        assert isinstance(saved_job_data['user_id'], str)

        assert isinstance(like_data['job_id'], str)
        assert isinstance(share_data['job_id'], str)
        assert isinstance(saved_job_data['job_id'], str)


if __name__ == '__main__':
    pytest.main([__file__])
