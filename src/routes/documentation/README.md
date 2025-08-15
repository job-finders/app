# Job Finders Platform Route Documentation

## Overview

This directory contains comprehensive documentation for all routes in the Job Finders platform. The documentation is
organized by feature area and provides detailed information about each route's functionality, usage patterns, expected
responses, templates, and integration points within the job seeker and company workflows.

## Documentation Structure

The documentation is organized to mirror the route structure:

- **admin/** - Administrative interface routes
- **agents/** - AI agent endpoints
- **ats/** - ATS (Applicant Tracking System) routes
- **auth/** - Authentication and authorization routes
- **billing/** - Payment and subscription management routes
- **blog/** - Blog content management routes
- **company/** - Company registration and profile routes
- **cron/** - Scheduled task endpoints
- **employer/** - Employer-specific functionality routes
- **home/** - Home page routes
- **jobs/** - Job posting and search routes
- **jobseeker/** - Job seeker profiles and application routes
- **payment_gateways/** - Payment processor integration routes
- **resumes/** - CV management routes
- **seo/** - SEO and sitemap generation routes
- **users/** - User account management routes

## Documentation Format

Each route documentation file follows a standardized template with the following sections:

- **Overview** - Brief description of the route category
- **Routes** - Detailed documentation for each route including:
    - Metadata (blueprint, function, authentication, user types)
    - Description and purpose
    - Workflow integration points
    - Parameters (URL, query, request body)
    - Response formats and examples
    - Template context (for HTML responses)
    - Controller integration details
    - Security considerations
    - Usage examples
    - Related routes

## Navigation

### By User Type

**Job Seekers:**

- [Authentication](auth/auth.md) - Registration, login, profile
- [Job Search](jobs/job_search_routes.md) - Finding and filtering jobs
- [Job Applications](jobseeker/job_applications.md) - Applying and tracking
- [Profile Management](jobseeker/jobseeker_profile.md) - CV and profile
- [Resume Management](resumes/resumes.md) - CV upload and optimization

**Employers/Companies:**

- [Company Registration](company/company_routes.md) - Business setup
- [Employer Verification](employer/employer_routes.md) - Account verification
- [Job Posting](jobs/jobs_workflow_routes.md) - Creating and managing jobs
- [Candidate Management](company/company_search_routes.md) - Finding candidates
- [Billing](billing/billing_routes.md) - Subscriptions and payments

**Administrators:**

- [System Administration](admin/system_admin_route.md) - Platform management
- [Monitoring](admin/monitors.md) - System health and metrics
- [Content Moderation](admin/job_actions_monitoring.md) - Job and user oversight

### By Workflow

**Job Seeker Journey:**

1. Registration → [auth/auth.md](auth/auth.md)
2. Profile Setup → [jobseeker/jobseeker_profile.md](jobseeker/jobseeker_profile.md)
3. Job Search → [jobs/job_search_routes.md](jobs/job_search_routes.md)
4. Job Application → [jobseeker/job_applications.md](jobseeker/job_applications.md)
5. Application Tracking → [jobseeker/jobseeker_applications.md](jobseeker/jobseeker_applications.md)

**Company Onboarding:**

1. Company Registration → [company/company_routes.md](company/company_routes.md)
2. Employer Verification → [employer/employer_routes.md](employer/employer_routes.md)
3. Billing Setup → [billing/billing_routes.md](billing/billing_routes.md)
4. Job Posting → [jobs/jobs_workflow_routes.md](jobs/jobs_workflow_routes.md)
5. Candidate Management → [company/company_search_routes.md](company/company_search_routes.md)

## AI and Automation

The platform includes AI-powered features documented in:

- [AI Agents](agents/) - Blog generation, job optimization, candidate matching
- [ATS Integration](ats/ats_tool.md) - Applicant tracking and scoring

## Integration Points

### External Services

- **PayFast** - [payment_gateways/payfast.md](payment_gateways/payfast.md)
- **Hashnode** - [blog/blog.md](blog/blog.md)
- **Job Scrapers** - [cron/cron.md](cron/cron.md)

### Internal Systems

- **Caching** - Redis integration across routes
- **Security** - Authentication and rate limiting
- **Analytics** - Job actions and user engagement tracking

## Development Guidelines

When adding new routes:

1. Follow the standardized documentation template
2. Include workflow integration points
3. Document authentication and authorization requirements
4. Provide comprehensive examples
5. Update cross-references and related routes

## Maintenance

This documentation is maintained alongside route development. When routes change:

1. Update the corresponding documentation file
2. Validate examples and code samples
3. Update cross-references if needed
4. Review workflow integration points

For questions or contributions, refer to the main project documentation.