#!/usr/bin/env python3
"""
Integration Test Runner for Job Actions Feature

Runs comprehensive integration tests for the job actions feature including:
- API endpoint integration
- Database operation integration
- Cache integration
- Authentication flow integration
- End-to-end workflows
"""

import os
import sys
import subprocess
import pytest
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_integration_tests_with_coverage():
    """Run all job actions integration tests with coverage reporting"""

    # Integration test files to run
    test_files = [
        'tests/integration/test_job_actions_api_integration.py',
        'tests/integration/test_job_actions_database_integration.py',
        'tests/integration/test_job_actions_cache_integration.py',
        'tests/integration/test_job_actions_auth_integration.py'
    ]

    # Source files to include in coverage
    source_files = [
        'src/controllers/jobs/actions.py',
        'src/controllers/company/public.py',
        'src/services/job_actions_analytics.py',
        'src/routes/jobs_routes/actions.py',
        'src/routes/jobs_routes/analytics.py',
        'src/routes/company_routes/public.py',
        'src/cache/job_actions_cache.py',
        'src/firewall/job_actions_security.py'
    ]

    print("🔗 Running Job Actions Integration Tests with Coverage...")
    print("=" * 70)

    # Build pytest command with coverage
    cmd = [
              'python', '-m', 'pytest',
              '--cov=' + ','.join(source_files),
              '--cov-report=html:tests/integration_coverage_html',
              '--cov-report=term-missing',
              '--cov-fail-under=85',  # Slightly lower for integration tests
              '--verbose',
              '--tb=short',
              '--maxfail=5',  # Stop after 5 failures
              '-x'  # Stop on first failure for debugging
          ] + test_files

    try:
        # Run tests
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print("\n✅ All integration tests passed with sufficient coverage!")
            print("📊 Coverage report generated in tests/integration_coverage_html/")
        else:
            print(f"\n❌ Integration tests failed with return code {result.returncode}")
            return False

    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest and pytest-cov:")
        print("pip install pytest pytest-cov")
        return False

    return result.returncode == 0


def run_specific_integration_category(category):
    """Run integration tests for a specific category"""

    categories = {
        'api': [
            'tests/integration/test_job_actions_api_integration.py'
        ],
        'database': [
            'tests/integration/test_job_actions_database_integration.py'
        ],
        'cache': [
            'tests/integration/test_job_actions_cache_integration.py'
        ],
        'auth': [
            'tests/integration/test_job_actions_auth_integration.py'
        ]
    }

    if category not in categories:
        print(f"❌ Unknown category: {category}")
        print(f"Available categories: {', '.join(categories.keys())}")
        return False

    test_files = categories[category]

    print(f"🔗 Running {category.title()} Integration Tests...")
    print("=" * 50)

    cmd = [
              'python', '-m', 'pytest',
              '--verbose',
              '--tb=short',
              '--maxfail=3'
          ] + test_files

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest:")
        print("pip install pytest")
        return False


def run_end_to_end_workflow_tests():
    """Run end-to-end workflow integration tests"""
    print("🌐 Running End-to-End Workflow Tests...")
    print("=" * 40)

    cmd = [
        'python', '-m', 'pytest',
        'tests/integration/test_job_actions_api_integration.py::TestEndToEndWorkflows',
        '--verbose',
        '--tb=short'
    ]

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest:")
        print("pip install pytest")
        return False


def check_integration_test_files_exist():
    """Check that all integration test files exist"""
    test_files = [
        'tests/integration/test_job_actions_api_integration.py',
        'tests/integration/test_job_actions_database_integration.py',
        'tests/integration/test_job_actions_cache_integration.py',
        'tests/integration/test_job_actions_auth_integration.py'
    ]

    missing_files = []
    for test_file in test_files:
        if not (project_root / test_file).exists():
            missing_files.append(test_file)

    if missing_files:
        print("❌ Missing integration test files:")
        for file in missing_files:
            print(f"  - {file}")
        return False

    print("✅ All integration test files found")
    return True


def generate_integration_test_summary():
    """Generate a summary of integration test coverage"""

    print("\n📋 Job Actions Integration Test Summary")
    print("=" * 60)

    test_categories = {
        "API Integration": [
            "Complete like/unlike workflow",
            "Complete save/unsave workflow",
            "Authenticated vs anonymous sharing",
            "Job actions state retrieval",
            "Company public profile access",
            "Analytics API endpoints",
            "Error handling and validation",
            "Rate limiting integration"
        ],
        "Database Integration": [
            "ORM CRUD operations",
            "Database relationships and joins",
            "Transaction handling and rollback",
            "Constraint enforcement",
            "Bulk operations performance",
            "Index usage optimization",
            "Foreign key validation",
            "Data consistency checks"
        ],
        "Cache Integration": [
            "Job actions state caching",
            "Cache invalidation on actions",
            "Company profile caching",
            "Cache warming strategies",
            "Cache consistency across operations",
            "Performance optimization",
            "Error handling and fallback",
            "TTL and expiration handling"
        ],
        "Authentication Integration": [
            "JWT token validation",
            "User session management",
            "Anonymous vs authenticated flows",
            "Permission-based access control",
            "Rate limiting with auth context",
            "CSRF protection integration",
            "User context propagation",
            "Authorization error handling"
        ]
    }

    for category, tests in test_categories.items():
        print(f"\n{category}:")
        for test in tests:
            print(f"  ✓ {test}")

    print(f"\n📊 Total Integration Categories: {len(test_categories)}")
    print(f"📊 Total Integration Test Areas: {sum(len(tests) for tests in test_categories.values())}")
    print("\n🎯 Coverage Target: 85% minimum for integration tests")


def run_performance_integration_tests():
    """Run performance-focused integration tests"""
    print("⚡ Running Performance Integration Tests...")
    print("=" * 45)

    cmd = [
        'python', '-m', 'pytest',
        'tests/integration/',
        '-k', 'performance or bulk or cache',
        '--verbose',
        '--tb=short',
        '--durations=10'  # Show 10 slowest tests
    ]

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest:")
        print("pip install pytest")
        return False


def validate_integration_test_environment():
    """Validate that the integration test environment is properly set up"""
    print("🔍 Validating Integration Test Environment...")
    print("=" * 50)

    # Check required dependencies
    required_packages = ['pytest', 'pytest-cov', 'flask', 'sqlalchemy', 'redis']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall with: pip install " + " ".join(missing_packages))
        return False

    # Check test database configuration
    test_db_url = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    print(f"✅ Test database: {test_db_url}")

    # Check Redis configuration for cache tests
    redis_url = os.environ.get('TEST_REDIS_URL', 'redis://localhost:6379/1')
    print(f"✅ Test Redis: {redis_url}")

    print("✅ Integration test environment validated")
    return True


def main():
    """Main integration test runner function"""

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'check':
            return check_integration_test_files_exist()
        elif command == 'summary':
            generate_integration_test_summary()
            return True
        elif command == 'validate':
            return validate_integration_test_environment()
        elif command in ['api', 'database', 'cache', 'auth']:
            return run_specific_integration_category(command)
        elif command == 'e2e':
            return run_end_to_end_workflow_tests()
        elif command == 'performance':
            return run_performance_integration_tests()
        elif command == 'help':
            print("Job Actions Integration Test Runner")
            print("\nUsage:")
            print("  python tests/run_job_actions_integration_tests.py [command]")
            print("\nCommands:")
            print("  (no command)  - Run all integration tests with coverage")
            print("  check         - Check if all test files exist")
            print("  summary       - Show integration test summary")
            print("  validate      - Validate test environment setup")
            print("  api           - Run API integration tests only")
            print("  database      - Run database integration tests only")
            print("  cache         - Run cache integration tests only")
            print("  auth          - Run authentication integration tests only")
            print("  e2e           - Run end-to-end workflow tests only")
            print("  performance   - Run performance integration tests only")
            print("  help          - Show this help message")
            return True
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'help' for available commands")
            return False
    else:
        # Run all integration tests with coverage
        if not check_integration_test_files_exist():
            return False

        if not validate_integration_test_environment():
            return False

        success = run_integration_tests_with_coverage()

        if success:
            generate_integration_test_summary()

        return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
