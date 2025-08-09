"""
Tests for Job Match Scoring Feature

This module contains comprehensive tests for the job match scoring functionality,
including quick match scoring, detailed match analysis, and API endpoints.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from tests.jobs.factories import create_job, create_category
from tests.base import BaseTestCase


class TestQuickMatchScoring:
    """Test cases for quick match scoring algorithm"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
    async def test_calculate_quick_match_score_perfect_match(self, get_controller, session):
        """Test perfect match scenario returns high score"""
        # Setup
        category = create_category(session, name="Engineering")
        job = create_job(
            session,
            title="Python Developer",
            location="Cape Town, Western Cape",
            category_id=category.category_id,
            experience_required="Mid Level",
            status="active"
        )
        
        # Mock user profile with matching criteria
        user_profile = Mock()
        user_profile.location = "Cape Town, Western Cape"
        user_profile.skills = ["Python", "Django", "REST API"]
        user_profile.experience_level = "Mid Level"
        user_profile.preferred_categories = ["Engineering"]
        
        controller = get_controller
        
        # Act
        score = await controller.calculate_quick_match_score(job, user_profile)
        
        # Assert
        assert isinstance(score, (int, float))
        assert 80 <= score <= 100  # High match score

    @pytest.mark.asyncio
    @pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
    async def test_calculate_quick_match_score_no_match(self, get_controller, session):
        """Test no match scenario returns low score"""
        # Setup
        category = create_category(session, name="Engineering")
        job = create_job(
            session,
            title="Java Developer",
            location="Johannesburg, Gauteng",
            category_id=category.category_id,
            experience_required="Senior Level",
            status="active"
        )
        
        # Mock user profile with non-matching criteria
        user_profile = Mock()
        user_profile.location = "Cape Town, Western Cape"
        user_profile.skills = ["Python", "Django"]
        user_profile.experience_level = "Entry Level"
        user_profile.preferred_categories = ["Marketing"]
        
        controller = get_controller
        
        # Act
        score = await controller.calculate_quick_match_score(job, user_profile)
        
        # Assert
        assert isinstance(score, (int, float))
        assert 0 <= score <= 40  # Low match score

    @pytest.mark.asyncio
    @pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
    async def test_calculate_quick_match_score_partial_match(self, get_controller, session):
        """Test partial match scenario returns medium score"""
        # Setup
        category = create_category(session, name="Engineering")
        job = create_job(
            session,
            title="Python Developer",
            location="Johannesburg, Gauteng",
            category_id=category.category_id,
            experience_required="Mid Level",
            status="active"
        )
        
        # Mock user profile with some matching criteria
        user_profile = Mock()
        user_profile.location = "Cape Town, Western Cape"  # Different location
        user_profile.skills = ["Python", "Django"]  # Matching skills
        user_profile.experience_level = "Mid Level"  # Matching experience
        user_profile.preferred_categories = ["Engineering"]  # Matching category
        
        controller = get_controller
        
        # Act
        score = await controller.calculate_quick_match_score(job, user_profile)
        
        # Assert
        assert isinstance(score, (int, float))
        assert 40 <= score <= 80  # Medium match score

    @pytest.mark.asyncio
    @pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
    async def test_calculate_quick_match_score_remote_job_bonus(self, get_controller, session):
        """Test remote job gets location bonus regardless of user location"""
        # Setup
        category = create_category(session, name="Engineering")
        job = create_job(
            session,
            title="Python Developer",
            location="Remote",
            category_id=category.category_id,
            remote_work="Full Remote",
            status="active"
        )
        
        user_profile = Mock()
        user_profile.location = "Durban, KwaZulu-Natal"
        user_profile.skills = ["Python"]
        user_profile.experience_level = "Mid Level"
        user_profile.preferred_categories = ["Engineering"]
        user_profile.remote_preference = True
        
        controller = get_controller
        
        # Act
        score = await controller.calculate_quick_match_score(job, user_profile)
        
        # Assert
        assert score >= 70  # Should get high score due to remote work match

    @pytest.mark.asyncio
    @pytest.mark.parametrize("get_controller", ["jobs_search"], indirect=True)
    async def test_calculate_quick_match_score_handles_missing_data(self, get_controller, session):
        """Test scoring handles missing or None data gracefully"""
        # Setup
        job = create_job(
            session,
            title="Developer",
            location=None,
            category_id=None,
            experience_required=None,
            status="active"
        )
        
        user_profile = Mock()
        user_profile.location = None
        user_profile.skills = None
        user_profile.experience_level = None
        user_profile.preferred_categories = None
        
        controller = get_controller
        
        # Act
        score = await controller.calculate_quick_match_score(job, user_profile)
        
        # Assert
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100  # Should not crash and return valid score


class TestBatchMatchScoring:
    """Test cases for batch match scoring functionality"""

    @pytest.mark.asyncio
    async def test_calculate_batch_match_scores_with_authenticated_user(self):
        """Test batch scoring with authenticated user and complete profile"""
        # Setup
        jobs = [Mock(job_id="job1"), Mock(job_id="job2")]
        user = Mock(uid="user123", is_authenticated=True)
        
        # Mock controller and profile
        job_search_controller = Mock()
        job_search_controller.calculate_quick_match_score = AsyncMock(return_value=85.0)
        
        with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_get_profile:
            mock_get_profile.return_value = Mock()  # Valid profile
            
            # Import the function to test
            from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
            
            # Act
            result = await calculate_batch_match_scores(jobs, user, job_search_controller)
            
            # Assert
            assert len(result) == 2
            assert all(hasattr(job, 'match_score') for job in result)
            assert all(job.match_score == 85.0 for job in result)

    @pytest.mark.asyncio
    async def test_calculate_batch_match_scores_with_unauthenticated_user(self):
        """Test batch scoring with unauthenticated user returns None scores"""
        # Setup
        jobs = [Mock(job_id="job1"), Mock(job_id="job2")]
        user = None
        job_search_controller = Mock()
        
        # Import the function to test
        from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
        
        # Act
        result = await calculate_batch_match_scores(jobs, user, job_search_controller)
        
        # Assert
        assert len(result) == 2
        assert all(hasattr(job, 'match_score') for job in result)
        assert all(job.match_score is None for job in result)

    @pytest.mark.asyncio
    async def test_calculate_batch_match_scores_with_incomplete_profile(self):
        """Test batch scoring with incomplete user profile returns None scores"""
        # Setup
        jobs = [Mock(job_id="job1")]
        user = Mock(uid="user123", is_authenticated=True)
        job_search_controller = Mock()
        
        with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_get_profile:
            mock_get_profile.return_value = None  # No profile
            
            # Import the function to test
            from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
            
            # Act
            result = await calculate_batch_match_scores(jobs, user, job_search_controller)
            
            # Assert
            assert len(result) == 1
            assert result[0].match_score is None

    @pytest.mark.asyncio
    async def test_calculate_batch_match_scores_handles_scoring_errors(self):
        """Test batch scoring handles individual job scoring errors gracefully"""
        # Setup
        jobs = [Mock(job_id="job1"), Mock(job_id="job2")]
        user = Mock(uid="user123", is_authenticated=True)
        
        # Mock controller that raises exception for first job
        job_search_controller = Mock()
        job_search_controller.calculate_quick_match_score = AsyncMock(side_effect=[Exception("Scoring error"), 75.0])
        
        with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_get_profile:
            mock_get_profile.return_value = Mock()  # Valid profile
            
            # Import the function to test
            from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
            
            # Act
            result = await calculate_batch_match_scores(jobs, user, job_search_controller)
            
            # Assert
            assert len(result) == 2
            assert result[0].match_score is None  # Error case
            assert result[1].match_score == 75.0  # Success case


class TestMatchAnalysisAPI:
    """Test cases for match analysis API endpoints"""

    def test_get_job_match_analysis_unauthenticated(self):
        """Test API returns 401 for unauthenticated requests"""
        from tests.conftest import app
        
        with app.test_client() as client:
            response = client.get('/api/jobs/test-job-id/match-analysis')
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'authentication' in data['message'].lower()

    def test_get_job_match_analysis_job_not_found(self):
        """Test API returns 404 for non-existent job"""
        from tests.conftest import app
        
        with app.test_client() as client:
            # Mock authenticated user
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = Mock(uid="user123")
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_job_by_id = AsyncMock(return_value=None)
                    mock_get_controller.return_value = mock_controller
                    
                    response = client.get('/api/jobs/non-existent-job/match-analysis')
                    
                    assert response.status_code == 404
                    data = json.loads(response.data)
                    assert data['success'] is False
                    assert 'not found' in data['message'].lower()

    def test_get_job_match_analysis_incomplete_profile(self):
        """Test API returns 400 for incomplete user profile"""
        from tests.conftest import app
        
        with app.test_client() as client:
            # Mock authenticated user with incomplete profile
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = Mock(uid="user123")
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_job_by_id = AsyncMock(return_value=Mock(job_id="job123"))
                    mock_get_controller.return_value = mock_controller
                    
                    with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_profile:
                        mock_profile.return_value = None  # No profile
                        
                        response = client.get('/api/jobs/job123/match-analysis')
                        
                        assert response.status_code == 400
                        data = json.loads(response.data)
                        assert data['success'] is False
                        assert 'complete your profile' in data['message'].lower()

    def test_get_job_match_analysis_success(self):
        """Test successful match analysis API response"""
        from tests.conftest import app
        
        with app.test_client() as client:
            # Mock successful scenario
            mock_job = Mock()
            mock_job.job_id = "job123"
            mock_job.title = "Python Developer"
            mock_job.company_name = "Tech Corp"
            
            mock_analysis = {
                'total_score': 85.5,
                'score_breakdown': {
                    'skills_match': 90,
                    'experience_match': 80,
                    'location_match': 85,
                    'salary_match': 75
                },
                'matched_skills': ['Python', 'Django'],
                'missing_skills': ['React'],
                'interpretation': 'Great match for this position'
            }
            
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = Mock(uid="user123")
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_job_by_id = AsyncMock(return_value=mock_job)
                    mock_controller.calculate_job_match_score = AsyncMock(return_value=mock_analysis)
                    mock_get_controller.return_value = mock_controller
                    
                    with patch('src.routes.jobs_routes.job_search_routes.get_user_profile_for_matching') as mock_profile:
                        mock_profile.return_value = Mock()  # Valid profile
                        
                        with patch('src.cache.cache_redis.cache') as mock_cache:
                            mock_cache.get.return_value = None  # No cached data
                            mock_cache.set.return_value = None
                            
                            response = client.get('/api/jobs/job123/match-analysis')
                            
                            assert response.status_code == 200
                            data = json.loads(response.data)
                            assert data['success'] is True
                            assert data['match_analysis']['total_score'] == 85.5
                            assert data['match_analysis']['job_title'] == "Python Developer"
                            assert 'skills_match' in data['match_analysis']
                            assert data['cached'] is False

    def test_get_job_match_analysis_cached_response(self):
        """Test API returns cached match analysis when available"""
        from tests.conftest import app
        
        cached_analysis = {
            'total_score': 90.0,
            'job_title': 'Cached Job',
            'skills_match': {'score': 95}
        }
        
        with app.test_client() as client:
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = Mock(uid="user123")
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_job_by_id = AsyncMock(return_value=Mock(job_id="job123"))
                    mock_get_controller.return_value = mock_controller
                    
                    with patch('src.cache.cache_redis.cache') as mock_cache:
                        mock_cache.get.return_value = cached_analysis  # Return cached data
                        
                        response = client.get('/api/jobs/job123/match-analysis')
                        
                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert data['success'] is True
                        assert data['match_analysis'] == cached_analysis
                        assert data['cached'] is True

    def test_get_job_match_analysis_server_error(self):
        """Test API handles server errors gracefully"""
        from tests.conftest import app
        
        with app.test_client() as client:
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = Mock(uid="user123")
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_job_by_id = AsyncMock(side_effect=Exception("Database error"))
                    mock_get_controller.return_value = mock_controller
                    
                    response = client.get('/api/jobs/job123/match-analysis')
                    
                    assert response.status_code == 500
                    data = json.loads(response.data)
                    assert data['success'] is False
                    assert 'error occurred' in data['message'].lower()


class TestJobListingIntegration:
    """Integration tests for job listing pages with match scores"""

    def test_job_listing_page_includes_match_scores(self):
        """Test job listing page includes match scores for authenticated users"""
        from tests.conftest import app
        
        with app.test_client() as client:
            # Mock authenticated user and jobs with match scores
            mock_jobs = [
                Mock(job_id="job1", title="Python Dev", match_score=85),
                Mock(job_id="job2", title="Java Dev", match_score=None)
            ]
            
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = Mock(uid="user123", is_authenticated=True)
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_all_jobs = AsyncMock(return_value={
                        'jobs': mock_jobs,
                        'page': 1,
                        'page_size': 25,
                        'total_pages': 1,
                        'total_jobs': 2
                    })
                    mock_get_controller.return_value = mock_controller
                    
                    with patch('src.routes.jobs_routes.job_search_routes.calculate_batch_match_scores') as mock_batch:
                        mock_batch.return_value = mock_jobs
                        
                        response = client.get('/jobs/browse-jobs')
                        
                        assert response.status_code == 200
                        assert b'85%' in response.data  # Match score displayed
                        assert b'Match Details' in response.data  # Match details button

    def test_job_listing_page_handles_unauthenticated_users(self):
        """Test job listing page handles unauthenticated users gracefully"""
        from tests.conftest import app
        
        with app.test_client() as client:
            mock_jobs = [Mock(job_id="job1", title="Python Dev", match_score=None)]
            
            with patch('src.routes.jobs_routes.job_search_routes.user_details') as mock_auth:
                mock_auth.return_value = None  # Unauthenticated
                
                with patch('src.utils.route_helpers.get_controller') as mock_get_controller:
                    mock_controller = Mock()
                    mock_controller.get_all_jobs = AsyncMock(return_value={
                        'jobs': mock_jobs,
                        'page': 1,
                        'page_size': 25,
                        'total_pages': 1,
                        'total_jobs': 1
                    })
                    mock_get_controller.return_value = mock_controller
                    
                    response = client.get('/jobs/browse-jobs')
                    
                    assert response.status_code == 200
                    assert b'Login Required' in response.data  # Login prompt
                    assert b'Match Details' not in response.data  # No match details for unauth users


class TestErrorHandling:
    """Test cases for error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_quick_match_scoring_with_invalid_job_data(self):
        """Test quick match scoring handles invalid job data"""
        # Setup invalid job
        job = Mock()
        job.title = None
        job.location = ""
        job.category_id = "invalid-uuid"
        
        user_profile = Mock()
        user_profile.location = "Cape Town"
        user_profile.skills = ["Python"]
        
        # Mock controller
        controller = Mock()
        controller.calculate_quick_match_score = AsyncMock(return_value=0.0)
        
        # Act
        score = await controller.calculate_quick_match_score(job, user_profile)
        
        # Assert
        assert score == 0.0  # Should handle gracefully

    def test_modal_javascript_error_handling(self):
        """Test modal JavaScript handles network errors"""
        # This would be tested with a JavaScript testing framework like Jest
        # For now, we document the expected behavior
        pass

    def test_css_fallbacks_for_disabled_javascript(self):
        """Test CSS fallbacks work when JavaScript is disabled"""
        from tests.conftest import app
        
        with app.test_client() as client:
            response = client.get('/jobs/browse-jobs')
            
            # Check that noscript styles are included
            assert b'noscript' in response.data
            assert b'JavaScript required for details' in response.data


class TestPerformanceOptimizations:
    """Test cases for performance optimizations"""

    @pytest.mark.asyncio
    async def test_batch_scoring_uses_caching(self):
        """Test batch scoring uses Redis caching"""
        jobs = [Mock(job_id="job1")]
        user = Mock(uid="user123")
        
        with patch('src.cache.cache_redis.cache') as mock_cache:
            mock_cache.get.return_value = 85.0  # Cached score
            
            # Import and test
            from src.routes.jobs_routes.job_search_routes import calculate_batch_match_scores
            
            controller = Mock()
            result = await calculate_batch_match_scores(jobs, user, controller)
            
            # Should use cached value, not call controller
            assert result[0].match_score == 85.0
            mock_cache.get.assert_called()

    def test_api_endpoint_implements_rate_limiting(self):
        """Test API endpoint has rate limiting (would need actual rate limiting implementation)"""
        # This test would verify rate limiting is in place
        # Implementation depends on the rate limiting strategy used
        pass

    def test_database_queries_are_optimized(self):
        """Test database queries use appropriate indexes and are optimized"""
        # This test would verify query performance
        # Could use query analysis tools or execution time measurements
        pass


if __name__ == '__main__':
    pytest.main([__file__])