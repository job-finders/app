# Project TODO List: JobFinders.site

This file tracks the remaining tasks to complete the JobFinders.site platform.

## Phase 1: Backend and Core Logic Integration

- [ ] **Database & Migrations**
    - [ ] Finalize all SQLAlchemy and Pydantic models.
    - [ ] Replace `boot.py` with a database migration tool (e.g., Alembic) to manage schema changes.

- [ ] **User Workflows**
    - [ ] **Job Seeker:** Wire up the UI for profile creation, CV management, job searching, and the full application process.
    - [ ] **Employer:** Connect the UI for company profile creation, job posting (including AI enhancement), candidate management, and document verification.

- [ ] **Billing Integration**
    - [ ] Perform end-to-end testing of the PayFast subscription workflow.
    - [ ] Verify cron jobs for managing subscription states (expirations, renewals).

- [ ] **Agent and Task Integration**
    - [ ] Verify all AI agents are correctly called from their respective controllers.
    - [ ] Confirm background tasks (Celery/APScheduler) are properly scheduled and executing.
    - [ ] Consolidate `Celery` and `APScheduler` into a single task scheduling system.

## Phase 2: Frontend Development

- [ ] **Build UI Pages**
    - [ ] Develop HTML templates for all user-facing features.
    - [ ] Create forms for user registration, profile management, job posting, and application submission.
        - [x] Populate CIPC registration form with existing company data.

- [ ] **Create Dashboards**
    - [ ] **Job Seeker Dashboard:** Display applied jobs, saved jobs, and profile completion status.
    - [ ] **Employer Dashboard:** Show posted jobs, application analytics, and candidate management tools.
    - [ ] **Admin Dashboard:** Provide an overview of system health, user activity, and moderation queues.

- [ ] **Dynamic Content**
    - [ ] Implement JavaScript (Fetch API/HTMX) for real-time features like ATS checks and AI-generated content.

## Phase 3: Finalization and Deployment

- [ ] **Configuration & Security**
    - [ ] Move all secrets to a secure production environment.
    - [ ] Create a production-specific configuration file.

- [ ] **Testing**
    - [ ] Write unit and integration tests for critical business logic.
    - [ ] Perform end-to-end testing of core user journeys.

- [ ] **Deployment**
    - [ ] Set up a production server environment (e.g., Gunicorn/Nginx).
    - [ ] Deploy the application to a cloud provider or dedicated server.
    - [ ] Configure and run background task workers in the production environment.
