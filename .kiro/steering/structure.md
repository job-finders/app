# Job Finders Platform Architecture Guide

## Overview

Job Finders is a comprehensive South African employment platform built with Flask, following a sophisticated MVC
architecture with dependency injection, service-oriented design, and AI-powered features. This guide provides detailed
architectural patterns and conventions for building and extending the platform.

## Root Directory Structure
```
├── app.py                 # Main Flask application entry point
├── requirements.txt       # Python dependencies
├── .env.developer        # Environment configuration
├── pytest.ini           # Test configuration
└── README.md            # Project documentation
```

## Core Architecture Principles

### 1. Data Flow Architecture

```
External Data → Pydantic Models → Business Logic → ORM Models → Database
Database → ORM Models → Pydantic Models → Business Logic → API Response
```

**Critical Rule**: All external data MUST pass through Pydantic models for validation before reaching ORM models. All
database reads MUST go through Pydantic models before business logic processing.

### 2. Controller Factory Pattern

Controllers are never imported directly into routes. All controller access follows the factory pattern:

```python
# ❌ WRONG - Direct import
from src.controllers.jobs import JobsSearchController

# ✅ CORRECT - Factory pattern
from src.utils.route_helpers import get_controller
jobs_controller = get_controller('jobs_search')
```

### 3. Service Interface Pattern

All services implement a standardized interface with an `execute()` method:

```python
class ServiceInterface:
    async def execute(self, action: str, *args, **kwargs):
        method_to_execute = self.__interface_map[action]
        if inspect.iscoroutinefunction(method_to_execute):
            return await method_to_execute(*args, **kwargs)
        else:
            return method_to_execute(*args, **kwargs)
```

## Source Code Organization (`src/`)

### Core Application Layer

#### `src/main/` - Application Bootstrap

- `boot.py` - Database initialization and app factory
- `error_handling.py` - Global error handlers and middleware
- `static/uploads/` - Runtime file upload storage

#### `src/config/` - Configuration Management

- Pydantic-based configuration with environment variable validation
- Type-safe configuration access throughout the application

#### `src/routes/` - Blueprint-Based Routing

Routes are organized by feature domain and follow RESTful conventions:

```
src/routes/
├── admin_routes/           # Administrative interface routes
│   ├── companies_route.py  # Company management for admins
│   ├── job_actions_monitoring.py  # Job action analytics
│   ├── match_scoring_admin.py     # ATS scoring administration
│   ├── monitors.py         # System monitoring endpoints
│   └── system_admin_route.py     # Core admin functionality
├── agents_routes/          # AI agent endpoints
│   ├── blog_agents_routes.py      # Blog content generation
│   ├── employee_agents_routes.py  # Job seeker AI tools
│   └── employer_agents_router.py  # Employer AI tools
├── ats_routes/            # ATS (Applicant Tracking System)
├── auth_routes/           # Authentication and authorization
├── billing_routes/        # Payment and subscription management
├── blog_routes/           # Blog content management
├── company_routes/        # Company registration and profiles
│   ├── company_routes.py   # Core company operations
│   ├── company_search_routes.py  # Company discovery
│   └── public.py          # Public company profiles
├── cron_routes/           # Scheduled task endpoints
├── employer_routes/       # Employer-specific functionality
├── jobs_routes/           # Job posting and search
│   ├── actions.py         # Job actions (save, share, apply)
│   ├── analytics.py       # Job performance metrics
│   ├── job_search_routes.py      # Job discovery and filtering
│   └── jobs_workflow_routes.py   # Job lifecycle management
├── jobseeker_routes/      # Job seeker profiles and applications
├── payment_gateways/      # Payment processor integrations
├── resumes_routes/        # CV management
├── seo_routes/           # SEO and sitemap generation
└── users_routes/         # User account management
```

**Route Naming Conventions:**

- Blueprint names: `{feature}_bp` (e.g., `jobs_bp`, `company_bp`)
- Route functions: `{action}_{resource}` (e.g., `get_job`, `create_company`)
- URL patterns: RESTful with hierarchical relationships

### Controller Layer (`src/controllers/`)

Controllers implement business logic and coordinate between routes, services, and data models. All controllers inherit
from the base `Controllers` class and follow the factory pattern.

#### Base Controller Architecture

```python
class Controllers:
    def __init__(self, factory, session_maker=Session):
        self.factory = factory           # Access to other controllers
        self.session_maker = session_maker
        self.sessions = []              # Session pool for performance
        self.logger = init_logger(self.__class__.__name__)
        self.app: Flask | None = None
        
    def init_app(self, app: Flask):
        """Initialize with Flask application"""
        self.app = app
        
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        # Session pooling and cleanup logic
        
    def close(self):
        """Resource cleanup"""
```

#### Controller Organization

```
src/controllers/
├── controller.py           # Base controller class and error handling
├── encryptor.py           # Encryption utilities for controllers
├── job_applications.py    # Legacy job application controller
├── admin/                 # Administrative controllers
│   ├── admin_controller.py        # Main admin operations
│   ├── interfaces.py              # Admin service interfaces
│   ├── user_security_engines.py  # Security risk analysis
│   ├── security_rules/            # Security rule definitions
│   └── services/                  # Admin service implementations
│       ├── analytics_service.py   # System analytics
│       ├── compliance_service.py  # Regulatory compliance
│       ├── job_moderation.py      # Content moderation
│       ├── job_recommendations.py # Job recommendation engine
│       └── security_service.py    # Security monitoring
├── agents/                # AI agent controllers
│   ├── ats_keywords_mining_tools.py     # ATS keyword extraction
│   ├── candidate_benchmark_controller.py # Candidate scoring
│   ├── employee_agents_controller.py     # Job seeker AI tools
│   ├── employer_agent_controller.py      # Employer AI tools
│   └── employer_ats_optimization_controller.py # ATS optimization
├── analytics/             # User engagement and analytics
│   └── user_engagements.py       # Engagement tracking
├── ats/                   # Applicant Tracking System
│   └── ats_controller.py          # ATS analysis and scoring
├── ats_ai/               # AI-powered ATS features
│   ├── enrich.py          # Resume enrichment
│   ├── extract.py         # Information extraction
│   ├── keyword_intelligence.py   # Keyword analysis
│   └── corpora/           # Training data and models
├── billing/              # Payment and subscription management
│   └── billing_controller.py     # Billing operations
├── blog/                 # Blog content management
│   ├── blog_agent_controller.py      # AI blog generation
│   ├── blog_feedback_controller.py   # Analytics integration
│   ├── blog_prompt_mutations.py      # Prompt optimization
│   ├── blog_search_controller.py     # Public blog API
│   ├── blog_workflow_controller.py   # Admin blog management
│   └── utils.py                       # Blog utilities
├── company/              # Company management
│   ├── company_controller.py      # Core company operations
│   └── public.py                  # Public company profiles
├── employers/            # Employer-specific operations
├── jobs/                 # Job management controllers
│   ├── actions.py         # Job actions (save, share, apply)
│   ├── auto_categorizer.py        # Automatic job categorization
│   ├── industrial_taxonomy.py     # Industry classification
│   ├── search.py          # Job search and filtering
│   └── workflow.py        # Job lifecycle management
├── jobseekers/           # Job seeker management
│   └── profile_controller.py      # Profile management
├── notifications/        # Notification system
│   └── notifications_controller.py # Centralized notifications
├── resumes/              # CV management
│   └── resume_controller.py       # Resume operations
├── seo/                  # SEO optimization
│   └── ping_controller.py         # Search engine pings
└── users/                # User account management
    └── users.py           # User operations
```

#### Controller Factory Registration

Every new controller must be registered in `src/factories/controller_factory.py`:

```python
class ControllerFactory:
    def get_new_controller(self) -> NewController:
        """Get NewController instance"""
        self.logger.info(f"Getting NewController")
        return self._get_controller('new_controller', NewController)
```

#### Controller Error Handling

All controller methods should use the `@error_handler` decorator:

```python
@error_handler
async def controller_method(self, param: str) -> SomeResult:
    """Controller method with error handling"""
    try:
        # Business logic here
        return result
    except SpecificException as e:
        # Handle specific exceptions
        raise
```

### Data Layer (`src/database/`)

The data layer follows a dual-model approach with strict separation between validation and persistence.

#### Database Architecture

```
src/database/
├── __init__.py            # Database initialization
├── constants/             # Database constants and enums
├── migrations/            # Schema changes and data migrations
│   ├── add_job_actions_tables.py     # Job action tracking
│   ├── add_match_scoring_indexes.sql # Performance optimization
│   ├── add_referral_tracking_tables.py # Referral system
│   ├── job_actions_integrity_check.py # Data integrity
│   ├── optimize_job_actions_indexes.sql # Index optimization
│   └── tables.SQL                     # Base schema
├── models/                # Pydantic validation models
│   ├── admin_models.py    # Administrative data models
│   ├── agent_models.py    # AI agent data models
│   ├── billing.py         # Billing and subscription models
│   ├── company_ats.py     # Company ATS integration models
│   ├── company_models.py  # Company and employer models
│   ├── config.py          # Configuration models
│   ├── employer_models.py # Employer-specific models
│   ├── feedback_analysis.py # Feedback and analytics models
│   ├── job_statistics.py  # Job performance metrics
│   ├── jobs_model.py      # Job posting models
│   ├── jobseeker_profile.py # Job seeker models
│   ├── notifications.py   # Notification models
│   ├── referral_tracking.py # Referral system models
│   ├── resume.py          # Resume and CV models
│   ├── seo.py            # SEO optimization models
│   ├── users.py          # User account models
│   ├── agents/           # AI agent specific models
│   └── payfast/          # Payment gateway models
└── sql/                  # SQLAlchemy ORM models
    ├── admin_sql.py       # Administrative ORM models
    ├── agent_session.py   # AI agent session tracking
    ├── analytics.py       # Analytics ORM models
    ├── billing_sql.py     # Billing ORM models
    ├── blog_learning.py   # Blog analytics ORM
    ├── company.py         # Company ORM models
    ├── config.py          # Configuration ORM
    ├── employer.py        # Employer ORM models
    ├── jobs_sql.py        # Job ORM models
    ├── jobseeker_profile.py # Job seeker ORM models
    ├── notifications.py   # Notification ORM models
    ├── resume.py          # Resume ORM models
    └── users.py           # User ORM models
```

#### Pydantic Models (`src/database/models/`)

Pydantic models handle data validation, serialization, and business logic computation. They serve as the interface
between external data and internal processing.

**Key Principles:**

1. **Validation First**: All external data must pass through Pydantic models
2. **Business Logic**: Computed properties and validation methods belong here
3. **Type Safety**: Strict typing with proper validation
4. **Serialization**: Handle JSON serialization and API responses

**Example Pydantic Model:**

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class Job(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    company_id: str = Field(..., description="Associated company ID")
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    posted_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    @validator('salary_max')
    def validate_salary_range(cls, v, values):
        if v and values.get('salary_min') and v < values['salary_min']:
            raise ValueError('Maximum salary must be greater than minimum')
        return v
    
    @property
    def is_recently_posted(self) -> bool:
        """Business logic: Check if job was posted within last 7 days"""
        return (datetime.utcnow() - self.posted_at).days <= 7
    
    @property
    def salary_display(self) -> str:
        """Business logic: Format salary for display"""
        if self.salary_min and self.salary_max:
            return f"R{self.salary_min:,} - R{self.salary_max:,}"
        return "Competitive Salary"
```

#### SQLAlchemy ORM Models (`src/database/sql/`)

ORM models handle database persistence and relationships. They mirror Pydantic models but focus on database operations.

**Key Principles:**

1. **Persistence Only**: Focus on database operations and relationships
2. **Naming Convention**: All ORM classes end with `ORM` suffix
3. **Relationships**: Define SQLAlchemy relationships for data integrity
4. **Conversion Methods**: Provide `to_dict()` methods for Pydantic conversion

**Example ORM Model:**

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.database.sql import Base

class JobORM(Base):
    __tablename__ = 'jobs'
    
    job_id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    company_id = Column(String(36), ForeignKey('companies.company_id'), nullable=False)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    posted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    company = relationship("CompanyORM", back_populates="jobs")
    applications = relationship("JobApplicationORM", back_populates="job")
    
    def to_dict(self) -> dict:
        """Convert ORM instance to dictionary for Pydantic model creation"""
        return {
            'job_id': self.job_id,
            'title': self.title,
            'description': self.description,
            'company_id': self.company_id,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'posted_at': self.posted_at,
            'is_active': self.is_active
        }
```

#### Data Flow Pattern

```python
# ✅ CORRECT: External data → Pydantic → ORM → Database
def create_job(job_data: dict) -> Job:
    # 1. Validate with Pydantic
    job = Job(**job_data)  # Validation happens here
    
    # 2. Convert to ORM for persistence
    job_orm = JobORM(**job.model_dump())
    
    # 3. Save to database
    session.add(job_orm)
    session.commit()
    
    return job

# ✅ CORRECT: Database → ORM → Pydantic → Business Logic
def get_job(job_id: str) -> Optional[Job]:
    # 1. Query database
    job_orm = session.query(JobORM).filter_by(job_id=job_id).first()
    
    if not job_orm:
        return None
    
    # 2. Convert to Pydantic for business logic
    job = Job(**job_orm.to_dict())
    
    # 3. Business logic can now be applied
    return job
```

### Service Layer (`src/services/`)

Services handle external integrations, complex business operations, and cross-cutting concerns. All services follow the
interface pattern.

#### Service Architecture

```
src/services/
├── __init__.py            # Service initialization
├── image_selector.py      # Image processing service
├── ip_address_service.py  # IP geolocation service
├── job_actions_analytics.py      # Job action tracking
├── job_actions_notifications.py  # Job action notifications
├── job_statistics_cache_warmer.py # Cache warming service
├── job_statistics_service.py     # Job performance metrics
├── optimized_match_scoring.py    # Job matching algorithms
├── referral_tracking.py          # Referral system service
├── strategy_weights.py           # Algorithm weighting
├── admin/                 # Administrative services
├── billing/              # Payment and billing services
│   ├── billing_cron_service.py   # Scheduled billing tasks
│   ├── billing_email_service.py  # Billing notifications
│   ├── billing_events.py         # Event tracking
│   ├── billing_service.py        # Core billing operations
│   ├── event_realtime_queue.py   # Real-time event processing
│   ├── invoice_service.py        # Invoice generation
│   ├── payfact_client.py         # PayFast integration
│   ├── payment_service.py        # Payment processing
│   └── schemas_interfaces.py     # Service interfaces
├── hashnode/             # Blog platform integration
│   ├── hashnode_agent_interface.py # AI blog generation
│   ├── hashnode_client.py        # API client
│   ├── hashnode_service.py       # Blog operations
│   └── schema.py                 # Data schemas
├── http_service/         # HTTP client utilities
│   └── http_request_service.py   # Standardized HTTP requests
└── verification_services/ # Identity verification
    ├── github_service.py         # GitHub verification
    ├── linkedin_service.py       # LinkedIn verification
    └── website_service.py        # Website verification
```

#### Service Interface Implementation

```python
from abc import ABC, abstractmethod
import inspect

class ServiceInterface(ABC):
    """Base interface for all services"""
    
    def __init__(self):
        self.__interface_map: dict[str, Callable] = {}
        
    async def execute(self, action: str, *args, **kwargs):
        """
        Dynamically execute service methods
        
        Args:
            action: Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Method result
            
        Raises:
            ValueError: If action not found
            RuntimeError: If execution fails
        """
        try:
            method_to_execute = self.__interface_map[action]
            
            if method_to_execute is None:
                raise ValueError(f"Action '{action}' not found in {self.__class__.__name__}")
                
            if inspect.iscoroutinefunction(method_to_execute):
                return await method_to_execute(*args, **kwargs)
            else:
                return method_to_execute(*args, **kwargs)
                
        except ValueError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Error executing action '{action}': {str(e)}") from e
```

### AI & Automation Layer

#### AI Agents (`src/agents/`)

AI agents provide intelligent automation for various platform functions.

```
src/agents/
├── base.py                # Base agent class
├── memory.py             # Agent memory management
├── openrouter_client.py  # LLM API client
├── blog/                 # Blog content generation
│   ├── agent.py          # Blog generation agent
│   ├── cli.py           # Command-line interface
│   ├── constants.py     # Blog-specific constants
│   ├── hashnode_client.py # Hashnode integration
│   ├── memory.py        # Blog agent memory
│   ├── schemas.py       # Blog data schemas
│   ├── prompts/         # AI prompts for blog generation
│   └── tests/           # Agent testing
├── employer/            # Employer-focused AI tools
│   ├── ats_suggestion_agent.py    # ATS optimization
│   ├── candidate_benchmark.py     # Candidate scoring
│   ├── document_verifications.py  # Document validation
│   ├── job_post_intelligence.py   # Job posting optimization
│   └── llm_keyword_miner.py      # Keyword extraction
└── jobseeker/          # Job seeker AI tools
    ├── application_coach.py       # Application guidance
    ├── cover_letter.py            # Cover letter generation
    └── cv_optimizer.py            # Resume optimization
```

#### Model Context Protocol (`src/mcp/`)

MCP implementations for external tool integrations.

```
src/mcp/
├── blog_mcp.py           # Blog management MCP
├── jobs_mcp.py          # Job management MCP
├── resumes_mcp.py       # Resume management MCP
├── DEVELOPER_GUIDE.md   # MCP development guide
├── TODO.md              # MCP roadmap
├── analytics_mcp/       # Analytics tools
├── authentication_mcp/  # Auth tools
├── documents_mcp/       # Document processing
├── feedback_mcp/        # Feedback collection
├── integration_mcp/     # External integrations
├── jobs_mcp/           # Job-specific tools
├── notifications_mcp/   # Notification tools
├── permissions_mcp/     # Permission management
├── profiles_mcp/       # Profile management
├── resumes_mcp/        # Resume tools
├── search_mcp/         # Search tools
├── support_mcp/        # Support tools
└── user_management_mcp/ # User management tools
```

#### Background Tasks (`src/tasks/`)

Scheduled and background task management.

```
src/tasks/
├── __init__.py           # Task initialization
├── agents/              # AI agent tasks
│   └── task_registry.py # Agent task registration
├── celery/             # Celery task queue
│   ├── celery_app.py   # Celery configuration
│   ├── scheduled_tasks.py # Scheduled task definitions
│   ├── task_queues.py  # Queue management
│   ├── admin_tasks/    # Administrative tasks
│   └── workers/        # Worker processes
├── health/             # Health monitoring
│   └── redis_stream_health.py # Redis health checks
└── task_scheduler/     # APScheduler integration
    ├── ap_scheduler.py # Scheduler configuration
    └── admin_ap_scheduler/ # Admin scheduled tasks
```

### Security & Infrastructure

#### Security Layer (`src/firewall/`)

Comprehensive security middleware and monitoring.

```
src/firewall/
├── __init__.py           # Security initialization
├── auditing.py          # Security audit logging
├── config.py            # Security configuration
├── csrf.py              # CSRF protection
├── database_sec.py      # Database security
├── headers.py           # Security headers
├── job_actions_security.py # Job action security
├── monitor.py           # Security monitoring
├── rate_limiting.py     # Rate limiting
└── smart_rate_limiter.py # Intelligent rate limiting
```

#### Authentication (`src/authentication/`)

JWT and session management.

```
src/authentication/
├── __init__.py          # Auth initialization
└── jwt_helper.py        # JWT token management
```

#### Caching (`src/cache/`)

Redis-based caching system.

```
src/cache/
├── __init__.py          # Cache initialization
├── cache_redis.py       # Redis cache implementation
├── job_actions_cache.py # Job action caching
└── route_cache.py       # Route-level caching
```

### Factory Pattern (`src/factories/`)

Dependency injection and service management.

```
src/factories/
├── __init__.py              # Factory initialization
├── controller_factory.py   # Controller dependency injection
├── redis_factory.py        # Redis connection factory
└── service_factory.py      # Service dependency injection
```

#### Factory Registration Pattern

When creating new controllers or services, they must be registered in the appropriate factory:

```python
# In controller_factory.py
def get_new_feature_controller(self) -> NewFeatureController:
    """Get NewFeatureController instance"""
    self.logger.info(f"Getting NewFeatureController")
    return self._get_controller('new_feature', NewFeatureController)

# In service_factory.py  
def get_new_service(self) -> NewService:
    """Get NewService instance"""
    return self._get_service('new_service', NewService)
```

### Utilities & Helpers (`src/utils/`)

Shared utility functions and helpers.

```
src/utils/
├── __init__.py                    # Utilities initialization
├── file_uploads.py               # File upload handling
├── job_actions_logger.py         # Job action logging
├── job_actions_monitoring.py     # Job action monitoring
└── route_helpers.py              # Route utility functions
```

### Web Scraping (`src/scrappers/`)

Job site scraping modules for data aggregation.

```
src/scrappers/
├── __init__.py          # Scraper initialization
├── career_junction.py   # Career Junction scraper
├── career24.py         # Career24 scraper
├── indeed.py           # Indeed scraper
└── pnet.py             # PNet scraper
```

### Monitoring (`src/monitoring/`)

System monitoring and metrics collection.

```
src/monitoring/
└── match_scoring_metrics.py # Job matching performance metrics
```

### Email Services (`src/emailer/`)

Email service integrations and templates.

```
src/emailer/
└── __init__.py          # Email service initialization
```

### Logging (`src/logger/`)

Centralized logging configuration.

```
src/logger/
└── __init__.py          # Logger initialization
```

## Development Patterns & Best Practices

### Controller Development Pattern

#### 1. Controller Creation Checklist

When creating a new controller:

1. **Inherit from Controllers base class**
2. **Register in ControllerFactory**
3. **Implement error handling with @error_handler**
4. **Use session context managers**
5. **Follow naming conventions**

```python
# Example new controller
from src.controllers.controller import Controllers, error_handler

class NewFeatureController(Controllers):
    """Controller for new feature operations"""
    
    def __init__(self, factory):
        super().__init__(factory)
        
    def init_app(self, app: Flask):
        super().init_app(app)
        
    @error_handler
    async def create_feature(self, data: dict) -> FeatureResult:
        """Create new feature with validation"""
        with self.get_session() as session:
            # Validate with Pydantic
            feature = Feature(**data)
            
            # Convert to ORM
            feature_orm = FeatureORM(**feature.model_dump())
            
            # Save to database
            session.add(feature_orm)
            session.commit()
            
            return FeatureResult(success=True, feature=feature)
```

#### 2. Factory Registration

```python
# In src/factories/controller_factory.py
def get_new_feature_controller(self) -> NewFeatureController:
    """Get NewFeatureController instance"""
    self.logger.info(f"Getting NewFeatureController")
    return self._get_controller('new_feature', NewFeatureController)
```

### Service Development Pattern

#### 1. Service Interface Implementation

All services must implement the standardized interface:

```python
from src.services.interfaces import ServiceInterface

class NewService(ServiceInterface):
    """Service for new functionality"""
    
    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.__interface_map = {
            'create': self._create_item,
            'update': self._update_item,
            'delete': self._delete_item,
            'list': self._list_items
        }
        
    async def _create_item(self, data: dict) -> ServiceResult:
        """Create new item"""
        # Implementation here
        
    async def _update_item(self, item_id: str, data: dict) -> ServiceResult:
        """Update existing item"""
        # Implementation here
```

#### 2. Service Usage in Controllers

```python
# In controller
new_service = self.factory.get_service('new_service')
result = await new_service.execute('create', data=item_data)
```

### Data Model Development Pattern

#### 1. Pydantic Model Creation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class NewFeature(BaseModel):
    """Pydantic model for new feature validation and business logic"""
    
    feature_id: str = Field(..., description="Unique feature identifier")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
    
    @property
    def display_name(self) -> str:
        """Business logic: Format name for display"""
        return self.name.title()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

#### 2. Corresponding ORM Model

```python
from sqlalchemy import Column, String, Boolean, DateTime, Text
from src.database.sql import Base

class NewFeatureORM(Base):
    """SQLAlchemy ORM model for new feature persistence"""
    
    __tablename__ = 'new_features'
    
    feature_id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> dict:
        """Convert ORM to dict for Pydantic model creation"""
        return {
            'feature_id': self.feature_id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at
        }
```

### Error Handling Patterns

#### 1. Controller Error Handling

```python
from src.controllers.controller import error_handler, UnauthorizedError

@error_handler
async def protected_operation(self, user_id: str) -> Result:
    """Operation with comprehensive error handling"""
    
    # Validate authorization
    if not self.is_authorized(user_id):
        raise UnauthorizedError("Access denied")
    
    try:
        with self.get_session() as session:
            # Database operations
            result = session.query(Model).filter_by(user_id=user_id).first()
            
            if not result:
                return Result(success=False, message="Not found")
                
            return Result(success=True, data=result.to_dict())
            
    except ValidationError as e:
        # Pydantic validation errors
        return Result(success=False, message=f"Validation error: {e}")
    except SQLAlchemyError as e:
        # Database errors
        self.logger.error(f"Database error: {e}")
        return Result(success=False, message="Database operation failed")
```

#### 2. Service Error Handling

```python
async def _service_method(self, data: dict) -> ServiceResult:
    """Service method with error handling"""
    try:
        # Validate input
        validated_data = InputModel(**data)
        
        # Process data
        result = await self._process_data(validated_data)
        
        return ServiceResult(success=True, data=result)
        
    except ValidationError as e:
        return ServiceResult(success=False, message=f"Invalid input: {e}")
    except Exception as e:
        self.logger.error(f"Service error: {e}")
        return ServiceResult(success=False, message="Service operation failed")
```

### Testing Patterns

#### 1. Controller Testing

```python
import pytest
from src.controllers.new_feature import NewFeatureController
from src.database.models.new_feature import NewFeature

@pytest.fixture
def controller():
    return NewFeatureController(mock_factory)

@pytest.mark.asyncio
async def test_create_feature(controller):
    """Test feature creation"""
    data = {
        'feature_id': 'test-123',
        'name': 'Test Feature',
        'description': 'Test description'
    }
    
    result = await controller.create_feature(data)
    
    assert result.success is True
    assert result.feature.name == 'Test Feature'
```

#### 2. Service Testing

```python
@pytest.mark.asyncio
async def test_service_create(service):
    """Test service creation method"""
    data = {'name': 'Test Item'}
    
    result = await service.execute('create', data=data)
    
    assert result.success is True
    assert 'item_id' in result.data
```

### Performance Optimization Patterns

#### 1. Controller Session Management

```python
class OptimizedController(Controllers):
    """Controller with optimized session management"""
    
    def __init__(self, factory):
        super().__init__(factory)
        # Pre-warm session pool
        self.session_limit = 10
        
    @error_handler
    async def bulk_operation(self, items: List[dict]) -> BulkResult:
        """Optimized bulk operation"""
        with self.get_session() as session:
            # Batch processing
            batch_size = 100
            results = []
            
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_results = await self._process_batch(session, batch)
                results.extend(batch_results)
                
                # Commit in batches
                if i % (batch_size * 5) == 0:
                    session.commit()
                    
            return BulkResult(success=True, results=results)
```

#### 2. Caching Patterns

```python
from src.cache.cache_redis import cache

class CachedController(Controllers):
    """Controller with caching support"""
    
    @error_handler
    async def get_cached_data(self, key: str) -> CachedResult:
        """Get data with caching"""
        
        # Try cache first
        cached_data = cache.get(f"data:{key}")
        if cached_data:
            return CachedResult(success=True, data=cached_data, from_cache=True)
        
        # Fetch from database
        with self.get_session() as session:
            data = session.query(Model).filter_by(key=key).first()
            
            if data:
                # Cache for 30 minutes
                cache.set(f"data:{key}", data.to_dict(), ttl=1800)
                return CachedResult(success=True, data=data.to_dict(), from_cache=False)
                
        return CachedResult(success=False, message="Data not found")
```

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

## Critical Development Rules

### 1. Data Flow Rules

- **NEVER** bypass Pydantic validation for external data
- **ALWAYS** use ORM models for database operations
- **NEVER** import controllers directly in routes
- **ALWAYS** use the factory pattern for controller access

### 2. Error Handling Rules

- **ALWAYS** use `@error_handler` decorator on controller methods
- **NEVER** let exceptions bubble up to routes without handling
- **ALWAYS** return standardized result objects
- **NEVER** expose internal error details to users

### 3. Performance Rules

- **ALWAYS** use session context managers
- **NEVER** leave database sessions open
- **ALWAYS** implement caching for expensive operations
- **NEVER** perform N+1 queries without optimization

### 4. Security Rules

- **ALWAYS** validate user permissions in controllers
- **NEVER** trust user input without validation
- **ALWAYS** use parameterized queries
- **NEVER** expose sensitive data in logs

### 5. Testing Rules

- **ALWAYS** write tests for new controllers and services
- **NEVER** commit code without passing tests
- **ALWAYS** test error conditions
- **NEVER** skip integration tests for critical paths