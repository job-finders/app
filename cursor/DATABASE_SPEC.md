# Job Finders - Database Specification

## ⚠️ CRITICAL: ID Field Immutability

**ID Fields are the foundation of the entire system and MUST NEVER be changed under any circumstances.**

### **ID Field Rules:**
- **IMMUTABLE**: Once assigned, ID values cannot be modified, deleted, or reused
- **SYSTEM INTEGRITY**: These IDs are referenced throughout the application, database relationships, caching layers, and external integrations
- **BUSINESS LOGIC**: Job applications, user sessions, billing records, and AI matching algorithms all depend on consistent ID references
- **CACHE DEPENDENCIES**: Redis cache keys, session management, and performance optimizations rely on stable ID values
- **EXTERNAL INTEGRATIONS**: ATS systems, payment gateways, and third-party services reference these IDs

### **Consequences of ID Changes:**
- **Data Corruption**: Broken foreign key relationships
- **Cache Invalidation**: Massive cache failures across the system
- **Session Loss**: User authentication and authorization failures
- **Business Logic Failures**: Job matching, applications, and billing system breakdowns
- **External System Failures**: ATS integrations and payment processing errors

### **ID Field Specifications:**
All ID fields are defined with:
```python
id = Column(String(ID_LEN), primary_key=True, default=lambda: str(uuid.uuid4()), 
           comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
```

**Note:** `ID_LEN = 64` (UUID string length)

---

## Database Architecture Overview

The Job Finders platform uses **MySQL** as the primary database with **SQLAlchemy 2.0.40** as the ORM layer, implementing a sophisticated data model that supports complex job matching, user management, and business operations.

## Core Database Models

### **User Management Models**

#### **Users Model** (`src/database/sql/users.py`)
```python
class UserORM(Base):
    __tablename__ = 'users'
    
    uid = Column(String(ID_LEN), primary_key=True, unique=True, index=True, 
                comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
    name = Column(String(NAME_LEN), nullable=False, index=True)
    email = Column(String(255))
    password_hash = Column(String(255))
    role = Column(String(12), default="seeker")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)
    last_login = Column(DateTime(timezone=True), onupdate=utc_time, nullable=True)
```

#### **Job Seeker Profile** (`src/database/sql/jobseeker_profile.py`)
```python
class JobSeekerProfileORM(Base):
    __tablename__ = 'jobseeker_profiles'
    
    user_uid = Column(String(ID_LEN), primary_key=True, unique=True, index=True,
                     comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
    # Additional fields would be defined here based on your actual model
```

#### **Employer Profile** (`src/database/sql/employer.py`)
```python
class EmployerORM(Base):
    __tablename__ = "employers"
    
    employer_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True,
                        comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
    user_uid = Column(String(128), nullable=False, unique=True, index=True)
    company_id = Column(String(128), ForeignKey('companies.company_id'), nullable=False, index=True)
    
    # Verification & timestamps
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)
    updated_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)
    
    # Personal information
    full_name = Column(String(100), nullable=True)
    job_title = Column(String(100), nullable=True, default="Human Resource")
    profile_picture_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    
    # Contact information
    company_email = Column(String(255), nullable=True)
    personal_email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    alternate_phone = Column(String(20), nullable=True)
    
    # Social profiles
    linkedin_url = Column(Text, nullable=True)
    twitter_handle = Column(String(50), nullable=True)
    
    # Professional details
    department = Column(String(100), nullable=True)
    hire_date = Column(DateTime(timezone=True), nullable=True)
```

### **Company & Organization Models**

#### **Company Models** (`src/database/sql/company.py`)
```python
class CompanyORM(Base):
    __tablename__ = 'companies'
    
    company_id = Column(String(ID_LEN), primary_key=True, index=True,
                       comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
    name = Column(String(255), unique=True, index=True)
    description = Column(Text)
    industry = Column(String(100))
    website = Column(String(255))
    logo_url = Column(String(255))
    
    # Location
    city = Column(String(100))
    province = Column(String(100))
    country = Column(String(100))
    
    # Contact Info
    contact_email = Column(String(255))
    phone_number = Column(String(20))
    
    billing_email = Column(String(255), nullable=True)
    send_invoice_emails = Column(Boolean, default=True)
    send_trial_reminders = Column(Boolean, default=True)
    
    # Company Details
    employee_count = Column(Integer)
    founded_year = Column(Integer)
    tech_stack = Column(JSON)
    
    # Social Media
    linkedin_url = Column(String(255), nullable=True)
    twitter_handle = Column(String(50), nullable=True)
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=utc_time)
    updated_at = Column(DateTime(timezone=True), default=utc_time, onupdate=utc_time)
    
    # Relationships
    jobs = relationship("JobsORM", back_populates="company")
    employers = relationship("EmployerORM", back_populates="company")
    saved_candidates = relationship("SavedCandidatesORM", back_populates="company")
    followers = relationship("CompanyFollowingORM", back_populates="followed_company")
```

### **Job & Employment Models**

#### **Jobs Model** (`src/database/sql/jobs_sql.py`)
```python
class JobsORM(Base):
    __tablename__ = 'jobs'
    
    job_id = Column(String(ID_LEN), primary_key=True, index=True, default=lambda: str(uuid.uuid4()),
                   comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
    category_id = Column(String(ID_LEN), ForeignKey('job_category.category_id'), index=True)
    job_ref = Column(String(NAME_LEN), unique=True, index=True)
    slug = Column(String(NAME_LEN), unique=True, index=True)
    external_source = Column(String(NAME_LEN))
    
    # Company Relationships
    employer_id = Column(String(ID_LEN), ForeignKey('employers.employer_id'), index=True)
    company_id = Column(String(ID_LEN), ForeignKey('companies.company_id'), index=True)
    
    # Job Details
    title = Column(String(255), index=True)
    description = deferred(Column(Text))
    position_type = Column(String(50), index=True)
    remote_policy = Column(String(50), index=True)
    
    # Compensation
    salary_min = Column(Float)
    salary_max = Column(Float)
    salary_currency = Column(String(3), default="ZAR")
    salary_confidential = Column(Boolean, default=False)
    
    # Location
    city = Column(String(NAME_LEN), index=True)
    province = Column(String(NAME_LEN), index=True)
    country = Column(String(NAME_LEN), index=True)
    geo_location = Column(String(100))
    
    # Timeline
    posted_at = Column(DateTime(timezone=True), default=utc_time, index=True)
    expires_at = Column(DateTime(timezone=True), index=True)
    application_deadline = Column(DateTime(timezone=True))
    
    # Requirements
    experience_level = Column(String(50), index=True)
    education_requirements = Column(JSON, default={})
    required_skills = Column(JSON, default=[])
    preferred_skills = Column(JSON, default=[])
    
    # Required documentations and questionnaire
    required_documents = Column(JSON, default=[])
```

### **Resume & Document Models**

#### **Resume Model** (`src/database/sql/resume.py`)
```python
class JobSeekerCVORM(Base):
    __tablename__ = 'jobseeker_cvs'
    
    cv_id = Column(String(ID_LEN), primary_key=True, unique=True, index=True,
                   comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
    user_uid = Column(ForeignKey('jobseeker_profiles.user_uid'), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    professional_title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    skills = Column(JSON, default=[])
    portfolio_links = Column(JSON, default=[])
    resume_file_url = Column(String(255), nullable=True)
    profile_image_url = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    phone = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    linkedin = Column(String(255), nullable=True)
    github = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_time)
    
    # Relationships
    experience = relationship("ExperienceORM", back_populates="cv", cascade="all, delete-orphan")
    education = relationship("EducationORM", back_populates="cv", cascade="all, delete-orphan")
    certifications = relationship("CertificationORM", back_populates="cv", cascade="all, delete-orphan")
    languages = relationship("LanguageORM", back_populates="cv", cascade="all, delete-orphan")
    projects = relationship("ProjectORM", back_populates="cv", cascade="all, delete-orphan")
    publications = relationship("PublicationORM", back_populates="cv", cascade="all, delete-orphan")
```

### **Billing & Subscription Models**

#### **Billing Models** (`src/database/sql/billing_sql.py`)
```python
class BillingPlanORM(Base):
    __tablename__ = "billing_plan"
    
    plan_id = Column(String(ID_LEN), primary_key=True, index=True,
                     comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    currency = Column(String(10), default="ZAR")
    duration_days = Column(Integer, default=30)
    
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    is_trial = Column(Boolean, default=False)
    
    max_open_jobs = Column(Integer, nullable=True)
    max_users = Column(Integer, nullable=True)
    max_applicants_per_job = Column(Integer, nullable=True)
    
    allow_priority_support = Column(Boolean, default=False)
    show_branding = Column(Boolean, default=True)
    
    sort_order = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    invoices = relationship("InvoiceORM", back_populates="billing_plan")
    billing_profiles = relationship("CompanyBillingProfileORM", back_populates="billing_plan")
```

### **Admin & System Models**

#### **Admin Models** (`src/database/sql/admin_sql.py`)
```python
class AdminORM(Base):
    __tablename__ = 'admin'
    
    admin_id = Column(Integer, primary_key=True, autoincrement=True)
    admin_users = Column(String(ID_LEN), ForeignKey('users.uid'))
    flagged_users = Column(String(ID_LEN), ForeignKey('flagged_users.flag_id'))
```

### **Additional Models**

#### **Agent Session** (`src/database/sql/agent_session.py`)
```python
class AgentSessionORM(Base):
    __tablename__ = "agent_sessions"
    
    session_id = Column(String(ID_LEN), primary_key=True,
                       comment='IMMUTABLE: This ID field is used throughout the system and should NEVER be changed under any circumstances')
    agent_name = Column(String(NAME_LEN), index=True)
    context_data = Column(JSON)
```

## ID Field Usage Patterns

### **System-Wide ID References**
```python
# Cache Keys
f"user:{user_uid}:profile"
f"job:{job_id}:applications"
f"company:{company_id}:jobs"
f"resume:{cv_id}:content"
f"employer:{employer_id}:profile"

# Session Management
session['user_uid'] = user.uid
session['company_id'] = company.company_id
session['employer_id'] = employer.employer_id

# API Endpoints
GET /api/users/{user_uid}/profile
GET /api/jobs/{job_id}/applications
GET /api/companies/{company_id}/jobs
GET /api/employers/{employer_id}/profile

# External Integrations
ats_webhook_url = f"https://ats.company.com/webhook/{company_id}"
payment_reference = f"INV-{plan_id}-{company_id}"

# AI Matching Algorithms
match_cache_key = f"match:job:{job_id}:user:{user_uid}"
```

### **Business Logic Dependencies**
```python
# Job Application Flow
application = JobApplicationORM(
    job_id=job.job_id,                    # References jobs.job_id
    jobseeker_profile_id=profile.user_uid, # References jobseeker_profiles.user_uid
    resume_id=resume.cv_id                 # References jobseeker_cvs.cv_id
)

# User Authentication
user = UserORM.query.get(user_uid)        # Primary lookup by users.uid
profile = JobSeekerProfileORM.query.filter_by(user_uid=user.uid).first()

# Company Operations
company_jobs = JobsORM.query.filter_by(company_id=company.company_id).all()
company_employers = EmployerORM.query.filter_by(company_id=company.company_id).all()

# Billing Operations
billing_plan = BillingPlanORM.query.get(plan_id)
company_billing = CompanyBillingProfileORM.query.filter_by(company_id=company.company_id).first()
```

---

## Database Relationships & Constraints

### **Primary Relationships**
```python
# User → Profile (One-to-One)
UserORM.uid → JobSeekerProfileORM.user_uid
UserORM.uid → EmployerORM.user_uid

# Company → Jobs (One-to-Many)
CompanyORM.jobs → JobsORM.company
CompanyORM.employers → EmployerORM.company

# Job → Applications (One-to-Many)
JobsORM.job_id → JobApplicationORM.job_id
JobsORM.employer_id → EmployerORM.employer_id

# Job Seeker → Applications (One-to-Many)
JobSeekerProfileORM.user_uid → JobApplicationORM.jobseeker_profile_id
JobSeekerProfileORM.user_uid → JobSeekerCVORM.user_uid

# Company → Billing (One-to-Many)
CompanyORM.company_id → CompanyBillingProfileORM.company_id
BillingPlanORM.plan_id → CompanyBillingProfileORM.billing_plan_id
```

### **Foreign Key Constraints**
```sql
-- User relationships
ALTER TABLE jobseeker_profiles ADD CONSTRAINT fk_jobseeker_user 
    FOREIGN KEY (user_uid) REFERENCES users(uid) ON DELETE CASCADE;

ALTER TABLE employers ADD CONSTRAINT fk_employer_user 
    FOREIGN KEY (user_uid) REFERENCES users(uid) ON DELETE CASCADE;

-- Company relationships
ALTER TABLE jobs ADD CONSTRAINT fk_job_company 
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE;

ALTER TABLE employers ADD CONSTRAINT fk_employer_company 
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE;

-- Job relationships
ALTER TABLE job_applications ADD CONSTRAINT fk_application_job 
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE;

ALTER TABLE job_applications ADD CONSTRAINT fk_application_jobseeker 
    FOREIGN KEY (jobseeker_profile_id) REFERENCES jobseeker_profiles(user_uid) ON DELETE CASCADE;

-- Resume relationships
ALTER TABLE jobseeker_cvs ADD CONSTRAINT fk_cv_jobseeker 
    FOREIGN KEY (user_uid) REFERENCES jobseeker_profiles(user_uid) ON DELETE CASCADE;
```

## Database Indexes & Performance

### **Primary Indexes**
```sql
-- User authentication
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_user_type ON users(user_type);
CREATE INDEX idx_users_verified ON users(is_verified);

-- Job search and filtering
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_location ON jobs(location);
CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_posted_date ON jobs(posted_date);
CREATE INDEX idx_jobs_employment_type ON jobs(employment_type);
CREATE INDEX idx_jobs_experience_level ON jobs(experience_level);

-- Application tracking
CREATE INDEX idx_applications_job ON job_applications(job_id);
CREATE INDEX idx_applications_jobseeker ON job_applications(jobseeker_profile_id);
CREATE INDEX idx_applications_status ON job_applications(status);
CREATE INDEX idx_applications_date ON job_applications(application_date);

-- Company search
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_companies_location ON companies(city, province);
CREATE INDEX idx_companies_verified ON companies(is_verified);

-- Resume search
CREATE INDEX idx_resumes_profile ON resumes(jobseeker_profile_id);
CREATE INDEX idx_resumes_current ON resumes(is_current);
CREATE INDEX idx_resumes_skills ON resumes(skills_extracted);
```

### **Composite Indexes**
```sql
-- Job search optimization
CREATE INDEX idx_jobs_search ON jobs(status, location, employment_type, experience_level);

-- Application performance
CREATE INDEX idx_applications_performance ON job_applications(job_id, status, application_date);

-- Company location search
CREATE INDEX idx_companies_location_search ON companies(city, province, country, is_verified);

-- User profile search
CREATE INDEX idx_jobseekers_search ON jobseeker_profiles(location, experience_years, skills);
```

## Data Migration & Schema Evolution

### **Migration Strategy**
```python
# src/database/migrations/
def upgrade():
    # Add new columns
    op.add_column('jobs', sa.Column('ai_score', sa.Float))
    op.add_column('jobs', sa.Column('skills_required', sa.JSON))
    
    # Create new tables
    op.create_table(
        'job_statistics',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('job_id', sa.Integer, sa.ForeignKey('jobs.id')),
        sa.Column('total_views', sa.Integer, default=0),
        sa.Column('total_applications', sa.Integer, default=0),
        sa.Column('avg_match_score', sa.Float),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    
    # Create indexes
    op.create_index('idx_job_statistics_job_date', 'job_statistics', ['job_id', 'date'])
    op.create_index('idx_jobs_ai_score', 'jobs', ['ai_score'])

def downgrade():
    # Remove new columns
    op.drop_column('jobs', 'ai_score')
    op.drop_column('jobs', 'skills_required')
    
    # Drop new tables
    op.drop_table('job_statistics')
    
    # Remove indexes
    op.drop_index('idx_jobs_ai_score', 'jobs')
```

## Data Validation & Constraints

### **Check Constraints**
```sql
-- Salary validation
ALTER TABLE jobs ADD CONSTRAINT chk_salary_range 
    CHECK (salary_min <= salary_max);

-- Date validation
ALTER TABLE jobs ADD CONSTRAINT chk_job_dates 
    CHECK (posted_date <= expiry_date);

-- Status validation
ALTER TABLE job_applications ADD CONSTRAINT chk_application_status 
    CHECK (status IN ('applied', 'reviewing', 'shortlisted', 'interviewing', 'offered', 'rejected'));

-- Email format validation
ALTER TABLE users ADD CONSTRAINT chk_email_format 
    CHECK (email REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
```

### **Unique Constraints**
```sql
-- User email uniqueness
ALTER TABLE users ADD CONSTRAINT uk_users_email UNIQUE (email);

-- Company CIPC number uniqueness
ALTER TABLE companies ADD CONSTRAINT uk_companies_cipc UNIQUE (cipc_number);

-- Invoice number uniqueness
ALTER TABLE invoices ADD CONSTRAINT uk_invoices_number UNIQUE (invoice_number);

-- Job application uniqueness (one application per job per user)
ALTER TABLE job_applications ADD CONSTRAINT uk_application_job_user 
    UNIQUE (job_id, jobseeker_profile_id);
```

## Database Security & Access Control

### **User Permissions**
```sql
-- Create application user
CREATE USER 'jobfinders_app'@'localhost' IDENTIFIED BY 'secure_password';

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON jobfinders.* TO 'jobfinders_app'@'localhost';

-- Restrict administrative operations
REVOKE CREATE, DROP, ALTER, INDEX ON jobfinders.* FROM 'jobfinders_app'@'localhost';

-- Grant specific table permissions
GRANT SELECT ON jobfinders.users TO 'jobfinders_app'@'localhost';
GRANT SELECT, INSERT, UPDATE ON jobfinders.jobs TO 'jobfinders_app'@'localhost';
```

### **Data Encryption**
```sql
-- Encrypt sensitive columns
ALTER TABLE users MODIFY password_hash VARBINARY(255);
ALTER TABLE users MODIFY phone VARBINARY(255);

-- Enable encryption at rest
ALTER TABLE users ENCRYPTION='Y';
ALTER TABLE companies ENCRYPTION='Y';
ALTER TABLE job_applications ENCRYPTION='Y';
```

## Backup & Recovery Strategy

### **Backup Schedule**
```bash
#!/bin/bash
# Daily backup script

# Full database backup
mysqldump --single-transaction --routines --triggers \
    --user=backup_user --password=backup_password \
    jobfinders > /backups/jobfinders_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip /backups/jobfinders_$(date +%Y%m%d_%H%M%S).sql

# Keep only last 30 days of backups
find /backups -name "*.sql.gz" -mtime +30 -delete
```

### **Recovery Procedures**
```sql
-- Point-in-time recovery
RESTORE DATABASE jobfinders FROM 'backup_file.sql';

-- Restore specific tables
RESTORE TABLE users, companies FROM 'backup_file.sql';

-- Verify data integrity
CHECK TABLE users, companies, jobs;
REPAIR TABLE users, companies, jobs;
```

## ID Field Maintenance & Best Practices

### **Development Guidelines**
```python
# ✅ CORRECT: Always use ID fields as immutable references
def get_user_profile(user_uid: str):
    return UserORM.query.get(user_uid)  # Use UID directly

def get_company_jobs(company_id: str):
    return JobsORM.query.filter_by(company_id=company_id).all()

def get_employer_profile(employer_id: str):
    return EmployerORM.query.get(employer_id)  # Use employer_id directly

# ❌ WRONG: Never modify ID values
def update_user_uid(user, new_uid):  # DANGEROUS!
    user.uid = new_uid  # This will break the entire system!
    db.session.commit()

# ❌ WRONG: Never delete and recreate with same ID
def recreate_user(user_uid: str):  # DANGEROUS!
    user = UserORM.query.get(user_uid)
    db.session.delete(user)
    db.session.commit()
    
    new_user = UserORM(uid=user_uid, ...)  # This will cause conflicts!
    db.session.add(new_user)
    db.session.commit()
```

### **Migration Safety**
```python
# ✅ SAFE: Add new columns, never modify existing IDs
def upgrade():
    # Safe operations
    op.add_column('users', sa.Column('new_field', sa.String(255)))
    op.create_index('idx_users_new_field', 'users', ['new_field'])
    
    # ❌ NEVER DO: Modify existing ID columns
    # op.alter_column('users', 'id', ...)  # DANGEROUS!
    # op.drop_column('users', 'id')        # DANGEROUS!
    # op.rename_column('users', 'id', 'new_id')  # DANGEROUS!

def downgrade():
    # Safe rollback
    op.drop_index('idx_users_new_field', 'users')
    op.drop_column('users', 'new_field')
```

### **Testing & Validation**
```python
# Test ID field immutability
def test_id_field_immutability():
    user = UserORM(email="test@example.com", ...)
    original_uid = user.uid
    
    # Verify UID cannot be changed
    with pytest.raises(Exception):
        user.uid = "new-uuid-string"  # Should fail
    
    # Verify UID remains consistent
    assert user.uid == original_uid
    
    # Verify UID is used in relationships
    profile = JobSeekerProfileORM(user_uid=user.uid, ...)
    assert profile.user_uid == user.uid

def test_uuid_format_validation():
    # Verify UUID format is correct
    user = UserORM.query.get("test-uid")
    assert len(user.uid) == ID_LEN  # Should be 64 characters
    assert user.uid.isalnum() or '-' in user.uid  # Valid UUID format
```

---

## Performance Monitoring & Optimization

### **Query Performance Analysis**
```sql
-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- Analyze slow queries
SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;

-- Check table performance
SHOW TABLE STATUS LIKE 'jobs';
SHOW INDEX FROM jobs;
```

### **Database Optimization**
```sql
-- Optimize tables
OPTIMIZE TABLE users, companies, jobs, job_applications;

-- Analyze table statistics
ANALYZE TABLE users, companies, jobs, job_applications;

-- Update table statistics
UPDATE TABLE_STATISTICS SET last_updated = NOW();
```

This database specification provides a comprehensive framework for the Job Finders data architecture, ensuring data integrity, performance, and scalability while supporting the complex business logic and AI-powered features of the platform.
