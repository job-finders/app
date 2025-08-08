import pytest
from src import create_app
from src.database.sql.config import db as _db
from src.database.models import User


@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for tests"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A CLI runner for the app"""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        user = User(
            email='test@example.com',
            password='testpass',
            first_name='Test',
            last_name='User'
        )
        _db.session.add(user)
        _db.session.commit()
        return user
