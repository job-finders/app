import unittest
from flask_testing import TestCase
from tests.conftest import app

class BaseTestCase(TestCase):
    """Base test case class with common utilities"""

    def create_app(self):
        return app

    def setUp(self):
        self.client = self.app.test_client()
        
    def tearDown(self):
        pass

    def login(self, email, password):
        return self.client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)