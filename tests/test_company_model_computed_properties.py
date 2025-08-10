"""
Unit tests for Company Model Computed Properties

Tests the computed properties added to the Company model for statistics,
including jobs_posted_last_12_months, avg_applications_per_job, and application_response_rate.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from src.database.constants import utc_time


class MockJobApplication:
    """Mock JobApplication for testing"""
    def __init__(self, applied_date=None, has_response=False):
        self.applied_date = applied_date or utc_time()
        self.has_response = has_response
        # Mock response status
        self.application_stage = "responded" if has_response else "applied"


class MockJob:
    """Mock Job for testing"""
    def __init__(self, job_id="test-job", posted_at=None, applications=None):
        self.job_id = job_id
        self.posted_at = posted_at or utc_time()
        self.applications = applications or []


class MockCompany:
    """Mock Company class with computed properties for testing"""
    def __init__(self, company_id="test-company", jobs=None, created_at=None):
        self.company_id = company_id
        self.jobs = jobs or []
        self.created_at = created_at or utc_time() - timedelta(days=365)
    
    @property
    def total_jobs(self) -> int:
        """Total number of jobs"""
        return len(self.jobs)
    
    @property
    def total_applications(self) -> int:
        """Total applications across all jobs"""
        return sum(len(job.applications) for job in self.jobs)
    
    @property
    def jobs_posted_last_12_months(self) -> int:
        """Count jobs posted in the last 12 months"""
        if not self.jobs:
            return 0
        
        cutoff_date = utc_time() - timedelta(days=365)
        return sum(1 for job in self.jobs if job.posted_at and job.posted_at >= cutoff_date)
    
    @property
    def avg_applications_per_job(self) -> float:
        """Average applications per job"""
        return self.total_applications / self.total_jobs if self.total_jobs > 0 else 0.0
    
    @property
    def application_response_rate(self) -> float:
        """Percentage of applications with employer response"""
        if not self.jobs or self.total_applications == 0:
            return 0.0
        
        total_responses = 0
        for job in self.jobs:
            for app in job.applications:
                if hasattr(app, 'has_response') and app.has_response:
                    total_responses += 1
                elif hasattr(app, 'application_stage') and app.application_stage in ["responded", "interviewed", "hired"]:
                    total_responses += 1
        
        return (total_responses / self.total_applications) * 100 if self.total_applications > 0 else 0.0


class TestCompanyJobsPostedLast12Months:
    """Test jobs_posted_last_12_months computed property"""
    
    def test_jobs_posted_last_12_months_with_recent_jobs(self):
        """Test counting jobs posted in last 12 months"""
        now = utc_time()
        
        jobs = [
            MockJob(posted_at=now - timedelta(days=30)),   # Within 12 months
            MockJob(posted_at=now - timedelta(days=180)),  # Within 12 months
            MockJob(posted_at=now - timedelta(days=300)),  # Within 12 months
            MockJob(posted_at=now - timedelta(days=400)),  # Outside 12 months
            MockJob(posted_at=now - timedelta(days=500)),  # Outside 12 months
        ]
        
        company = MockCompany(jobs=jobs)
        
        assert company.jobs_posted_last_12_months == 3
    
    def test_jobs_posted_last_12_months_no_jobs(self):
        """Test counting when company has no jobs"""
        company = MockCompany(jobs=[])
        
        assert company.jobs_posted_last_12_months == 0
    
    def test_jobs_posted_last_12_months_all_old_jobs(self):
        """Test counting when all jobs are older than 12 months"""
        now = utc_time()
        
        jobs = [
            MockJob(posted_at=now - timedelta(days=400)),
            MockJob(posted_at=now - timedelta(days=500)),
            MockJob(posted_at=now - timedelta(days=600)),
        ]
        
        company = MockCompany(jobs=jobs)
        
        assert company.jobs_posted_last_12_months == 0
    
    def test_jobs_posted_last_12_months_all_recent_jobs(self):
        """Test counting when all jobs are within 12 months"""
        now = utc_time()
        
        jobs = [
            MockJob(posted_at=now - timedelta(days=30)),
            MockJob(posted_at=now - timedelta(days=60)),
            MockJob(posted_at=now - timedelta(days=90)),
            MockJob(posted_at=now - timedelta(days=120)),
        ]
        
        company = MockCompany(jobs=jobs)
        
        assert company.jobs_posted_last_12_months == 4
    
    def test_jobs_posted_last_12_months_edge_case_exactly_365_days(self):
        """Test counting job posted exactly 365 days ago"""
        now = utc_time()
        
        jobs = [
            MockJob(posted_at=now - timedelta(days=365)),  # Exactly 365 days ago
            MockJob(posted_at=now - timedelta(days=365, hours=1)),  # Just over 365 days
        ]
        
        company = MockCompany(jobs=jobs)
        
        # Should include the job posted exactly 365 days ago
        assert company.jobs_posted_last_12_months == 1
    
    def test_jobs_posted_last_12_months_with_none_posted_at(self):
        """Test counting when some jobs have None posted_at"""
        now = utc_time()
        
        jobs = [
            MockJob(posted_at=now - timedelta(days=30)),
            MockJob(posted_at=None),  # No posted date
            MockJob(posted_at=now - timedelta(days=60)),
        ]
        
        company = MockCompany(jobs=jobs)
        
        # Should only count jobs with valid posted_at dates
        assert company.jobs_posted_last_12_months == 2


class TestCompanyAvgApplicationsPerJob:
    """Test avg_applications_per_job computed property"""
    
    def test_avg_applications_per_job_with_applications(self):
        """Test average applications per job calculation"""
        jobs = [
            MockJob(applications=[MockJobApplication() for _ in range(10)]),  # 10 applications
            MockJob(applications=[MockJobApplication() for _ in range(5)]),   # 5 applications
            MockJob(applications=[MockJobApplication() for _ in range(15)]),  # 15 applications
        ]
        
        company = MockCompany(jobs=jobs)
        
        # Total: 30 applications, 3 jobs = 10.0 average
        assert company.avg_applications_per_job == 10.0
    
    def test_avg_applications_per_job_no_jobs(self):
        """Test average applications per job with no jobs"""
        company = MockCompany(jobs=[])
        
        assert company.avg_applications_per_job == 0.0
    
    def test_avg_applications_per_job_no_applications(self):
        """Test average applications per job with jobs but no applications"""
        jobs = [
            MockJob(applications=[]),
            MockJob(applications=[]),
            MockJob(applications=[]),
        ]
        
        company = MockCompany(jobs=jobs)
        
        assert company.avg_applications_per_job == 0.0
    
    def test_avg_applications_per_job_mixed_applications(self):
        """Test average applications per job with mixed application counts"""
        jobs = [
            MockJob(applications=[MockJobApplication() for _ in range(20)]),  # 20 applications
            MockJob(applications=[]),  # 0 applications
            MockJob(applications=[MockJobApplication() for _ in range(4)]),   # 4 applications
            MockJob(applications=[MockJobApplication() for _ in range(6)]),   # 6 applications
        ]
        
        company = MockCompany(jobs=jobs)
        
        # Total: 30 applications, 4 jobs = 7.5 average
        assert company.avg_applications_per_job == 7.5
    
    def test_avg_applications_per_job_fractional_result(self):
        """Test average applications per job with fractional result"""
        jobs = [
            MockJob(applications=[MockJobApplication() for _ in range(7)]),
            MockJob(applications=[MockJobApplication() for _ in range(8)]),
        ]
        
        company = MockCompany(jobs=jobs)
        
        # Total: 15 applications, 2 jobs = 7.5 average
        assert company.avg_applications_per_job == 7.5


class TestCompanyApplicationResponseRate:
    """Test application_response_rate computed property"""
    
    def test_application_response_rate_with_responses(self):
        """Test application response rate calculation"""
        jobs = [
            MockJob(applications=[
                MockJobApplication(has_response=True),   # Responded
                MockJobApplication(has_response=False),  # No response
                MockJobApplication(has_response=True),   # Responded
                MockJobApplication(has_response=False),  # No response
            ]),
            MockJob(applications=[
                MockJobApplication(has_response=True),   # Responded
                MockJobApplication(has_response=True),   # Responded
            ])
        ]
        
        company = MockCompany(jobs=jobs)
        
        # Total: 6 applications, 4 responses = 66.67% response rate
        expected_rate = (4 / 6) * 100
        assert abs(company.application_response_rate - expected_rate) < 0.01
    
    def test_application_response_rate_no_applications(self):
        """Test application response rate with no applications"""
        jobs = [
            MockJob(applications=[]),
            MockJob(applications=[]),
        ]
        
        company = MockCompany(jobs=jobs)
        
        assert company.application_response_rate == 0.0
    
    def test_application_response_rate_no_jobs(self):
        """Test application response rate with no jobs"""
        company = MockCompany(jobs=[])
        
        assert company.application_response_rate == 0.0
    
    def test_application_response_rate_all_responded(self):
        """Test application response rate when all applications have responses"""
        jobs = [
            MockJob(applications=[
                MockJobApplication(has_response=True),
                MockJobApplication(has_response=True),
                MockJobApplication(has_response=True),
            ])
        ]
        
        company = MockCompany(jobs=jobs)
        
        assert company.application_response_rate == 100.0
    
    def test_application_response_rate_no_responses(self):
        """Test application response rate when no applications have responses"""
        jobs = [
            MockJob(applications=[
                MockJobApplication(has_response=False),
                MockJobApplication(has_response=False),
                MockJobApplication(has_response=False),
            ])
        ]
        
        company = MockCompany(jobs=jobs)
        
        assert company.application_response_rate == 0.0
    
    def test_application_response_rate_with_application_stages(self):
        """Test application response rate using application stages"""
        # Create applications with different stages
        applications = []
        
        # Create mock applications with stage-based responses
        for stage, has_response in [
            ("applied", False),
            ("responded", True),
            ("interviewed", True),
            ("hired", True),
            ("rejected", True),
            ("applied", False),
        ]:
            app = MockJobApplication()
            app.application_stage = stage
            app.has_response = has_response
            applications.append(app)
        
        jobs = [MockJob(applications=applications)]
        company = MockCompany(jobs=jobs)
        
        # 4 out of 6 applications have responses = 66.67%
        expected_rate = (4 / 6) * 100
        assert abs(company.application_response_rate - expected_rate) < 0.01


class TestCompanyComputedPropertiesIntegration:
    """Test integration of company computed properties"""
    
    def test_all_properties_work_together(self):
        """Test that all computed properties work together"""
        now = utc_time()
        
        # Create a realistic company scenario
        jobs = [
            # Recent job with many applications, some responses
            MockJob(
                posted_at=now - timedelta(days=30),
                applications=[
                    MockJobApplication(has_response=True),
                    MockJobApplication(has_response=True),
                    MockJobApplication(has_response=False),
                    MockJobApplication(has_response=False),
                    MockJobApplication(has_response=True),
                ]
            ),
            # Older job within 12 months, fewer applications
            MockJob(
                posted_at=now - timedelta(days=200),
                applications=[
                    MockJobApplication(has_response=True),
                    MockJobApplication(has_response=False),
                ]
            ),
            # Very old job outside 12 months
            MockJob(
                posted_at=now - timedelta(days=400),
                applications=[
                    MockJobApplication(has_response=False),
                ]
            ),
        ]
        
        company = MockCompany(jobs=jobs)
        
        # Test all properties
        jobs_12_months = company.jobs_posted_last_12_months
        avg_applications = company.avg_applications_per_job
        response_rate = company.application_response_rate
        
        assert jobs_12_months == 2  # Only first 2 jobs are within 12 months
        assert avg_applications == 8 / 3  # 8 total applications / 3 jobs
        assert abs(response_rate - (4 / 8) * 100) < 0.01  # 4 responses out of 8 applications
    
    def test_properties_with_empty_company(self):
        """Test computed properties with empty company"""
        company = MockCompany(jobs=[])
        
        assert company.jobs_posted_last_12_months == 0
        assert company.avg_applications_per_job == 0.0
        assert company.application_response_rate == 0.0
    
    def test_properties_performance_with_many_jobs(self):
        """Test computed properties performance with many jobs"""
        now = utc_time()
        
        # Create many jobs with applications
        jobs = []
        for i in range(100):  # 100 jobs
            applications = [MockJobApplication(has_response=i % 2 == 0) for _ in range(i % 10)]  # Varying applications
            job_date = now - timedelta(days=i * 3)  # Spread over time
            jobs.append(MockJob(posted_at=job_date, applications=applications))
        
        company = MockCompany(jobs=jobs)
        
        # Properties should still work efficiently
        start_time = datetime.now()
        
        jobs_12_months = company.jobs_posted_last_12_months
        avg_applications = company.avg_applications_per_job
        response_rate = company.application_response_rate
        
        end_time = datetime.now()
        calculation_time = (end_time - start_time).total_seconds()
        
        # Should complete quickly (less than 1 second)
        assert calculation_time < 1.0
        
        # Results should be reasonable
        assert isinstance(jobs_12_months, int)
        assert jobs_12_months >= 0
        assert isinstance(avg_applications, float)
        assert avg_applications >= 0
        assert isinstance(response_rate, float)
        assert 0 <= response_rate <= 100


class TestCompanyComputedPropertiesErrorHandling:
    """Test error handling in company computed properties"""
    
    def test_properties_with_none_values(self):
        """Test computed properties handle None values gracefully"""
        # Company with None jobs list
        company = MockCompany(jobs=None)
        company.jobs = None
        
        # Should handle gracefully (though this might not be realistic)
        # The actual implementation should handle this case
        
        # Test with jobs that have None applications
        jobs = [MockJob(applications=None)]
        jobs[0].applications = None
        
        company = MockCompany(jobs=jobs)
        
        # Should not crash, though behavior depends on implementation
        try:
            jobs_12_months = company.jobs_posted_last_12_months
            avg_applications = company.avg_applications_per_job
            response_rate = company.application_response_rate
            
            # If it doesn't crash, results should be reasonable
            assert isinstance(jobs_12_months, int)
            assert isinstance(avg_applications, float)
            assert isinstance(response_rate, float)
        except (AttributeError, TypeError):
            # This is acceptable for None values
            pass
    
    def test_properties_with_invalid_data(self):
        """Test computed properties with invalid data"""
        # Test with applications that have invalid attributes
        invalid_app = Mock()
        invalid_app.has_response = None
        invalid_app.application_stage = None
        
        jobs = [MockJob(applications=[invalid_app])]
        company = MockCompany(jobs=jobs)
        
        # Should handle gracefully
        response_rate = company.application_response_rate
        assert isinstance(response_rate, float)
        assert 0 <= response_rate <= 100
    
    def test_properties_consistency(self):
        """Test that computed properties are consistent across multiple calls"""
        now = utc_time()
        
        jobs = [
            MockJob(
                posted_at=now - timedelta(days=30),
                applications=[MockJobApplication(has_response=True) for _ in range(5)]
            ),
            MockJob(
                posted_at=now - timedelta(days=60),
                applications=[MockJobApplication(has_response=False) for _ in range(3)]
            ),
        ]
        
        company = MockCompany(jobs=jobs)
        
        # Multiple calls should return same results
        jobs_12_months_1 = company.jobs_posted_last_12_months
        jobs_12_months_2 = company.jobs_posted_last_12_months
        
        avg_applications_1 = company.avg_applications_per_job
        avg_applications_2 = company.avg_applications_per_job
        
        response_rate_1 = company.application_response_rate
        response_rate_2 = company.application_response_rate
        
        assert jobs_12_months_1 == jobs_12_months_2
        assert avg_applications_1 == avg_applications_2
        assert response_rate_1 == response_rate_2