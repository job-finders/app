# JobFinders Route Documentation

## Overview

This document provides a comprehensive mapping of all routes in the JobFinders application, organized by blueprint and
functionality. The routes are discovered through manual analysis of the directory structure and route files.

## Route Organization

### Blueprint Structure

The application uses Flask blueprints to organize routes by functional domain:

```
src/routes/
├── home_routes/           # Public pages and general site functionality
├── auth_routes/           # Authentication and user management
├── jobs_routes/           # Job search and job workflow management
├── company_routes/        # Company profiles and employer functionality
├── jobseeker_routes/      # Job seeker profiles and applications
├── admin_routes/          # Administrative functionality
├── billing_routes/        # Payment and subscription management
├── blog_routes/           # Blog content management
├── seo_routes/           # SEO and sitemap functionality
├── ats_routes/           # Applicant Tracking System
├── agents_routes/        # AI agent functionality
└── employer_routes/      # Employer-specific features
```

## Route Categories

### 1. Home Routes (`home` blueprint)

**URL Prefix:** None (root level)
**File:** `src/routes/home_routes/home.py`

| Endpoint                 | URL                                     | Methods | Auth Required | Description                          |
|--------------------------|-----------------------------------------|---------|---------------|--------------------------------------|
| `home.get_home`          | `/`                                     | GET     | No            | Main homepage with job search        |
| `home.about`             | `/about`                                | GET     | No            | About page                           |
| `home.contact`           | `/contact`                              | GET     | No            | Contact information                  |
| `home.terms`             | `/terms`                                | GET     | No            | Terms and conditions                 |
| `home.privacy`           | `/privacy`                              | GET     | No            | Privacy policy                       |
| `home.documentation`     | `/documentation`                        | GET     | No            | API documentation                    |
| `home.sister_sites`      | `/sister-sites`                         | GET     | No            | Related websites                     |
| `home.faq`               | `/faq`                                  | GET     | No            | Frequently asked questions           |
| `home.linkedin_learning` | `/linkedin-learning`                    | GET     | No            | LinkedIn Learning integration        |
| `home.serve_logo`        | `/media/logos/<job_ref>.png`            | GET     | No            | Serve cached job logos               |
| `home.email_me`          | `/job-notifications/<search_term>`      | POST    | No            | Job notification subscription        |
| `home.verify_email`      | `/email-verification/<verification_id>` | GET     | No            | Email verification for notifications |

### 2. Authentication Routes (`auth` blueprint)

**URL Prefix:** `/auth`
**File:** `src/routes/auth_routes/auth.py`

| Endpoint              | URL                    | Methods   | Auth Required | Description       |
|-----------------------|------------------------|-----------|---------------|-------------------|
| `auth.login`          | `/auth/login`          | GET, POST | No            | User login        |
| `auth.logout`         | `/auth/logout`         | GET       | Yes           | User logout       |
| `auth.subscribe`      | `/auth/subscribe`      | GET, POST | No            | User registration |
| `auth.password_reset` | `/auth/password-reset` | GET, POST | No            | Password reset    |

### 3. Job Search Routes (`jobs` blueprint)

**URL Prefix:** `/jobs`
**File:** `src/routes/jobs_routes/job_search_routes.py`

| Endpoint                      | URL                                 | Methods | Auth Required | Description                     |
|-------------------------------|-------------------------------------|---------|---------------|---------------------------------|
| `jobs.list_jobs`              | `/jobs/browse-jobs`                 | GET     | No            | Browse all jobs with pagination |
| `jobs.search_jobs`            | `/jobs/search`                      | GET     | No            | Search jobs by keyword          |
| `jobs.job_categories`         | `/jobs/categories`                  | GET     | No            | List job categories             |
| `jobs.category_jobs`          | `/jobs/category/<category>`         | GET     | No            | Jobs filtered by category       |
| `jobs.job_details`            | `/jobs/<job_id>`                    | GET     | No            | Individual job details          |
| `jobs.full_job_details`       | `/jobs/full-job-detail/<job_id>`    | GET     | No            | Full job details view           |
| `jobs.jobs_by_location`       | `/jobs/location/<location>`         | GET     | No            | Jobs filtered by location       |
| `jobs.jobs_by_type`           | `/jobs/type/<job_type>`             | GET     | No            | Jobs filtered by type           |
| `jobs.featured_jobs`          | `/jobs/featured`                    | GET     | No            | Featured job listings           |
| `jobs.recent_jobs`            | `/jobs/recent`                      | GET     | No            | Recently posted jobs            |
| `jobs.jobs_by_salary_range`   | `/jobs/salary`                      | GET     | No            | Jobs filtered by salary         |
| `jobs.get_job_match_analysis` | `/jobs/job-match-analysis/<job_id>` | GET     | Yes           | Job match analysis API          |

### 4. Job Workflow Routes (`jobs_workflow` blueprint)

**URL Prefix:** `/dashboard/jobs`
**File:** `src/routes/jobs_routes/jobs_workflow_routes.py`

| Endpoint                              | URL                                                                     | Methods | Auth Required | Roles     | Description               |
|---------------------------------------|-------------------------------------------------------------------------|---------|---------------|-----------|---------------------------|
| `jobs_workflow.show_create_form`      | `/dashboard/jobs/create`                                                | GET     | Yes           | Employer  | Show job creation form    |
| `jobs_workflow.create_job`            | `/dashboard/jobs/create`                                                | POST    | Yes           | Employer  | Create new job posting    |
| `jobs_workflow.save_job_draft`        | `/dashboard/jobs/save-job-draft`                                        | POST    | Yes           | Employer  | Save job as draft         |
| `jobs_workflow.show_edit_form`        | `/dashboard/jobs/<job_id>/edit`                                         | GET     | Yes           | Employer  | Show job edit form        |
| `jobs_workflow.edit_job`              | `/dashboard/jobs/<job_id>/edit`                                         | POST    | Yes           | Employer  | Update job posting        |
| `jobs_workflow.calculate_ats`         | `/dashboard/jobs/<job_id>/calculate-ats`                                | POST    | Yes           | Employer  | Calculate ATS metrics     |
| `jobs_workflow.archive_job`           | `/dashboard/jobs/<job_id>/archive`                                      | GET     | Yes           | Employer  | Archive job posting       |
| `jobs_workflow.feature_job`           | `/dashboard/jobs/<job_id>/feature`                                      | GET     | Yes           | Employer  | Feature job posting       |
| `jobs_workflow.approve_job`           | `/dashboard/jobs/approve/<approval_token>`                              | GET     | Yes           | Admin     | Approve pending job       |
| `jobs_workflow.reject_job`            | `/dashboard/jobs/reject/<approval_token>`                               | GET     | Yes           | Admin     | Reject pending job        |
| `jobs_workflow.submit_application`    | `/dashboard/jobs/<job_id>/apply`                                        | POST    | Yes           | Jobseeker | Submit job application    |
| `jobs_workflow.job_insights`          | `/dashboard/jobs/<job_id>/insights`                                     | GET     | Yes           | Employer  | View job analytics        |
| `jobs_workflow.view_job_applications` | `/dashboard/jobs/<job_id>/view-applications`                            | GET     | Yes           | Employer  | View job applications     |
| `jobs_workflow.get_application`       | `/dashboard/jobs/<job_id>/application/<application_id>/get-application` | GET     | Yes           | Employer  | View specific application |
| `jobs_workflow.update_status`         | `/dashboard/jobs/<job_id>/update-status`                                | POST    | Yes           | Employer  | Update job status         |

### 5. Company Routes (`company` blueprint)

**URL Prefix:** `/dashboard/company`
**File:** `src/routes/company_routes/company_routes.py`

| Endpoint                                 | URL                                                                   | Methods   | Auth Required | Roles    | Description                    |
|------------------------------------------|-----------------------------------------------------------------------|-----------|---------------|----------|--------------------------------|
| `company.create_company_profile`         | `/dashboard/company/create-company`                                   | GET, POST | Yes           | -        | Create company profile         |
| `company.edit_company_profile`           | `/dashboard/company/profile/edit`                                     | GET       | Yes           | Employer | Edit company profile form      |
| `company.update_company_profile`         | `/dashboard/company/profile/update`                                   | POST      | Yes           | Employer | Update company profile         |
| `company.update_employer_profile`        | `/dashboard/company/update-employer`                                  | GET, POST | Yes           | Employer | Update employer profile        |
| `company.view_company`                   | `/dashboard/company/profile`                                          | GET       | Yes           | Employer | View company profile           |
| `company.view_employer_profile`          | `/dashboard/company/employer/profile`                                 | GET       | Yes           | Employer | View employer profile          |
| `company.manage_jobs`                    | `/dashboard/company/jobs`                                             | GET, POST | Yes           | Employer | Manage company jobs            |
| `company.candidate_management`           | `/dashboard/company/candidates`                                       | GET, POST | Yes           | Employer | Manage candidates              |
| `company.candidate_details`              | `/dashboard/company/candidate/<cv_id>`                                | GET       | Yes           | Employer | View candidate details         |
| `company.application_analytics`          | `/dashboard/company/analytics/applications`                           | GET       | Yes           | Employer | Application analytics          |
| `company.initiate_employer_verification` | `/dashboard/company/verify-employer-profile`                          | POST      | Yes           | Employer | Start employer verification    |
| `company.verify_employer_profile`        | `/dashboard/company/do-verify-employer-profile/<token>/<employer_id>` | GET       | No            | -        | Complete employer verification |
| `company.initiate_company_verification`  | `/dashboard/company/submit-company-verification`                      | GET, POST | Yes           | Employer | Company verification process   |

### 6. Job Actions Routes (`jobs_actions` blueprint)

**URL Prefix:** `/jobs/actions`
**File:** `src/routes/jobs_routes/actions.py`

| Endpoint                  | URL                    | Methods | Auth Required | Description               |
|---------------------------|------------------------|---------|---------------|---------------------------|
| `jobs_actions.save_job`   | `/jobs/actions/save`   | POST    | Yes           | Save job to favorites     |
| `jobs_actions.unsave_job` | `/jobs/actions/unsave` | POST    | Yes           | Remove job from favorites |
| `jobs_actions.share_job`  | `/jobs/actions/share`  | POST    | No            | Share job posting         |
| `jobs_actions.report_job` | `/jobs/actions/report` | POST    | Yes           | Report inappropriate job  |

### 7. Job Analytics Routes (`jobs_analytics` blueprint)

**URL Prefix:** `/jobs/analytics`
**File:** `src/routes/jobs_routes/analytics.py`

| Endpoint                            | URL                                    | Methods | Auth Required | Roles    | Description                 |
|-------------------------------------|----------------------------------------|---------|---------------|----------|-----------------------------|
| `jobs_analytics.job_performance`    | `/jobs/analytics/performance/<job_id>` | GET     | Yes           | Employer | Job performance metrics     |
| `jobs_analytics.application_funnel` | `/jobs/analytics/funnel/<job_id>`      | GET     | Yes           | Employer | Application funnel analysis |

## Route Patterns

### URL Parameter Patterns

The application uses several URL parameter patterns:

- `<job_id>` - Job identifier (UUID format)
- `<category>` - Job category slug
- `<location>` - Location name or slug
- `<job_type>` - Job type (full-time, part-time, contract, etc.)
- `<cv_id>` - CV/Resume identifier
- `<application_id>` - Job application identifier
- `<employer_id>` - Employer identifier
- `<company_id>` - Company identifier
- `<token>` - Verification or authentication token
- `<search_term>` - Search keyword or phrase
- `<verification_id>` - Email verification identifier

### Authentication Patterns

Routes are categorized by authentication requirements:

1. **Public Routes** (28 routes) - No authentication required
    - Home pages, job search, job details
    - Authentication pages (login, register)
    - Public company profiles

2. **Protected Routes** (32 routes) - Authentication required
    - User dashboards and profiles
    - Job applications and saved jobs
    - Company management features

3. **Role-Based Routes**
    - **Employer Only** (20 routes) - Company and job management
    - **Jobseeker Only** (1 route) - Job applications
    - **Admin Only** (2 routes) - Job approval/rejection

### URL Prefix Organization

Routes are organized with logical URL prefixes:

- **No prefix**: Public pages (`/`, `/about`, `/contact`)
- **`/auth`**: Authentication (`/auth/login`, `/auth/register`)
- **`/jobs`**: Public job browsing (`/jobs/search`, `/jobs/categories`)
- **`/dashboard/jobs`**: Job management (`/dashboard/jobs/create`)
- **`/dashboard/company`**: Company management
- **`/dashboard/jobseeker`**: Jobseeker features
- **`/admin`**: Administrative functions
- **`/api`**: API endpoints
- **`/seo`**: SEO-related routes

## Blueprint Dependencies

### Import Structure

Each blueprint is imported through its `__init__.py` file:

```python
# src/routes/home_routes/__init__.py
from src.routes.home_routes.home import home_route

# src/routes/jobs_routes/__init__.py  
from src.routes.jobs_routes.job_search_routes import jobs_search_route
from src.routes.jobs_routes.jobs_workflow_routes import jobs_workflow_route
from src.routes.jobs_routes.actions import jobs_actions_bp

# src/routes/company_routes/__init__.py
from src.routes.company_routes.company_routes import company_bp
from src.routes.company_routes.company_search_routes import company_search_routes
from src.routes.company_routes.public import company_public_bp
```

### Blueprint Registration

All blueprints are registered in `src/main/__init__.py`:

```python
def _register_blueprints(app):
    blueprints = [
        auth_route, home_route, jobs_workflow_route, jobs_search_route,
        jobs_actions_bp, jobs_analytics_bp, seo_route, blog_route,
        users_route, jobseeker_route, jobseeker_profiles_bp,
        resume_routes, jobseeker_applications_route, application_workflow_bp,
        cron_route, ats_tool_route, company_bp, company_search_routes,
        company_public_bp, billing_route, system_admin_route,
        employee_agents_route, employer_agents_route, employer_route
    ]
    for blueprint in blueprints:
        app.register_blueprint(blueprint)
```

## Route Analysis Summary

- **Total Routes**: ~85 routes across all blueprints
- **Public Routes**: 28 (accessible without authentication)
- **Protected Routes**: 57 (require authentication)
- **Parameterized Routes**: 25 (contain URL parameters)
- **Static Routes**: 60 (fixed URL patterns)

## Common Route Patterns

### Job-Related Routes

- Job browsing: `/jobs/*`
- Job management: `/dashboard/jobs/*`
- Job actions: `/jobs/actions/*`

### User Management Routes

- Authentication: `/auth/*`
- Company dashboard: `/dashboard/company/*`
- Jobseeker dashboard: `/dashboard/jobseeker/*`

### API Routes

- Job matching: `/jobs/job-match-analysis/*`
- Analytics: `/jobs/analytics/*`
- Actions: `/jobs/actions/*`

This documentation provides a comprehensive overview of the JobFinders routing structure, enabling developers to
understand the application's URL patterns and navigate the codebase effectively.