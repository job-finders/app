# tests/conftest.py

import pytest

from src.utils.route_helpers import get_controller
from flask import Flask, current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base  # Replace with actual base model


@pytest.fixture(scope="function")
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    yield Session()
    engine.dispose()

@pytest.fixture(scope="module")
def test_app():
    from src.config import config_instance
    from src.main import create_app
    app = create_app(config_instance())  # or import your actual app instance
    # optionally load config, init extensions, etc.
    with app.app_context():
        yield app

@pytest.fixture(params=[
    "jobs_search", "jobs_workflow", "resume", "company", "users",
    "ats", "job_seeker_profile", "employer_agents", "employee_agents",
    "admin_controller", "user_engagement", "billing"])
def get_controller(test_app, request):
    return get_controller(request.param)


# @pytest.fixture
# def job_search_controller():
#     with current_app.app_context():
#         return get_controller("jobs_search")

# @pytest.fixture
# def job_workflow_controller():
#     with current_app.app_context():
#         return get_controller("jobs_workflow")

# @pytest.fixture
# def resume_controller():
#     with current_app.app_context():
#         return get_controller("resume")

# @pytest.fixture
# def company_controller():
#     with current_app.app_context():
#         return get_controller("company")

# @pytest.fixture
# def users_controller():
#     with current_app.app_context():
#         return get_controller("users")

# @pytest.fixture
# def ats_controller():
#     with current_app.app_context():
#         return get_controller("ats")

# @pytest.fixture
# def job_seeker_controller():
#     with current_app.app_context():
#         return get_controller("job_seeker_profile")

# @pytest.fixture
# def employer_agents_controller():
#     with current_app.app_context():
#         return get_controller("employer_agents")


# @pytest.fixture
# def employee_agents_controller():
#     with current_app.app_context():
#         return get_controller("employee_agents")

# @pytest.fixture
# def admin_controller_controller():
#     with current_app.app_context():
#         return get_controller("admin_controller")

# @pytest.fixture
# def user_engagement_controller():
#     with current_app.app_context():
#         return get_controller("user_engagement")

# @pytest.fixture
# def billing_controller():
#     with current_app.app_context():
#         return get_controller("billing")
