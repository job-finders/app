# Project Structure

## Root Directory
```
├── app.py                 # Main Flask application entry point
├── requirements.txt       # Python dependencies
├── .env.developer        # Environment configuration
├── pytest.ini           # Test configuration
└── README.md            # Project documentation
```

## Source Code Organization (`src/`)

### Core Application
- `src/main/` - Flask app factory and initialization
- `src/config/` - Pydantic-based configuration management
- `src/routes/` - Blueprint-based route definitions organized by feature
  - `company_routes/` - Company registration, profiles, and management
  - `employer_routes/` - Employer-specific functionality and verification
  - `billing_routes/` - Payment processing and subscription management
  - `jobs_routes/` - Job posting, search, and workflow management
  - `jobseeker_routes/` - Job seeker profiles and applications
  - `auth_routes/` - Authentication and authorization
  - `admin_routes/` - Administrative functions
- `src/controllers/` - Business logic controllers (MVC pattern)
  - `company/` - Company management and employer operations
  - `employers/` - Employer-specific business logic
  - `billing/` - Payment and subscription processing
  - `jobs/` - Job search, matching, and workflow controllers
  - `jobseekers/` - Job seeker profile and application management

### Data Layer
- `src/database/` - Database models, migrations, and SQL utilities
  - `models/` - SQLAlchemy ORM models
  - `sql/` - Raw SQL queries and database utilities
  - `migrations/` - Database schema changes

### Services & Utilities
- `src/services/` - External service integrations (email, payments, etc.)
- `src/scrappers/` - Job site scraping modules (Career24, PNet, Indeed, etc.)
- `src/cache/` - Redis and route caching implementations
- `src/utils/` - Shared utility functions and helpers

### AI & Automation
- `src/agents/` - AI agents for job matching and content generation
- `src/mcp/` - Model Context Protocol implementations
- `src/tasks/` - Background task definitions and scheduling

### Security
- `src/firewall/` - Security middleware (rate limiting, CSRF, headers)
- `src/authentication/` - JWT and session management

### Factories
- `src/factories/` - Dependency injection for controllers and services

## Company Ecosystem Structure

### Company Management Flow
```
Company Registration → Employer Onboarding → Job Posting → Candidate Management
```

### Key Company Components
- **Company Profiles**: Business information, verification status, and public profiles
- **Employer Management**: Individual employer accounts within companies
- **Billing System**: Subscription management and payment processing via PayFast
- **Verification Hub**: Document upload and CIPC registration verification
- **Analytics Dashboard**: Job posting performance and candidate engagement metrics
- **ATS Integration**: Applicant tracking system for managing applications

### Company-Related Database Models
- `CompanyORM` - Core company information and settings
- `EmployerORM` - Individual employer accounts linked to companies
- `CompanyBillingProfileORM` - Billing and subscription data
- `InvoiceORM` - Payment and invoice tracking
- `PaymentMethodORM` - Stored payment methods
- `BillingEventORM` - Billing event history and audit trail

## Frontend Assets (`static/` & `template/`)

### Static Files
```
static/
├── css/
│   ├── jobseekers/cv/    # Resume and profile styles
│   ├── jobs/             # Job listing styles
│   └── admin/            # Admin interface styles
├── js/
│   ├── jobs/             # Job-related JavaScript
│   └── lib/              # Third-party libraries
└── images/               # Static images and assets
```

### Templates
```
template/
├── layouts/              # Base templates and common layouts
├── jobs/                 # Job listing and detail templates
├── jobseekers/          # Job seeker profile templates
├── company/             # Company management and employer dashboards
│   ├── billing/         # Company billing and subscription templates
│   ├── candidates/      # Candidate management templates
│   ├── components/      # Reusable company UI components
│   ├── layout/          # Company-specific layout templates
│   └── public/          # Public company profile templates
├── employers/           # Employer verification and onboarding
└── admin/               # Admin interface templates
```

## Data & Cache
- `cache/` - Scraped job data cache files
- `backup_cache/` - Backup of cache files
- `media/` - User-uploaded files (CVs, company logos, documents)
  - `logos/` - Company logo uploads
- `logs/` - Application and security logs
- `static/uploads/` - Runtime file uploads organized by company

## Testing
- `tests/` - Pytest-based test suite organized by feature
- `ai-tasks/` - AI-related task definitions and tests

## Configuration Files
- `.kiro/` - Kiro IDE configuration and specs
- `.vscode/` - VS Code settings
- `.github/` - GitHub Actions workflows

## Naming Conventions

### Files & Directories
- **Snake_case** for Python files: `job_search.py`
- **Kebab-case** for CSS/JS files: `job-listing.css`
- **PascalCase** for classes: `JobSearchController`
- **Lowercase** for directories: `controllers/jobs/`

### Database
- **Singular** table names: `job`, `user`, `company`
- **Snake_case** for columns: `created_at`, `job_id`
- **ORM suffix** for SQLAlchemy models: `JobsORM`, `UserORM`

### Routes & Blueprints
- **Feature-based** organization: `jobs_routes/`, `company_routes/`, `auth_routes/`
- **RESTful** URL patterns: `/api/jobs/<job_id>`, `/company/<company_id>`
- **Blueprint naming**: `jobs_search_route`, `company_bp`, `employer_route`, `billing_route`
- **Hierarchical routing**: Company → Employer → Jobs relationship reflected in URLs