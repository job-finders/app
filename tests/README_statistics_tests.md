# Job Statistics Tests

This directory contains comprehensive unit tests for the job statistics feature implementation.

## Test Files Overview

### 1. `test_job_statistics_service.py`
Tests the main `JobStatisticsService` class including:
- **Service Methods**: All calculation methods (`get_job_statistics`, `get_application_statistics`, etc.)
- **Error Handling**: Timeout handling, fallback mechanisms, graceful degradation
- **Integration**: Full service workflow with mocked dependencies
- **Helper Methods**: Internal calculation and analysis methods

**Key Test Classes:**
- `TestJobStatisticsService` - Main service functionality
- `TestApplicationStatistics` - Application statistics calculation
- `TestCompetitivenessMetrics` - ATS-based competitiveness analysis
- `TestTrendAnalysis` - Application trend calculations
- `TestCompanyStatistics` - Company hiring statistics
- `TestCaching` - Cache integration tests
- `TestErrorHandling` - Error scenarios and fallbacks
- `TestHelperMethods` - Internal utility methods
- `TestIntegration` - End-to-end service tests

### 2. `test_job_statistics_models.py`
Tests the Pydantic models used for statistics data:
- **Model Validation**: Field validation, type checking, constraints
- **Computed Properties**: All computed fields and their logic
- **Serialization**: JSON serialization/deserialization
- **Edge Cases**: Boundary conditions and error scenarios

**Key Test Classes:**
- `TestApplicationStatistics` - Application statistics model
- `TestCompetitivenessMetrics` - Competitiveness metrics model
- `TestTrendAnalysis` - Trend analysis model and data points
- `TestCompanyStatistics` - Company statistics model
- `TestJobStatistics` - Main statistics container model

### 3. `test_job_statistics_caching.py`
Tests the Redis caching functionality:
- **Cache Operations**: Storage, retrieval, invalidation
- **TTL Management**: Time-to-live functionality and freshness checks
- **Performance**: Serialization/deserialization performance
- **Error Recovery**: Handling Redis failures and corrupted data
- **Integration**: Cache integration with service methods

**Key Test Classes:**
- `TestCacheStorage` - Cache storage operations
- `TestCacheRetrieval` - Cache retrieval operations
- `TestCacheInvalidation` - Cache invalidation
- `TestCacheTTL` - Time-to-live functionality
- `TestCacheIntegration` - Integration with main service
- `TestCachePerformance` - Performance characteristics
- `TestCacheErrorRecovery` - Error handling scenarios

### 4. `test_job_model_computed_properties.py`
Tests the new computed properties added to the Job model:
- **applications_per_day**: Daily application rate calculation
- **application_trend_direction**: Trend analysis (increasing/decreasing/stable)
- **application_velocity**: Velocity analysis (accelerating/decelerating/steady)
- **Integration**: How properties work together
- **Performance**: Efficiency with large datasets

**Key Test Classes:**
- `TestJobApplicationsPerDay` - Applications per day calculation
- `TestJobApplicationTrendDirection` - Trend direction analysis
- `TestJobApplicationVelocity` - Application velocity calculation
- `TestComputedPropertiesIntegration` - Integration testing
- `TestErrorHandling` - Error scenarios

### 5. `test_company_model_computed_properties.py`
Tests the computed properties added to the Company model:
- **jobs_posted_last_12_months**: Recent job posting count
- **avg_applications_per_job**: Average applications across jobs
- **application_response_rate**: Employer response rate percentage
- **Integration**: How properties work together
- **Performance**: Efficiency with large datasets

**Key Test Classes:**
- `TestCompanyJobsPostedLast12Months` - Recent job counting
- `TestCompanyAvgApplicationsPerJob` - Application averages
- `TestCompanyApplicationResponseRate` - Response rate calculation
- `TestCompanyComputedPropertiesIntegration` - Integration testing
- `TestCompanyComputedPropertiesErrorHandling` - Error scenarios

## Test Utilities

### `test_statistics_suite.py`
Comprehensive test runner that executes all statistics tests and provides coverage summary.

### `validate_statistics_tests.py`
Validation script that checks test file syntax, imports, and structure without executing tests.

## Running Tests

### Individual Test Files
```bash
# Run specific test file
python -m pytest tests/test_job_statistics_service.py -v

# Run with coverage
python -m pytest tests/test_job_statistics_service.py --cov=src.services.job_statistics_service -v
```

### Full Test Suite
```bash
# Run all statistics tests
python tests/test_statistics_suite.py

# Or using pytest
python -m pytest tests/test_job_statistics_*.py tests/test_*_model_computed_properties.py -v
```

### Validation Only
```bash
# Validate test structure without running
python tests/validate_statistics_tests.py
```

## Test Coverage

The tests cover the following requirements from the specification:

### Requirement 8.1 - Efficient Calculation
- ✅ Tests use of existing computed properties from Job, JobApplication, and Company models
- ✅ Tests performance with large datasets
- ✅ Tests helper method efficiency

### Requirement 8.2 - Caching Implementation
- ✅ Tests Redis caching with appropriate TTL values
- ✅ Tests cache invalidation strategies
- ✅ Tests cache key formats and data serialization
- ✅ Tests cache performance characteristics

### Requirement 8.5 - Error Handling
- ✅ Tests graceful handling of missing data
- ✅ Tests timeout scenarios and fallback mechanisms
- ✅ Tests Redis failures and recovery
- ✅ Tests invalid data scenarios

## Mock Objects

The tests use comprehensive mock objects to simulate:
- **MockJob**: Job instances with configurable applications and ATS reports
- **MockJobApplication**: Application instances with dates and response status
- **MockATSReport**: ATS analysis reports with scores and keywords
- **MockCompany**: Company instances with jobs and statistics
- **Redis Mocks**: Async Redis client operations

## Test Data Patterns

Tests use realistic data patterns including:
- **Time-based Data**: Applications spread over time periods
- **Trend Patterns**: Increasing, decreasing, and stable application trends
- **ATS Score Distributions**: Realistic score ranges and keyword patterns
- **Company Activity**: Various hiring activity levels and response rates

## Performance Testing

Performance tests ensure:
- **Calculation Speed**: Statistics calculations complete within reasonable time
- **Memory Usage**: Efficient handling of large datasets
- **Cache Performance**: Fast serialization/deserialization
- **Scalability**: Performance with 1000+ applications/jobs

## Error Scenarios Tested

- **Missing Data**: Jobs without applications, companies without jobs
- **Invalid Dates**: None values, future dates, malformed timestamps
- **Redis Failures**: Connection errors, corrupted cache data, timeouts
- **Calculation Errors**: Division by zero, invalid score ranges
- **Integration Failures**: Controller timeouts, service unavailability

## Assertions and Validations

Tests include comprehensive assertions for:
- **Data Types**: Correct return types for all methods
- **Value Ranges**: Scores within 0-100, percentages within 0-100
- **Consistency**: Multiple calls return same results
- **Relationships**: Computed values match expected calculations
- **Edge Cases**: Boundary conditions and special cases

## Future Enhancements

Areas for potential test expansion:
- **Load Testing**: High-concurrency scenarios
- **Integration Testing**: Full database integration
- **Performance Benchmarking**: Detailed performance metrics
- **Security Testing**: Input validation and sanitization
- **Monitoring**: Test execution metrics and reporting