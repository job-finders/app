import unittest
from tests.base import BaseTestCase
from src.database.models import User
from src import db

class DashboardRouteTests(BaseTestCase):
    """Test dashboard routes and functionality"""

    def test_dashboard_requires_login(self):
        """Test dashboard requires authentication"""
        response = self.client.get('/jobseeker/dashboard')
        self.assertEqual(response.status_code, 302)  # Should redirect to login

    def test_dashboard_with_valid_user(self):
        """Test dashboard with authenticated user"""
        # Create test user
        user = User(email='test@example.com', password='testpass')
        db.session.add(user)
        db.session.commit()

        # Login
        self.login(user.email, 'testpass')

        # Access dashboard
        response = self.client.get('/jobseeker/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

    def test_dashboard_stats_loading(self):
        """Test dashboard statistics are loaded"""
        user = User(email='test@example.com', password='testpass')
        db.session.add(user)
        db.session.commit()

        self.login(user.email, 'testpass')
        
        response = self.client.get('/jobseeker/dashboard')
        self.assertIn(b'applications_count', response.data)
        self.assertIn(b'saved_jobs_count', response.data)

if __name__ == '__main__':
    unittest.main()