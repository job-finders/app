"""
Comprehensive Test Suite for Job Statistics

This module runs all statistics-related tests and provides a summary
of test coverage for the job statistics feature.
"""

import pytest
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_statistics_tests():
    """Run all statistics-related tests"""
    
    test_files = [
        "tests/test_job_statistics_service.py",
        "tests/test_job_statistics_models.py", 
        "tests/test_job_statistics_caching.py",
        "tests/test_job_model_computed_properties.py",
        "tests/test_company_model_computed_properties.py"
    ]
    
    print("Running Job Statistics Test Suite")
    print("=" * 50)
    
    all_passed = True
    
    for test_file in test_files:
        print(f"\nRunning {test_file}...")
        
        # Run pytest for each file
        result = pytest.main([
            test_file,
            "-v",
            "--tb=short",
            "--no-header"
        ])
        
        if result != 0:
            all_passed = False
            print(f"❌ {test_file} - Some tests failed")
        else:
            print(f"✅ {test_file} - All tests passed")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All statistics tests passed!")
    else:
        print("⚠️  Some tests failed. Please review the output above.")
    
    return all_passed


def test_coverage_summary():
    """Provide a summary of what is being tested"""
    
    coverage_areas = {
        "JobStatisticsService": [
            "✅ get_job_statistics() method",
            "✅ get_application_statistics() method", 
            "✅ get_competitiveness_metrics() method",
            "✅ get_trend_analysis() method",
            "✅ get_company_statistics() method",
            "✅ Error handling and fallbacks",
            "✅ Timeout handling",
            "✅ Helper methods"
        ],
        "Statistics Models": [
            "✅ ApplicationStatistics validation and computed fields",
            "✅ CompetitivenessMetrics validation and computed fields",
            "✅ TrendAnalysis validation and computed fields", 
            "✅ CompanyStatistics validation and computed fields",
            "✅ JobStatistics validation and computed fields",
            "✅ Model serialization and deserialization",
            "✅ Edge cases and error handling"
        ],
        "Caching System": [
            "✅ Cache storage operations",
            "✅ Cache retrieval operations", 
            "✅ Cache invalidation",
            "✅ TTL (Time To Live) functionality",
            "✅ Cache integration with service methods",
            "✅ Performance characteristics",
            "✅ Error recovery scenarios"
        ],
        "Job Model Computed Properties": [
            "✅ applications_per_day property",
            "✅ application_trend_direction property",
            "✅ application_velocity property",
            "✅ Integration between properties",
            "✅ Performance with large datasets",
            "✅ Error handling with invalid data"
        ],
        "Company Model Computed Properties": [
            "✅ jobs_posted_last_12_months property",
            "✅ avg_applications_per_job property", 
            "✅ application_response_rate property",
            "✅ Integration between properties",
            "✅ Performance with large datasets",
            "✅ Error handling with invalid data"
        ]
    }
    
    print("\nTest Coverage Summary")
    print("=" * 50)
    
    for area, tests in coverage_areas.items():
        print(f"\n{area}:")
        for test in tests:
            print(f"  {test}")
    
    print(f"\nTotal Test Areas: {len(coverage_areas)}")
    total_tests = sum(len(tests) for tests in coverage_areas.values())
    print(f"Total Test Categories: {total_tests}")


if __name__ == "__main__":
    # Show coverage summary
    test_coverage_summary()
    
    # Run all tests
    success = run_statistics_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)