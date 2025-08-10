# Job Actions Feature - Unit Tests Documentation

This document describes the comprehensive unit test suite for the Job Actions feature, covering all components with a
minimum 90% code coverage requirement.

## Test Structure

### Test Categories

1. **Controller Tests** (`tests/controllers/`)
    - `test_job_actions_controller.py` - JobActionsController functionality
    - `test_company_public_controller.py` - CompanyPublicController functionality

2. **Model Tests** (`tests/models/`)
    - `test_job_actions_models.py` - Pydantic model validation and serialization

3. **Database Tests** (`tests/database/`)
    - `test_job_actions_orm.py` - SQLAlchemy ORM operations and constraints

4. **Service Tests** (`tests/services/`)
    - `test_job_actions_analytics.py` - Analytics service functionality

## Test Coverage Requirements

### Minimum Coverage: 90%

Each component must achieve at least 90% code coverage:

- **JobActionsController**: All methods (like, save, share, state retrieval)
- **CompanyPublicController**: All public profile methods
- **Pydantic Models**: Validation, serialization, business logic
- **ORM Models**: CRUD operations, relationships, constraints
- **Analytics Service**: Event tracking, metrics calculation, reporting

## Running Tests

### Run All Tests with Coverage

```bash
python tests/run_job_actions_tests.py
```

### Run Specific Test Categories

```bash
# Controller tests only
python tests/run_job_actions_tests.py controllers

# Model tests only
python tests/run_job_actions_tests.py models

# Database tests only
python tests/run_job_actions_tests.py database

# Service tests only
python tests/run_job_actions_tests.py services
```

### Check Test Files

```bash
python tests/run_job_actions_tests.py check
```

### View Test Summary

```bash
python tests/run_job_actions_tests.py summary
```

## Test Details

### JobActionsController Tests

#### Like/Unlike Functionality

- ✅ Successful job like with analytics tracking
- ✅ Duplicate like prevention (409 error)
- ✅ User not found handling (404 error)
- ✅ Job not found handling (404 error)
- ✅ Successful job unlike with count update
- ✅ Unlike non-existent like (404 error)
- ✅ Database error handling (500 error)
- ✅ Invalid ID validation (400 error)

#### Save/Unsave Functionality

- ✅ Successful job save with analytics tracking
- ✅ Duplicate save prevention (409 error)
- ✅ User/job existence validation
- ✅ Successful job unsave
- ✅ Unsave non-existent save (404 error)
- ✅ Cache invalidation on save/unsave

#### Share Functionality

- ✅ Authenticated user sharing with referral code
- ✅ Anonymous sharing without referral code
- ✅ Invalid share method validation (400 error)
- ✅ Job existence validation
- ✅ Share count tracking
- ✅ Analytics event tracking

#### State Retrieval

- ✅ Complete job actions state retrieval
- ✅ User action status (liked/saved)
- ✅ Aggregate counts (likes/shares)
- ✅ Cache integration
- ✅ Error handling

### CompanyPublicController Tests

#### Public Profile

- ✅ Successful company profile retrieval
- ✅ Company not found handling (404)
- ✅ Invalid company ID validation
- ✅ Database error handling

#### Active Jobs Listing

- ✅ Successful active jobs retrieval
- ✅ Empty jobs list handling
- ✅ Limit parameter support
- ✅ Job filtering by status

#### Company Statistics

- ✅ Statistics calculation (jobs, applications)
- ✅ Zero values handling
- ✅ Database aggregation queries
- ✅ Error handling

### Pydantic Model Tests

#### JobLike Model

- ✅ Default value generation (ID, timestamp)
- ✅ Explicit value assignment
- ✅ Required field validation
- ✅ Empty string validation
- ✅ Model serialization (model_dump)
- ✅ Dictionary creation (from_dict)

#### JobShare Model

- ✅ Default value generation
- ✅ User and anonymous sharing
- ✅ Share method validation
- ✅ Referral code generation
- ✅ All valid share methods testing
- ✅ Model serialization

#### JobActionsState Model

- ✅ Default boolean/count values
- ✅ Explicit value assignment
- ✅ Required field validation
- ✅ Negative count handling
- ✅ State aggregation representation

#### SavedJob Model

- ✅ Default value generation
- ✅ Required field validation
- ✅ Model serialization
- ✅ Timestamp handling

#### ShareMethodEnum

- ✅ All enum values validation
- ✅ Invalid value rejection
- ✅ Integration with JobShare model

### Database ORM Tests

#### JobLikeORM

- ✅ Instance creation and attributes
- ✅ Table name and primary key
- ✅ Foreign key constraints
- ✅ Unique constraint (user_id, job_id)
- ✅ to_dict method functionality
- ✅ CRUD operations

#### JobShareORM

- ✅ Instance creation with all fields
- ✅ Anonymous sharing (nullable user_id)
- ✅ Column definitions and constraints
- ✅ Nullable field validation
- ✅ Relationship definitions

#### SavedJobORM

- ✅ Instance creation and validation
- ✅ Required field constraints
- ✅ Unique constraint validation
- ✅ Table structure

#### Relationships

- ✅ JobsORM relationships (likes, shares, saved_jobs)
- ✅ JobSeekerProfileORM relationships
- ✅ Back reference configuration
- ✅ Foreign key constraint validation

### Analytics Service Tests

#### Event Tracking

- ✅ Successful job action tracking
- ✅ Invalid parameter handling
- ✅ Event metadata storage
- ✅ Company ID resolution

#### Engagement Metrics

- ✅ Job engagement calculation
- ✅ Conversion rate calculations
- ✅ View count integration
- ✅ Zero values handling

#### Company Analytics

- ✅ Company engagement statistics
- ✅ Growth rate calculation
- ✅ Top performing jobs identification
- ✅ Time period filtering

#### Reporting

- ✅ Comprehensive analytics reports
- ✅ Trend data generation
- ✅ Popular jobs identification
- ✅ User engagement history

## Test Fixtures and Mocks

### Common Fixtures

- `mock_factory`: Mock controller factory
- `mock_session`: Mock database session
- `sample_company_orm`: Sample company data
- `sample_job_orm`: Sample job data

### Mock Strategies

- **Database Sessions**: Mock SQLAlchemy sessions and queries
- **External Services**: Mock analytics and cache services
- **Time/UUID**: Mock datetime and UUID generation for consistency
- **Error Conditions**: Mock database errors and exceptions

## Coverage Reports

### HTML Coverage Report

Generated at: `tests/coverage_html/index.html`

### Terminal Coverage Report

Shows line-by-line coverage with missing lines highlighted

### XML Coverage Report

Generated at: `tests/coverage.xml` for CI/CD integration

## Continuous Integration

### GitHub Actions Integration

```yaml
- name: Run Job Actions Tests
  run: |
    pip install pytest pytest-cov
    python tests/run_job_actions_tests.py
```

### Coverage Badges

Coverage badges can be generated from the XML report for README display.

## Test Data Management

### Test Database

- Uses SQLite in-memory database for speed
- Isolated test transactions
- Automatic cleanup after each test

### Mock Data

- Consistent test data across test files
- Realistic data patterns
- Edge case coverage

## Performance Considerations

### Test Execution Speed

- Parallel test execution support
- In-memory database for speed
- Efficient mock strategies
- Timeout protection (5 minutes max)

### Resource Management

- Proper session cleanup
- Mock object disposal
- Memory leak prevention

## Debugging Tests

### Verbose Output

```bash
python tests/run_job_actions_tests.py --verbose
```

### Debug Specific Test

```bash
pytest tests/controllers/test_job_actions_controller.py::TestLikeJobFunctionality::test_like_job_success -v -s
```

### Coverage Debug

```bash
pytest --cov=src/controllers/jobs/actions --cov-report=html --cov-report=term-missing
```

## Quality Metrics

### Code Coverage: ≥90%

- Line coverage
- Branch coverage
- Function coverage

### Test Quality

- Comprehensive edge case coverage
- Error condition testing
- Integration scenario testing
- Performance validation

### Maintainability

- Clear test naming conventions
- Comprehensive documentation
- Modular test structure
- Easy debugging capabilities

## Future Enhancements

### Planned Additions

- Performance benchmarking tests
- Load testing for analytics
- End-to-end integration tests
- API contract testing

### Test Automation

- Automated test generation
- Mutation testing
- Property-based testing
- Regression test automation