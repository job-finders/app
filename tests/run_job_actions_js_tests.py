#!/usr/bin/env python3
"""
JavaScript Test Runner for Job Actions Feature

Runs comprehensive JavaScript tests for the job actions feature including:
- Unit tests for job actions functions
- Share modal functionality tests
- End-to-end user workflow tests
- Performance and accessibility validation
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_javascript_tests_with_coverage():
    """Run all JavaScript tests with coverage reporting"""

    print("🟨 Running Job Actions JavaScript Tests with Coverage...")
    print("=" * 65)

    # Check if Node.js and npm are available
    if not check_node_environment():
        return False

    # Install dependencies if needed
    if not install_dependencies():
        return False

    # Build Jest command
    cmd = [
        'npx', 'jest',
        '--config', 'tests/js/jest.config.js',
        '--coverage',
        '--verbose',
        '--detectOpenHandles',
        '--forceExit'
    ]

    try:
        # Run tests
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print("\n✅ All JavaScript tests passed with sufficient coverage!")
            print("📊 Coverage report generated in tests/js/coverage/")

            # Parse and display coverage summary
            display_coverage_summary()
        else:
            print(f"\n❌ JavaScript tests failed with return code {result.returncode}")
            return False

    except FileNotFoundError:
        print("❌ Jest not found. Please install Node.js and run:")
        print("npm install --save-dev jest @testing-library/jest-dom jsdom")
        return False

    return result.returncode == 0


def run_specific_js_test_category(category):
    """Run JavaScript tests for a specific category"""

    categories = {
        'unit': [
            'tests/js/test_job_actions.js'
        ],
        'modal': [
            'tests/js/test_share_modal.js'
        ],
        'e2e': [
            'tests/js/test_job_actions_e2e.js'
        ]
    }

    if category not in categories:
        print(f"❌ Unknown category: {category}")
        print(f"Available categories: {', '.join(categories.keys())}")
        return False

    test_files = categories[category]

    print(f"🟨 Running {category.title()} JavaScript Tests...")
    print("=" * 50)

    cmd = [
              'npx', 'jest',
              '--config', 'tests/js/jest.config.js',
              '--verbose'
          ] + test_files

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ Jest not found. Please install Node.js and Jest")
        return False


def run_performance_tests():
    """Run performance-focused JavaScript tests"""
    print("⚡ Running JavaScript Performance Tests...")
    print("=" * 45)

    cmd = [
        'npx', 'jest',
        '--config', 'tests/js/jest.config.js',
        '--testNamePattern', 'performance|Performance',
        '--verbose'
    ]

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ Jest not found. Please install Node.js and Jest")
        return False


def run_accessibility_tests():
    """Run accessibility-focused JavaScript tests"""
    print("♿ Running JavaScript Accessibility Tests...")
    print("=" * 45)

    cmd = [
        'npx', 'jest',
        '--config', 'tests/js/jest.config.js',
        '--testNamePattern', 'accessibility|Accessibility|a11y',
        '--verbose'
    ]

    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ Jest not found. Please install Node.js and Jest")
        return False


def check_node_environment():
    """Check if Node.js environment is properly set up"""
    print("🔍 Checking Node.js Environment...")
    print("=" * 35)

    # Check Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js: {result.stdout.strip()}")
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js")
        return False

    # Check npm
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm: {result.stdout.strip()}")
        else:
            print("❌ npm not found")
            return False
    except FileNotFoundError:
        print("❌ npm not found. Please install npm")
        return False

    return True


def install_dependencies():
    """Install JavaScript testing dependencies"""
    print("📦 Installing JavaScript Dependencies...")
    print("=" * 40)

    # Check if package.json exists
    package_json_path = project_root / 'package.json'
    if not package_json_path.exists():
        create_package_json()

    # Install dependencies
    dependencies = [
        'jest',
        '@testing-library/jest-dom',
        'jsdom',
        'babel-jest',
        '@babel/core',
        '@babel/preset-env',
        'jest-html-reporters',
        'jest-sonar-reporter',
        'identity-obj-proxy'
    ]

    cmd = ['npm', 'install', '--save-dev'] + dependencies

    try:
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ npm not found")
        return False


def create_package_json():
    """Create package.json if it doesn't exist"""
    package_json = {
        "name": "jobfinders-js-tests",
        "version": "1.0.0",
        "description": "JavaScript tests for Job Finders job actions feature",
        "scripts": {
            "test": "jest --config tests/js/jest.config.js",
            "test:coverage": "jest --config tests/js/jest.config.js --coverage",
            "test:watch": "jest --config tests/js/jest.config.js --watch"
        },
        "devDependencies": {},
        "babel": {
            "presets": ["@babel/preset-env"]
        }
    }

    package_json_path = project_root / 'package.json'
    with open(package_json_path, 'w') as f:
        json.dump(package_json, f, indent=2)

    print("✅ Created package.json")


def display_coverage_summary():
    """Display coverage summary from Jest output"""
    coverage_summary_path = project_root / 'tests/js/coverage/coverage-summary.json'

    if coverage_summary_path.exists():
        try:
            with open(coverage_summary_path, 'r') as f:
                coverage_data = json.load(f)

            print("\n📊 Coverage Summary:")
            print("=" * 25)

            total = coverage_data.get('total', {})

            for metric in ['lines', 'functions', 'branches', 'statements']:
                if metric in total:
                    pct = total[metric].get('pct', 0)
                    covered = total[metric].get('covered', 0)
                    total_count = total[metric].get('total', 0)

                    status = "✅" if pct >= 85 else "⚠️" if pct >= 70 else "❌"
                    print(f"{status} {metric.title()}: {pct}% ({covered}/{total_count})")

        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"⚠️ Could not read coverage summary: {e}")


def check_js_test_files_exist():
    """Check that all JavaScript test files exist"""
    test_files = [
        'tests/js/test_job_actions.js',
        'tests/js/test_share_modal.js',
        'tests/js/test_job_actions_e2e.js',
        'tests/js/jest.config.js',
        'tests/js/setup.js'
    ]

    missing_files = []
    for test_file in test_files:
        if not (project_root / test_file).exists():
            missing_files.append(test_file)

    if missing_files:
        print("❌ Missing JavaScript test files:")
        for file in missing_files:
            print(f"  - {file}")
        return False

    print("✅ All JavaScript test files found")
    return True


def generate_js_test_summary():
    """Generate a summary of JavaScript test coverage"""

    print("\n📋 Job Actions JavaScript Test Summary")
    print("=" * 50)

    test_categories = {
        "Unit Tests": [
            "toggleLike function with success/error handling",
            "toggleSave function with authentication",
            "shareJob function with multiple platforms",
            "copyJobUrl with clipboard API fallback",
            "updateJobActionsState UI management",
            "Error handling and network failures",
            "UI state management and loading states",
            "Accessibility and keyboard navigation",
            "Performance optimization and debouncing"
        ],
        "Share Modal Tests": [
            "Modal open/close behavior",
            "Social media sharing (LinkedIn, Twitter, Facebook)",
            "Email sharing with pre-populated content",
            "WhatsApp sharing functionality",
            "Copy to clipboard with fallback",
            "Native Web Share API integration",
            "URL generation for different platforms",
            "Modal accessibility and focus management",
            "Responsive design and mobile optimization"
        ],
        "End-to-End Tests": [
            "Complete user engagement workflow",
            "Anonymous vs authenticated user flows",
            "Company profile to job actions flow",
            "Share to application conversion tracking",
            "Error recovery and retry mechanisms",
            "Performance benchmarks and optimization",
            "Accessibility standards compliance",
            "Mobile interaction handling",
            "Analytics and user journey tracking"
        ]
    }

    for category, tests in test_categories.items():
        print(f"\n{category}:")
        for test in tests:
            print(f"  ✓ {test}")

    print(f"\n📊 Total Test Categories: {len(test_categories)}")
    print(f"📊 Total Test Areas: {sum(len(tests) for tests in test_categories.values())}")
    print("\n🎯 Coverage Target: 85% minimum for JavaScript code")


def lint_javascript_code():
    """Run JavaScript linting"""
    print("🔍 Running JavaScript Linting...")
    print("=" * 35)

    # Check if ESLint is available
    try:
        cmd = ['npx', 'eslint', 'static/js/**/*.js', '--ext', '.js']
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ JavaScript code passes linting")
            return True
        else:
            print("⚠️ JavaScript linting issues found:")
            print(result.stdout)
            return False

    except FileNotFoundError:
        print("⚠️ ESLint not found. Skipping linting.")
        return True


def main():
    """Main JavaScript test runner function"""

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'check':
            return check_js_test_files_exist()
        elif command == 'summary':
            generate_js_test_summary()
            return True
        elif command == 'env':
            return check_node_environment()
        elif command == 'install':
            return install_dependencies()
        elif command in ['unit', 'modal', 'e2e']:
            return run_specific_js_test_category(command)
        elif command == 'performance':
            return run_performance_tests()
        elif command == 'accessibility':
            return run_accessibility_tests()
        elif command == 'lint':
            return lint_javascript_code()
        elif command == 'help':
            print("Job Actions JavaScript Test Runner")
            print("\nUsage:")
            print("  python tests/run_job_actions_js_tests.py [command]")
            print("\nCommands:")
            print("  (no command)  - Run all JavaScript tests with coverage")
            print("  check         - Check if all test files exist")
            print("  summary       - Show JavaScript test summary")
            print("  env           - Check Node.js environment")
            print("  install       - Install JavaScript dependencies")
            print("  unit          - Run unit tests only")
            print("  modal         - Run share modal tests only")
            print("  e2e           - Run end-to-end tests only")
            print("  performance   - Run performance tests only")
            print("  accessibility - Run accessibility tests only")
            print("  lint          - Run JavaScript linting")
            print("  help          - Show this help message")
            return True
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'help' for available commands")
            return False
    else:
        # Run all JavaScript tests with coverage
        if not check_js_test_files_exist():
            return False

        if not check_node_environment():
            return False

        success = run_javascript_tests_with_coverage()

        if success:
            generate_js_test_summary()

        return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
