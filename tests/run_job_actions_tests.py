#!/usr/bin/env python3
"""
Test Runner for Job Actions Feature

Runs comprehensive unit tests for the job actions feature and generates coverage reports.
This script ensures all components meet the 90% code coverage requirement.
"""

import os
import sys
import subprocess
import pytest
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests_with_coverage():
    """Run all job actions tests with coverage reporting"""

    # Test files to run
    test_files = [
        'tests/controllers/test_job_actions_controller.py',
        'tests/controllers/test_company_public_controller.py',
        'tests/models/test_job_actions_models.py',
        'tests/database/test_job_actions_orm.py',
        'tests/services/test_job_actions_analytics.py'
    ]

    # Source files to include in coverage
    source_files = [
        'src/controllers/jobs/actions.py',
        'src/controllers/company/public.py',
        'src/services/job_actions_analytics.py',
        'src/database/models.py',  # Job actions models
        'src/routes/jobs_routes/actions.py',
        'src/routes/jobs_routes/analytics.py',
        'src/routes/company_routes/public.py'
    ]

    print("🧪 Running Job Actions Unit Tests with Coverage...")
    print("=" * 60)

    # Build pytest command with coverage
    cmd = [
              'python', '-m', 'pytest',
              '--cov=' + ','.join(source_files),
              '--cov-report=html:tests/coverage_html',
              '--cov-report=term-missing',
              '--cov-fail-under=90',  # Require 90% coverage
              '--verbose',
              '--tb=short'
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
            print("\n✅ All tests passed with sufficient coverage!")
            print("📊 Coverage report generated in tests/coverage_html/")
        else:
            print(f"\n❌ Tests failed with return code {result.returncode}")
            return False

    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest and pytest-cov:")
        print("pip install pytest pytest-cov")
        return False

    return result.returncode == 0


def run_specific_test_category(category):
    """Run tests for a specific category"""

    categories = {
        'controllers': [
            'tests/controllers/test_job_actions_controller.py',
            'tests/controllers/test_company_public_controller.py'
        ],
        'models': [
            'tests/models/test_job_actions_models.py'
        ],
        'database': [
            'tests/database/test_job_actions_orm.py'
        ],
        'services': [
            'tests/services/test_job_actions_analytics.py'
        ]
    }

    if category not in categories:
        print(f"❌ Unknown category: {category}")
        print(f"Available categories: {', '.join(categories.keys())}")
        return False

    test_files = categories[category]

    print(f"🧪 Running {category.title()} Tests...")
    print("=" * 40)

    cmd = [
              'python', '-m', 'pytest',
              '--verbose',
              '--tb=short'
          ] + test_files

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest:")
        print("pip install pytest")
        return False


def check_test_files_exist():
    """Check that all test files exist"""
    test_files = [
        'tests/controllers/test_job_actions_controller.py',
        'tests/controllers/test_company_public_controller.py',
        'tests/models/test_job_actions_models.py',
        'tests/database/test_job_actions_orm.py',
        'tests/services/test_job_actions_analytics.py'
    ]

    missing_files = []
    for test_file in test_files:
        if not (project_root / test_file).exists():
            missing_files.append(test_file)

    if missing_files:
        print("❌ Missing test files:")
        for file in missing_files:
            print(f"  - {file}")
        return False

    print("✅ All test files found")
    return True


def generate_test_summary():
    """Generate a summary of test coverage"""

    print("\n📋 Job Actions Test Summary")
    print("=" * 50)

    test_categories = {
        "Controllers": [
            "JobActionsController - like/unlike functionality",
            "JobActionsController - save/unsave functionality",
            "JobActionsController - share functionality",
            "JobActionsController - state retrieval",
            "CompanyPublicController - profile retrieval",
            "CompanyPublicController - jobs listing",
            "CompanyPublicController - statistics"
        ],
        "Models": [
            "JobLike model validation and serialization",
            "JobShare model validation and serialization",
            "JobActionsState model validation",
            "SavedJob model validation",
            "ShareMethodEnum validation"
        ],
        "Database": [
            "JobLikeORM CRUD operations",
            "JobShareORM CRUD operations",
            "SavedJobORM CRUD operations",
            "Database constraints and relationships",
            "Foreign key validations"
        ],
        "Services": [
            "JobActionsAnalyticsService event tracking",
            "Engagement metrics calculation",
            "Company analytics reporting",
            "User engagement history",
            "Popular jobs identification"
        ]
    }

    for category, tests in test_categories.items():
        print(f"\n{category}:")
        for test in tests:
            print(f"  ✓ {test}")

    print(f"\n📊 Total Test Categories: {len(test_categories)}")
    print(f"📊 Total Test Areas: {sum(len(tests) for tests in test_categories.values())}")
    print("\n🎯 Coverage Target: 90% minimum")


def main():
    """Main test runner function"""

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'check':
            return check_test_files_exist()
        elif command == 'summary':
            generate_test_summary()
            return True
        elif command in ['controllers', 'models', 'database', 'services']:
            return run_specific_test_category(command)
        elif command == 'help':
            print("Job Actions Test Runner")
            print("\nUsage:")
            print("  python tests/run_job_actions_tests.py [command]")
            print("\nCommands:")
            print("  (no command)  - Run all tests with coverage")
            print("  check         - Check if all test files exist")
            print("  summary       - Show test summary")
            print("  controllers   - Run controller tests only")
            print("  models        - Run model tests only")
            print("  database      - Run database tests only")
            print("  services      - Run service tests only")
            print("  help          - Show this help message")
            return True
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'help' for available commands")
            return False
    else:
        # Run all tests with coverage
        if not check_test_files_exist():
            return False

        success = run_tests_with_coverage()

        if success:
            generate_test_summary()

        return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
