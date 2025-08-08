import unittest
from tests.base import BaseTestCase
from src.database.models import Job, User
from src import db

class JobSearchRouteTests(BaseTestCase):
    """Test job search routes and functionality"""

    def setUp(self):
        super().setUp()
        # Add test data
        self.job = Job(
            title='Software Engineer',
            description='Looking for Python developer',
            location='Remote',
            status='active'
        )
        db.session.add(self.job)
        db.session.commit()

    def test_job_search_route(self):
        """Test basic job search route"""
        response = self.client.get('/jobs/search?keyword=python')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Software Engineer', response.data)

    def test_job_filters(self):
        """Test job filtering by location"""
        response = self.client.get('/jobs/location/Remote')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Software Engineer', response.data)

    def test_job_detail_route(self):
        """Test individual job view"""
        response = self.client.get(f'/jobs/{self.job.job_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Software Engineer', response.data)

    def test_nonexistent_job(self):
        """Test 404 for non-existent job"""
        response = self.client.get('/jobs/invalid-id')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()