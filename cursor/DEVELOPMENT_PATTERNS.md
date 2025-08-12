# Job Finders - Development Patterns Specification

## Core Development Principles

### 1. **Factory Pattern Enforcement**
- **NO DIRECT INSTANTIATION** of controllers or services
- All access must go through factory classes
- Ensures proper dependency injection and lifecycle management

### 2. **Error Handling First**
- Every controller method must use `@error_handler` decorator
- Comprehensive error logging and user-friendly error responses
- Graceful degradation and failure recovery

### 3. **Type Safety & Validation**
- Pydantic models for all external data validation
- Strict type hints throughout the codebase
- Runtime validation for data integrity

## Controller Development Patterns

### **Base Controller Structure**
```python
from src.factories.controller_factory import ControllerFactory
from src.utils.job_actions_error_handler import error_handler
from src.utils.job_actions_api_response import Response

class DomainController:
    @error_handler
    def method_name(self, request_data: PydanticModel) -> Response:
        # 1. Validate input through Pydantic model
        # 2. Get service through factory
        # 3. Execute business logic
        # 4. Return standardized response
        
        service = ServiceFactory.get_service('service_name')
        result = service.execute(request_data)
        
        return Response(
            data=result,
            message="Operation completed successfully",
            status="success"
        )
```

### **Controller Method Requirements**
- **Decorator**: Must use `@error_handler`
- **Input Validation**: Pydantic model parameter
- **Service Access**: Through ServiceFactory only
- **Response Format**: Standardized Response object
- **Error Handling**: Automatic error catching and logging

### **Controller Registration**
```python
# In src/factories/controller_factory.py
CONTROLLER_REGISTRY = {
    'jobs': JobsController,
    'users': UsersController,
    'company': CompanyController,
    # Add new controllers here
}

# Usage
controller = ControllerFactory.get_controller('jobs')
```

## Service Development Patterns

### **Service Interface Contract**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel

class BaseService(ABC):
    @abstractmethod
    def execute(self, data: BaseModel) -> Dict[str, Any]:
        """Execute the service operation"""
        pass

class JobService(BaseService):
    def execute(self, data: JobRequest) -> Dict[str, Any]:
        # Business logic implementation
        # Database operations
        # External service calls
        return {
            'status': 'success',
            'data': result_data,
            'metadata': metadata
        }
```

### **Service Method Requirements**
- **Interface**: Must implement `execute()` method
- **Input**: Pydantic model parameter
- **Output**: Dictionary with standardized structure
- **Error Handling**: Proper exception handling and logging
- **Database Sessions**: Use session context managers

### **Service Registration**
```python
# In src/factories/service_factory.py
SERVICE_REGISTRY = {
    'jobs': JobService,
    'users': UserService,
    'billing': BillingService,
    # Add new services here
}

# Usage
service = ServiceFactory.get_service('jobs')
```

## Database Development Patterns

### **Session Management**
```python
from src.database.sql.session_manager import SessionManager

class JobService(BaseService):
    def execute(self, data: JobRequest) -> Dict[str, Any]:
        with SessionManager() as session:
            try:
                # Database operations
                job = session.query(Job).filter_by(id=data.job_id).first()
                
                if not job:
                    raise ValueError("Job not found")
                
                # More operations...
                session.commit()
                return {'status': 'success', 'data': job_data}
                
            except Exception as e:
                session.rollback()
                raise e
```

### **Model Relationships**
```python
# SQLAlchemy Models with proper relationships
class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="jobs")
    applications = relationship("JobApplication", back_populates="job")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### **Database Migration Pattern**
```python
# In src/database/migrations/
def upgrade():
    # Add new columns
    op.add_column('jobs', sa.Column('new_field', sa.String(255)))
    
    # Create indexes
    op.create_index('idx_jobs_title', 'jobs', ['title'])
    
    # Data migrations
    connection = op.get_bind()
    connection.execute("UPDATE jobs SET new_field = 'default_value'")

def downgrade():
    # Revert changes
    op.drop_column('jobs', 'new_field')
    op.drop_index('idx_jobs_title', 'jobs')
```

## Route Development Patterns

### **Route Registration**
```python
# In src/routes/__init__.py
from flask import Blueprint
from src.controllers.jobs import JobsController

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/jobs', methods=['GET'])
def get_jobs():
    controller = ControllerFactory.get_controller('jobs')
    return controller.get_jobs()

@jobs_bp.route('/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    controller = ControllerFactory.get_controller('jobs')
    return controller.get_job(job_id)
```

### **Route Middleware**
```python
# Authentication middleware
@jobs_bp.before_request
def authenticate_request():
    # JWT token validation
    # User authentication
    # Role-based access control
    pass

# Rate limiting middleware
@jobs_bp.before_request
def rate_limit():
    # Smart rate limiting
    # IP-based throttling
    # User-based quotas
    pass
```

## Error Handling Patterns

### **Error Handler Decorator**
```python
def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            # Pydantic validation errors
            logger.error(f"Validation error: {e}")
            return Response(
                data=None,
                message="Invalid request data",
                status="error",
                errors=e.errors()
            )
        except DatabaseError as e:
            # Database errors
            logger.error(f"Database error: {e}")
            return Response(
                data=None,
                message="Database operation failed",
                status="error"
            )
        except Exception as e:
            # Generic errors
            logger.error(f"Unexpected error: {e}")
            return Response(
                data=None,
                message="An unexpected error occurred",
                status="error"
            )
    return wrapper
```

### **Custom Exception Classes**
```python
class JobFindersException(Exception):
    """Base exception for Job Finders application"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class ValidationException(JobFindersException):
    """Data validation exception"""
    pass

class AuthenticationException(JobFindersException):
    """Authentication exception"""
    pass

class AuthorizationException(JobFindersException):
    """Authorization exception"""
    pass
```

## Caching Patterns

### **Cache Integration**
```python
from src.cache.job_actions_cache_manager import CacheManager

class JobService(BaseService):
    def execute(self, data: JobRequest) -> Dict[str, Any]:
        # Check cache first
        cache_key = f"job:{data.job_id}"
        cached_result = CacheManager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Execute business logic
        result = self._process_job(data)
        
        # Cache the result
        CacheManager.set(cache_key, result, ttl=3600)
        
        return result
```

### **Cache Invalidation**
```python
class JobService(BaseService):
    def update_job(self, data: JobUpdateRequest) -> Dict[str, Any]:
        with SessionManager() as session:
            # Update job in database
            job = session.query(Job).filter_by(id=data.job_id).first()
            job.title = data.title
            session.commit()
            
            # Invalidate related caches
            CacheManager.delete(f"job:{data.job_id}")
            CacheManager.delete(f"jobs:company:{job.company_id}")
            CacheManager.delete("jobs:search:*")
            
            return {'status': 'success', 'data': job_data}
```

## Security Patterns

### **Input Sanitization**
```python
from src.firewall.job_actions_security import SecurityManager

class JobService(BaseService):
    def execute(self, data: JobRequest) -> Dict[str, Any]:
        # Sanitize input
        sanitized_title = SecurityManager.sanitize_input(data.title)
        sanitized_description = SecurityManager.sanitize_html(data.description)
        
        # Validate against security rules
        SecurityManager.validate_job_data({
            'title': sanitized_title,
            'description': sanitized_description
        })
        
        # Process sanitized data
        return self._create_job(sanitized_title, sanitized_description)
```

### **Rate Limiting**
```python
from src.firewall.smart_rate_limiter import SmartRateLimiter

class JobController:
    @error_handler
    def create_job(self, data: JobCreateRequest) -> Response:
        # Check rate limits
        user_id = get_current_user_id()
        if not SmartRateLimiter.allow_request(user_id, 'job_creation'):
            raise RateLimitExceeded("Too many job creation requests")
        
        # Process request
        service = ServiceFactory.get_service('jobs')
        result = service.execute(data)
        
        return Response(data=result)
```

## Testing Patterns

### **Test Structure**
```python
# tests/test_jobs.py
import pytest
from src.factories.controller_factory import ControllerFactory
from src.factories.service_factory import ServiceFactory

class TestJobsController:
    def setup_method(self):
        # Setup test data
        self.controller = ControllerFactory.get_controller('jobs')
        self.test_data = JobRequest(
            title="Test Job",
            company="Test Company",
            location="Test Location"
        )
    
    def test_create_job_success(self):
        result = self.controller.create_job(self.test_data)
        assert result.status == "success"
        assert result.data is not None
    
    def test_create_job_validation_error(self):
        invalid_data = JobRequest(title="", company="", location="")
        result = self.controller.create_job(invalid_data)
        assert result.status == "error"
        assert "Invalid request data" in result.message
```

### **Mock Services**
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_job_service():
    service = Mock()
    service.execute.return_value = {
        'status': 'success',
        'data': {'id': 1, 'title': 'Test Job'}
    }
    return service

@pytest.fixture
def mock_controller(mock_job_service):
    with patch('src.factories.service_factory.ServiceFactory.get_service') as mock_get:
        mock_get.return_value = mock_job_service
        yield
```

## Logging Patterns

### **Structured Logging**
```python
import logging
from src.logger import get_logger

logger = get_logger(__name__)

class JobService(BaseService):
    def execute(self, data: JobRequest) -> Dict[str, Any]:
        logger.info("Processing job creation request", extra={
            'user_id': get_current_user_id(),
            'job_title': data.title,
            'company': data.company,
            'request_id': get_request_id()
        })
        
        try:
            result = self._create_job(data)
            logger.info("Job created successfully", extra={
                'job_id': result['id'],
                'request_id': get_request_id()
            })
            return result
        except Exception as e:
            logger.error("Job creation failed", extra={
                'error': str(e),
                'request_id': get_request_id()
            })
            raise
```

### **Performance Logging**
```python
from src.utils.job_actions_performance_logger import PerformanceLogger

class JobService(BaseService):
    def execute(self, data: JobRequest) -> Dict[str, Any]:
        with PerformanceLogger.measure("job_creation"):
            # Business logic execution
            result = self._create_job(data)
            
            # Log performance metrics
            PerformanceLogger.log_metric("jobs_created", 1)
            PerformanceLogger.log_metric("job_creation_time", execution_time)
            
            return result
```

## Configuration Patterns

### **Environment Configuration**
```python
# src/config/__init__.py
import os
from typing import Dict, Any

class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'mysql://localhost/jobfinders')
    DATABASE_POOL_SIZE = int(os.getenv('DATABASE_POOL_SIZE', 10))
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # Security
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default-secret')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
    
    # External Services
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    PAYFAST_MERCHANT_ID = os.getenv('PAYFAST_MERCHANT_ID')
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        return {
            'database': {
                'url': cls.DATABASE_URL,
                'pool_size': cls.DATABASE_POOL_SIZE
            },
            'redis': {
                'url': cls.REDIS_URL,
                'db': cls.REDIS_DB
            },
            'security': {
                'jwt_secret': cls.JWT_SECRET_KEY,
                'jwt_expiration': cls.JWT_EXPIRATION_HOURS
            }
        }
```

## Code Quality Standards

### **Code Style**
- **PEP 8**: Python style guide compliance
- **Type Hints**: All functions must have type annotations
- **Docstrings**: Comprehensive documentation for all public methods
- **Line Length**: Maximum 120 characters per line
- **Imports**: Organized imports with proper grouping

### **Code Organization**
- **Single Responsibility**: Each class/method has one clear purpose
- **Dependency Inversion**: Depend on abstractions, not concretions
- **Interface Segregation**: Keep interfaces focused and specific
- **Open/Closed Principle**: Open for extension, closed for modification

### **Performance Considerations**
- **Lazy Loading**: Load data only when needed
- **Connection Pooling**: Reuse database and Redis connections
- **Batch Operations**: Group database operations when possible
- **Async Processing**: Use background tasks for heavy operations

## Deployment Patterns

### **Environment Variables**
```bash
# .env file
DATABASE_URL=mysql://user:password@localhost/jobfinders
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key
OPENROUTER_API_KEY=your-api-key
PAYFAST_MERCHANT_ID=your-merchant-id
```

### **Docker Configuration**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

### **Health Checks**
```python
# src/tasks/health/health_check.py
class HealthChecker:
    @staticmethod
    def check_database():
        try:
            with SessionManager() as session:
                session.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    @staticmethod
    def check_redis():
        try:
            redis_client = RedisFactory.get_client()
            redis_client.ping()
            return True
        except Exception:
            return False
    
    @staticmethod
    def check_all():
        return {
            'database': HealthChecker.check_database(),
            'redis': HealthChecker.check_redis(),
            'overall': all([
                HealthChecker.check_database(),
                HealthChecker.check_redis()
            ])
        }
```

This development patterns specification ensures consistency, maintainability, and quality across the entire Job Finders codebase.
