# JobFinders Route Hierarchy and Categorization

## Overview

This document categorizes all discovered routes by their functional purpose, authentication requirements, and user
roles. This categorization is essential for template validation as it helps identify which routes should be accessible
from which templates.

## Functional Categories

### 1. Public Content Routes

**Purpose**: Static content pages accessible to all users
**Authentication**: None required
**SEO Importance**: High

| Blueprint | Endpoint          | URL                  | Template           | Navigation |
|-----------|-------------------|----------------------|--------------------|------------|
| home      | get_home          | `/`                  | home.html          | Main nav   |
| home      | about             | `/about`             | about.html         | Footer nav |
| home      | contact           | `/contact`           | contact.html       | Footer nav |
| home      | terms             | `/terms`             | terms.html         | Footer nav |
| home      | privacy           | `/privacy`           | terms.html         | Footer nav |
| home      | faq               | `/faq`               | faq.html           | Footer nav |
| home      | documentation     | `/documentation`     | documentation.html | Footer nav |
| home      | sister_sites      | `/sister-sites`      | sisters.html       | Footer nav |
| home      | linkedin_learning | `/linkedin-learning` | linkedin.html      | Footer nav |

**Template Link Patterns**:

- Should use `url_for('home.get_home')` for homepage links
- Footer links should use `url_for('home.about')`, `url_for('home.contact')`, etc.
- No authentication checks needed in templates

### 2. Authentication Routes

**Purpose**: User login, registration, and account management
**Authentication**: Mixed (login/register are public, logout requires auth)
**Role-Based Redirects**: Yes

| Blueprint | Endpoint       | URL                    | Template                 | Auth Required |
|-----------|----------------|------------------------|--------------------------|---------------|
| auth      | login          | `/auth/login`          | auth/login.html          | No            |
| auth      | logout         | `/auth/logout`         | None (redirect)          | Yes           |
| auth      | subscribe      | `/auth/subscribe`      | auth/register.html       | No            |
| auth      | password_reset | `/auth/password-reset` | auth/password_reset.html | No            |

**Template Link Patterns**:

```jinja2
<!-- Login/Register links (when user not authenticated) -->
{% if not current_user.is_authenticated %}
    <a href="{{ url_for('auth.login') }}">Login</a>
    <a href="{{ url_for('auth.subscribe') }}">Register</a>
{% else %}
    <a href="{{ url_for('auth.logout') }}">Logout</a>
{% endif %}
```

**Post-Authentication Redirects**:

- Employer → `url_for('company.view_company')`
- Jobseeker → `url_for('jobseeker.dashboard')`
- Admin → `url_for('admin.dashboard')`

### 3. Job Browsing Routes (Public)

**Purpose**: Public job search and discovery
**Authentication**: None required
**SEO Importance**: Very High
**Pagination**: Required

| Blueprint | Endpoint             | URL Pattern                      | Template                        | Parameters      |
|-----------|----------------------|----------------------------------|---------------------------------|-----------------|
| jobs      | list_jobs            | `/jobs/browse-jobs`              | jobs/list.html                  | page, page_size |
| jobs      | search_jobs          | `/jobs/search`                   | jobs/search.html                | keyword, page   |
| jobs      | job_categories       | `/jobs/categories`               | jobs/job_categories_list.html   | None            |
| jobs      | category_jobs        | `/jobs/category/<category>`      | jobs/category.html              | category        |
| jobs      | job_details          | `/jobs/<job_id>`                 | jobs/job_detail/job_detail.html | job_id          |
| jobs      | full_job_details     | `/jobs/full-job-detail/<job_id>` | jobs/full_job_detail.html       | job_id          |
| jobs      | jobs_by_location     | `/jobs/location/<location>`      | jobs/location.html              | location        |
| jobs      | jobs_by_type         | `/jobs/type/<job_type>`          | jobs/type.html                  | job_type        |
| jobs      | featured_jobs        | `/jobs/featured`                 | jobs/featured.html              | page            |
| jobs      | recent_jobs          | `/jobs/recent`                   | jobs/recent.html                | page            |
| jobs      | jobs_by_salary_range | `/jobs/salary`                   | jobs/salary.html                | min, max, unit  |

**Template Link Patterns**:

```jinja2
<!-- Job browsing navigation -->
<a href="{{ url_for('jobs.list_jobs') }}">Browse Jobs</a>
<a href="{{ url_for('jobs.search_jobs') }}">Search Jobs</a>
<a href="{{ url_for('jobs.job_categories') }}">Categories</a>
<a href="{{ url_for('jobs.featured_jobs') }}">Featured Jobs</a>

<!-- Dynamic job links -->
<a href="{{ url_for('jobs.job_details', job_id=job.job_id) }}">{{ job.title }}</a>
<a href="{{ url_for('jobs.category_jobs', category=category.slug) }}">{{ category.name }}</a>
<a href="{{ url_for('jobs.jobs_by_location', location=location.slug) }}">Jobs in {{ location.name }}</a>
```

### 4. Job Management Routes (Employer Only)

**Purpose**: Employer job posting and management
**Authentication**: Required
**Roles**: Employer only
**Billing**: Required

| Blueprint     | Endpoint              | URL Pattern                                  | Template                                             | Purpose              |
|---------------|-----------------------|----------------------------------------------|------------------------------------------------------|----------------------|
| jobs_workflow | show_create_form      | `/dashboard/jobs/create`                     | jobs_workflow/create.html                            | Job creation form    |
| jobs_workflow | create_job            | `/dashboard/jobs/create`                     | None (POST)                                          | Process job creation |
| jobs_workflow | save_job_draft        | `/dashboard/jobs/save-job-draft`             | None (POST)                                          | Save draft           |
| jobs_workflow | show_edit_form        | `/dashboard/jobs/<job_id>/edit`              | jobs_workflow/job_editor/edit.html                   | Job edit form        |
| jobs_workflow | edit_job              | `/dashboard/jobs/<job_id>/edit`              | None (POST)                                          | Process job update   |
| jobs_workflow | job_insights          | `/dashboard/jobs/<job_id>/insights`          | jobs_workflow/job_metrics.html                       | Job analytics        |
| jobs_workflow | view_job_applications | `/dashboard/jobs/<job_id>/view-applications` | jobs_workflow/job_applications/job_applications.html | View applications    |
| jobs_workflow | archive_job           | `/dashboard/jobs/<job_id>/archive`           | None (redirect)                                      | Archive job          |
| jobs_workflow | feature_job           | `/dashboard/jobs/<job_id>/feature`           | None (redirect)                                      | Feature job          |

**Template Link Patterns**:

```jinja2
<!-- Employer job management -->
{% if current_user.role == 'employer' %}
    <a href="{{ url_for('jobs_workflow.show_create_form') }}">Post New Job</a>
    <a href="{{ url_for('company.manage_jobs') }}">Manage Jobs</a>
    
    <!-- Job-specific actions -->
    <a href="{{ url_for('jobs_workflow.show_edit_form', job_id=job.job_id) }}">Edit Job</a>
    <a href="{{ url_for('jobs_workflow.job_insights', job_id=job.job_id) }}">View Analytics</a>
    <a href="{{ url_for('jobs_workflow.view_job_applications', job_id=job.job_id) }}">View Applications</a>
{% endif %}
```

### 5. Company Management Routes (Employer Only)

**Purpose**: Company profile and employer management
**Authentication**: Required
**Roles**: Employer only

| Blueprint | Endpoint               | URL Pattern                                 | Template                           | Purpose              |
|-----------|------------------------|---------------------------------------------|------------------------------------|----------------------|
| company   | create_company_profile | `/dashboard/company/create-company`         | company/create_company.html        | Company creation     |
| company   | view_company           | `/dashboard/company/profile`                | company/view_company_profile.html  | Company dashboard    |
| company   | edit_company_profile   | `/dashboard/company/profile/edit`           | company/company_editor.html        | Edit company         |
| company   | view_employer_profile  | `/dashboard/company/employer/profile`       | company/view_employer_profile.html | Employer profile     |
| company   | manage_jobs            | `/dashboard/company/jobs`                   | company/jobs.html                  | Job management       |
| company   | candidate_management   | `/dashboard/company/candidates`             | company/candidates.html            | Candidate management |
| company   | application_analytics  | `/dashboard/company/analytics/applications` | company/analytics.html             | Hiring analytics     |

**Template Link Patterns**:

```jinja2
<!-- Company dashboard navigation -->
{% if current_user.role == 'employer' %}
    <a href="{{ url_for('company.view_company') }}">Company Profile</a>
    <a href="{{ url_for('company.view_employer_profile') }}">My Profile</a>
    <a href="{{ url_for('company.manage_jobs') }}">Manage Jobs</a>
    <a href="{{ url_for('company.candidate_management') }}">Candidates</a>
    <a href="{{ url_for('company.application_analytics') }}">Analytics</a>
{% endif %}
```

### 6. Job Actions (AJAX/API Routes)

**Purpose**: User interactions with jobs (save, share, report)
**Authentication**: Required
**Content-Type**: JSON
**Method**: POST

| Blueprint    | Endpoint   | URL                    | Purpose                  |
|--------------|------------|------------------------|--------------------------|
| jobs_actions | save_job   | `/jobs/actions/save`   | Save job to favorites    |
| jobs_actions | unsave_job | `/jobs/actions/unsave` | Remove from favorites    |
| jobs_actions | share_job  | `/jobs/actions/share`  | Share job posting        |
| jobs_actions | report_job | `/jobs/actions/report` | Report inappropriate job |

**Template Link Patterns**:

```jinja2
<!-- AJAX job actions -->
<button onclick="saveJob('{{ job.job_id }}')" data-url="{{ url_for('jobs_actions.save_job') }}">
    Save Job
</button>
<button onclick="shareJob('{{ job.job_id }}')" data-url="{{ url_for('jobs_actions.share_job') }}">
    Share Job
</button>
```

### 7. Static Asset Routes

**Purpose**: Serve static files and media
**Authentication**: None
**Caching**: Enabled

| Blueprint | Endpoint   | URL Pattern                  | Purpose         |
|-----------|------------|------------------------------|-----------------|
| home      | serve_logo | `/media/logos/<job_ref>.png` | Company logos   |
| static    | static     | `/static/<path:filename>`    | CSS, JS, images |

**Template Link Patterns**:

```jinja2
<!-- Static assets -->
<img src="{{ url_for('home.serve_logo', job_ref=job.job_ref) }}" alt="Company Logo">
<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
<script src="{{ url_for('static', filename='js/app.js') }}"></script>
```

## Authentication Patterns

### Public Routes (No Authentication Required)

- All `home.*` routes
- All `jobs.*` browsing routes
- `auth.login`, `auth.subscribe`, `auth.password_reset`
- Static asset routes

### Protected Routes (Authentication Required)

- All `jobs_workflow.*` routes
- All `company.*` routes
- All `jobs_actions.*` routes
- `auth.logout`

### Role-Based Routes

#### Employer Only

- `jobs_workflow.*` (job management)
- `company.*` (company management)

#### Jobseeker Only

- `jobs_workflow.submit_application`
- `jobseeker.*` routes

#### Admin Only

- `jobs_workflow.approve_job`
- `jobs_workflow.reject_job`
- `admin.*` routes

## Template Validation Implications

### 1. Navigation Menus

Templates should conditionally show navigation based on user authentication and role:

```jinja2
<!-- Main navigation -->
<nav>
    <a href="{{ url_for('home.get_home') }}">Home</a>
    <a href="{{ url_for('jobs.search_jobs') }}">Jobs</a>
    
    {% if current_user.is_authenticated %}
        {% if current_user.role == 'employer' %}
            <a href="{{ url_for('company.view_company') }}">Dashboard</a>
            <a href="{{ url_for('jobs_workflow.show_create_form') }}">Post Job</a>
        {% elif current_user.role == 'jobseeker' %}
            <a href="{{ url_for('jobseeker.dashboard') }}">Dashboard</a>
        {% endif %}
        <a href="{{ url_for('auth.logout') }}">Logout</a>
    {% else %}
        <a href="{{ url_for('auth.login') }}">Login</a>
        <a href="{{ url_for('auth.subscribe') }}">Register</a>
    {% endif %}
</nav>
```

### 2. Breadcrumb Navigation

Templates should use proper route hierarchy for breadcrumbs:

```jinja2
<!-- Job details breadcrumb -->
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li><a href="{{ url_for('home.get_home') }}">Home</a></li>
        <li><a href="{{ url_for('jobs.search_jobs') }}">Jobs</a></li>
        <li><a href="{{ url_for('jobs.category_jobs', category=job.category) }}">{{ job.category }}</a></li>
        <li class="active">{{ job.title }}</li>
    </ol>
</nav>
```

### 3. Form Actions

All forms should use proper `url_for` for action attributes:

```jinja2
<!-- Job search form -->
<form action="{{ url_for('jobs.search_jobs') }}" method="get">
    <input type="text" name="keyword" placeholder="Search jobs...">
    <button type="submit">Search</button>
</form>

<!-- Job application form -->
<form action="{{ url_for('jobs_workflow.submit_application', job_id=job.job_id) }}" method="post">
    <!-- form fields -->
    <button type="submit">Apply Now</button>
</form>
```

This categorization provides the foundation for the next phase of template analysis, where we'll identify hardcoded URLs
and convert them to proper `url_for` syntax.