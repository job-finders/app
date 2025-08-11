# Database Models Steering File

## Overview
The `src/database/models/` module defines SQLAlchemy ORM models that represent the core business entities in the Job Finders platform. All models follow consistent patterns for South African employment marketplace requirements.

## Core Model Architecture

### Model Inheritance Hierarchy
```python
from sqlalchemy import Column, Integer, DateTime, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

## Primary Business Models

### User Management Models

#### UserORM - Base User Entity
```python
class UserORM(BaseModel):
    __tablename__ = 'user'
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    user_type = Column(String(20), nullable=False)  # 'jobseeker', 'employer', 'admin'
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    
    # South African specific fields
    sa_id_number = Column(String(13), nullable=True, unique=True)  # RSA ID number
    preferred_language = Column(String(10), default='en', nullable=False)  # 'en', 'af', 'zu', etc.
```

#### JobSeekerProfileORM
```python
class JobSeekerProfileORM(BaseModel):
    __tablename__ = 'jobseeker_profile'
    
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, unique=True)
    
    # Personal Information
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)  # 'male', 'female', 'other', 'prefer_not_to_say'
    nationality = Column(String(50), default='South African')
    
    # Location (South African specific)
    province = Column(String(50), nullable=True)  # 'gauteng', 'western_cape', etc.
    city = Column(String(100), nullable=True)
    suburb = Column(String(100), nullable=True)
    postal_code = Column(String(10), nullable=True)
    willing_to_relocate = Column(Boolean, default=False)
    
    # Employment Preferences
    desired_salary_min = Column(Integer, nullable=True)  # In ZAR
    desired_salary_max = Column(Integer, nullable=True)
    job_type_preference = Column(String(50), nullable=True)  # 'full_time', 'part_time', 'contract'
    availability = Column(String(20), default='immediate')  # 'immediate', '1_month', '2_months'
    
    # Skills & Experience
    years_experience = Column(Integer, default=0)
    education_level = Column(String(50), nullable=True)  # 'matric', 'diploma', 'degree', 'postgraduate'
    skills = Column(Text, nullable=True)  # JSON array of skills
    
    # CV Management
    cv_file_path = Column(String(500), nullable=True)
    cv_uploaded_at = Column(DateTime, nullable=True)
    profile_completion = Column(Integer, default=0)  # Percentage 0-100
    
    # Relationships
    user = relationship("UserORM", back_populates="jobseeker_profile")
    applications = relationship("JobApplicationORM", back_populates="jobseeker")
```

### Company & Employer Models

#### CompanyORM - Business Entity
```python
class CompanyORM(BaseModel):
    __tablename__ = 'company'
    
    # Basic Company Information
    company_name = Column(String(255), nullable=False, index=True)
    trading_name = Column(String(255), nullable=True)  # If different from company name
    company_registration_number = Column(String(20), nullable=True, unique=True)  # CIPC number
    vat_number = Column(String(15), nullable=True)
    
    # Contact Information
    primary_email = Column(String(255), nullable=False)
    primary_phone = Column(String(20), nullable=False)
    website = Column(String(255), nullable=True)
    
    # Address (South African format)
    physical_address_line1 = Column(String(255), nullable=True)
    physical_address_line2 = Column(String(255), nullable=True)
    physical_city = Column(String(100), nullable=True)
    physical_province = Column(String(50), nullable=True)
    physical_postal_code = Column(String(10), nullable=True)
    
    postal_address_line1 = Column(String(255), nullable=True)
    postal_address_line2 = Column(String(255), nullable=True)
    postal_city = Column(String(100), nullable=True)
    postal_province = Column(String(50), nullable=True)
    postal_postal_code = Column(String(10), nullable=True)
    
    # Business Details
    industry = Column(String(100), nullable=True)
    company_size = Column(String(20), nullable=True)  # '1-10', '11-50', '51-200', '201-500', '500+'
    founded_year = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    logo_path = Column(String(500), nullable=True)
    
    # Verification Status
    verification_status = Column(String(20), default='pending')  # 'pending', 'verified', 'rejected'
    verified_at = Column(DateTime, nullable=True)
    verification_documents = Column(Text, nullable=True)  # JSON array of document paths
    
    # Platform Settings
    is_premium = Column(Boolean, default=False)
    job_posting_limit = Column(Integer, default=5)  # Free tier limit
    
    # Relationships
    employers = relationship("EmployerORM", back_populates="company")
    jobs = relationship("JobORM", back_populates="company")
    billing_profile = relationship("CompanyBillingProfileORM", back_populates="company", uselist=False)
```

#### EmployerORM - Individual Employer Accounts
```python
class EmployerORM(BaseModel):
    __tablename__ = 'employer'
    
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, unique=True)
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)
    
    # Role within company
    job_title = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    role_level = Column(String(20), nullable=False)  # 'admin', 'hr_manager', 'hiring_manager', 'recruiter'
    
    # Permissions
    can_post_jobs = Column(Boolean, default=True)
    can_manage_candidates = Column(Boolean, default=True)
    can_manage_billing = Column(Boolean, default=False)
    can_manage_company = Column(Boolean, default=False)
    
    # Employment verification
    employment_verified = Column(Boolean, default=False)
    employment_verification_method = Column(String(50), nullable=True)  # 'email_domain', 'document', 'phone'
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("UserORM", back_populates="employer_profile")
    company = relationship("CompanyORM", back_populates="employers")
    posted_jobs = relationship("JobORM", back_populates="posted_by_employer")
```

### Job & Application Models

#### JobORM - Job Postings
```python
class JobORM(BaseModel):
    __tablename__ = 'job'
    
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)
    posted_by_employer_id = Column(Integer, ForeignKey('employer.id'), nullable=False)
    
    # Job Details
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    
    # Employment Details
    job_type = Column(String(20), nullable=False)  # 'full_time', 'part_time', 'contract', 'internship'
    contract_duration = Column(String(50), nullable=True)  # For contract positions
    experience_level = Column(String(20), nullable=True)  # 'entry', 'mid', 'senior', 'executive'
    education_required = Column(String(50), nullable=True)
    
    # Compensation (South African context)
    salary_min = Column(Integer, nullable=True)  # ZAR
    salary_max = Column(Integer, nullable=True)  # ZAR
    salary_period = Column(String(20), default='monthly')  # 'hourly', 'monthly', 'annually'
    salary_currency = Column(String(3), default='ZAR')
    benefits = Column(Text, nullable=True)  # JSON array of benefits
    
    # Location
    work_location_type = Column(String(20), nullable=False)  # 'onsite', 'remote', 'hybrid'
    province = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    
    # Application Settings
    application_email = Column(String(255), nullable=True)
    application_url = Column(String(500), nullable=True)
    application_instructions = Column(Text, nullable=True)
    
    # Job Status
    status = Column(String(20), default='active')  # 'active', 'paused', 'closed', 'expired'
    expires_at = Column(DateTime, nullable=True)
    applications_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    
    # Source Information (for aggregated jobs)
    source_site = Column(String(50), nullable=True)  # 'career24', 'pnet', 'indeed', null for direct posts
    external_id = Column(String(255), nullable=True)  # Original job ID from source
    source_url = Column(String(500), nullable=True)
    last_scraped_at = Column(DateTime, nullable=True)
    
    # SEO & Search
    slug = Column(String(255), nullable=True, unique=True, index=True)
    search_keywords = Column(Text, nullable=True)  # For search optimization
    
    # Relationships
    company = relationship("CompanyORM", back_populates="jobs")
    posted_by_employer = relationship("EmployerORM", back_populates="posted_jobs")
    applications = relationship("JobApplicationORM", back_populates="job")
    categories = relationship("JobCategoryORM", secondary="job_category_mapping")
```

#### JobApplicationORM
```python
class JobApplicationORM(BaseModel):
    __tablename__ = 'job_application'
    
    job_id = Column(Integer, ForeignKey('job.id'), nullable=False)
    jobseeker_id = Column(Integer, ForeignKey('jobseeker_profile.id'), nullable=False)
    
    # Application Details
    status = Column(String(20), default='pending')  # 'pending', 'reviewed', 'shortlisted', 'rejected', 'hired'
    cover_letter = Column(Text, nullable=True)
    cv_file_path = Column(String(500), nullable=True)  # Snapshot of CV at application time
    
    # Application Source
    application_source = Column(String(20), nullable=False)  # 'direct', 'aggregated'
    applied_via = Column(String(50), nullable=True)  # 'job_finders', 'external_site'
    
    # Employer Actions
    viewed_by_employer = Column(Boolean, default=False)
    viewed_at = Column(DateTime, nullable=True)
    employer_notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 employer rating
    
    # Communication
    last_contact_date = Column(DateTime, nullable=True)
    next_followup_date = Column(DateTime, nullable=True)
    
    # Relationships
    job = relationship("JobORM", back_populates="applications")
    jobseeker = relationship("JobSeekerProfileORM", back_populates="applications")
    
    # Unique constraint to prevent duplicate applications
    __table_args__ = (UniqueConstraint('job_id', 'jobseeker_id'),)
```

### Billing & Subscription Models

#### CompanyBillingProfileORM
```python
class CompanyBillingProfileORM(BaseModel):
    __tablename__ = 'company_billing_profile'
    
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False, unique=True)
    
    # Subscription Details
    subscription_plan = Column(String(20), default='free')  # 'free', 'basic', 'professional', 'enterprise'
    subscription_status = Column(String(20), default='active')  # 'active', 'suspended', 'cancelled'
    subscription_start_date = Column(DateTime, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    
    # Billing Information (South African context)
    billing_email = Column(String(255), nullable=True)
    billing_contact_name = Column(String(255), nullable=True)
    billing_phone = Column(String(20), nullable=True)
    
    # Payment Integration (PayFast)
    payfast_merchant_id = Column(String(100), nullable=True)
    payment_method_id = Column(Integer, ForeignKey('payment_method.id'), nullable=True)
    
    # Usage Tracking
    jobs_posted_this_month = Column(Integer, default=0)
    jobs_posted_total = Column(Integer, default=0)
    monthly_job_limit = Column(Integer, default=5)
    
    # Auto-renewal
    auto_renewal_enabled = Column(Boolean, default=True)
    next_billing_date = Column(DateTime, nullable=True)
    
    # Relationships
    company = relationship("CompanyORM", back_populates="billing_profile")
    payment_method = relationship("PaymentMethodORM")
    invoices = relationship("InvoiceORM", back_populates="billing_profile")
```

#### InvoiceORM - PayFast Integration
```python
class InvoiceORM(BaseModel):
    __tablename__ = 'invoice'
    
    billing_profile_id = Column(Integer, ForeignKey('company_billing_profile.id'), nullable=False)
    
    # Invoice Details
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    
    # Amounts (ZAR)
    subtotal = Column(Numeric(10, 2), nullable=False)
    vat_amount = Column(Numeric(10, 2), nullable=False)  # 15% VAT in South Africa
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Payment Status
    payment_status = Column(String(20), default='pending')  # 'pending', 'paid', 'overdue', 'cancelled'
    payment_date = Column(DateTime, nullable=True)
    payment_reference = Column(String(255), nullable=True)
    
    # PayFast Integration
    payfast_payment_id = Column(String(100), nullable=True)
    payfast_signature = Column(String(255), nullable=True)
    
    # Invoice Items (JSON)
    line_items = Column(Text, nullable=False)  # JSON array of billing items
    
    # Relationships
    billing_profile = relationship("CompanyBillingProfileORM", back_populates="invoices")
    billing_events = relationship("BillingEventORM", back_populates="invoice")
```

## Supporting Models

### Geographic & Location Models
```python
class ProvinceORM(BaseModel):
    __tablename__ = 'province'
    
    code = Column(String(10), unique=True, nullable=False)  # 'GP', 'WC', 'KZN', etc.
    name = Column(String(100), unique=True, nullable=False)
    display_order = Column(Integer, default=0)

class CityORM(BaseModel):
    __tablename__ = 'city'
    
    province_id = Column(Integer, ForeignKey('province.id'), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    is_major_city = Column(Boolean, default=False)
    
    province = relationship("ProvinceORM")
```

### Job Categories & Skills
```python
class JobCategoryORM(BaseModel):
    __tablename__ = 'job_category'
    
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    parent_category_id = Column(Integer, ForeignKey('job_category.id'), nullable=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon class name
    display_order = Column(Integer, default=0)
    
    # Self-referential relationship for subcategories
    parent = relationship("JobCategoryORM", remote_side="JobCategoryORM.id")
    subcategories = relationship("JobCategoryORM")

class SkillORM(BaseModel):
    __tablename__ = 'skill'
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=True)  # 'technical', 'soft', 'industry'
    verified = Column(Boolean, default=False)  # Curated vs user-generated
```

## Model Conventions

### Naming Standards
- **Table names**: Singular, lowercase, snake_case
- **Column names**: snake_case, descriptive
- **Foreign keys**: `{table_name}_id`
- **ORM classes**: PascalCase with `ORM` suffix
- **Boolean fields**: Start with `is_`, `has_`, `can_`, `should_`

### Common Field Patterns
```python
# Standard audit fields (inherited from BaseModel)
id, created_at, updated_at, is_active

# South African specific fields
sa_id_number      # RSA ID number (13 digits)
vat_number        # VAT registration number  
company_registration_number  # CIPC number
province          # South African provinces
postal_code       # South African postal codes

# Currency and amounts
# Always use ZAR as base currency, Numeric(10,2) for money fields
salary_min = Column(Numeric(10, 2), nullable=True)
vat_amount = Column(Numeric(10, 2), nullable=False)

# Status enumerations
status = Column(String(20), default='active')
# Common values: 'active', 'inactive', 'pending', 'approved', 'rejected'
```

### Relationship Patterns
```python
# One-to-One
billing_profile = relationship("CompanyBillingProfileORM", back_populates="company", uselist=False)

# One-to-Many  
jobs = relationship("JobORM", back_populates="company")

# Many-to-Many with association table
categories = relationship("JobCategoryORM", secondary="job_category_mapping")

# Self-referential
parent = relationship("JobCategoryORM", remote_side="JobCategoryORM.id")
```

### Index Strategy
- **Primary keys**: Automatic
- **Foreign keys**: Always indexed
- **Email fields**: Unique index
- **Search fields**: Composite indexes for job search
- **Status fields**: Filtered indexes where appropriate

```python
# Example composite index for job search
Index('idx_job_search', 'status', 'province', 'job_type', 'created_at')
```

### Validation Patterns
```python
from sqlalchemy.orm import validates

class CompanyORM(BaseModel):
    @validates('company_registration_number')
    def validate_registration_number(self, key, value):
        if value and not re.match(r'^\d{4}/\d{6}/\d{2}$', value):
            raise ValueError("Invalid CIPC registration number format")
        return value
    
    @validates('vat_number') 
    def validate_vat_number(self, key, value):
        if value and not re.match(r'^\d{10}$', value):
            raise ValueError("VAT number must be 10 digits")
        return value
```

## South African Compliance

### Employment Equity Data
```python
# Optional demographic fields for Employment Equity reporting
class JobSeekerProfileORM(BaseModel):
    # ... other fields ...
    
    # Employment Equity categories (optional, for reporting)
    race = Column(String(20), nullable=True)  # 'african', 'coloured', 'indian', 'white'
    disability_status = Column(String(20), nullable=True)  # 'none', 'yes', 'prefer_not_to_say'
    equity_consent = Column(Boolean, default=False)  # Explicit consent for EE data collection
```

### Language Support
```python
# Multi-language content support
class JobORM(BaseModel):
    # ... other fields ...
    
    language = Column(String(10), default='en')  # 'en', 'af', 'zu', 'xh', etc.
    translated_content = Column(Text, nullable=True)  # JSON with translations
```

This steering file establishes consistent, scalable database patterns that align with South African business requirements and employment regulations while maintaining clean ORM architecture.