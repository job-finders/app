"""
Test dashboard Browse Jobs button routing functionality.
"""
import pytest
from flask import url_for


def test_browse_jobs_route_exists(test_app):
    """Test that the browse jobs route exists and is accessible."""
    with test_app.test_client() as client:
        with test_app.app_context():
            # Test that the route exists
            browse_jobs_url = url_for('jobs.list_jobs')
            assert browse_jobs_url == '/jobs/browse-jobs'
            
            # Test that the route is accessible (though it may require authentication)
            response = client.get(browse_jobs_url)
            # The route should exist (not return 404), even if it redirects due to auth
            assert response.status_code != 404


def test_dashboard_template_has_correct_browse_jobs_link(test_app):
    """Test that the dashboard template generates the correct Browse Jobs URL."""
    with test_app.app_context():
        # Test that url_for generates the correct URL for the Browse Jobs button
        browse_jobs_url = url_for('jobs.list_jobs')
        assert browse_jobs_url == '/jobs/browse-jobs'
        
        # Verify the route name matches what we expect
        assert 'jobs.list_jobs' in [rule.endpoint for rule in test_app.url_map.iter_rules()]


def test_jobs_blueprint_registered(test_app):
    """Test that the jobs blueprint is properly registered."""
    # Check that the jobs blueprint routes are registered
    job_routes = [rule for rule in test_app.url_map.iter_rules() if rule.endpoint.startswith('jobs.')]
    
    # Should have at least the list_jobs route
    job_endpoints = [rule.endpoint for rule in job_routes]
    assert 'jobs.list_jobs' in job_endpoints
    
    # Verify the browse-jobs route exists
    browse_jobs_routes = [rule for rule in job_routes if rule.rule == '/jobs/browse-jobs']
    assert len(browse_jobs_routes) == 1
    assert browse_jobs_routes[0].endpoint == 'jobs.list_jobs'