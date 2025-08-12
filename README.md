# JobFinders.site

**South Africa's Premier Job Search Platform**

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.3.2-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

JobFinders.site is a comprehensive job search and recruitment platform designed specifically for the South African job market. The platform connects job seekers with employers through advanced job matching, ATS integration, and comprehensive career management tools.

## 🌟 Features

### For Job Seekers
- **Advanced Job Search**: Search jobs by keywords, location, salary, and industry
- **Profile Management**: Create detailed professional profiles with skills and experience
- **CV Builder & Management**: Upload, edit, and optimize CVs with ATS scoring
- **Job Applications**: Apply directly to jobs with cover letter customization
- **Job Alerts**: Get notified about relevant job opportunities via email
- **Application Tracking**: Monitor application status and employer responses
- **ATS Resume Checker**: Optimize resumes for Applicant Tracking Systems
- **Career Resources**: Access blog content and career development materials

### For Employers
- **Company Profiles**: Create comprehensive company profiles with verification
- **Job Posting**: Post jobs with AI-enhanced descriptions
- **Candidate Management**: Browse and manage job applications
- **ATS Integration**: Built-in Applicant Tracking System functionality
- **Analytics Dashboard**: Track job performance and candidate metrics
- **Billing Management**: Flexible subscription plans and billing
- **Document Verification**: CIPC registration and company verification
- **Candidate Matching**: AI-powered candidate recommendation system

### Platform Features
- **Multi-Source Job Aggregation**: Scrapes jobs from major SA job boards
- **SEO Optimized**: Dynamic SEO for better search engine visibility
- **Responsive Design**: Mobile-friendly interface
- **Email Notifications**: Automated email system for alerts and updates
- **Admin Dashboard**: Comprehensive administrative controls
- **Performance Monitoring**: Built-in monitoring and analytics

## 🏗️ Architecture

### Technology Stack
- **Backend**: Python 3.8+ with Flask framework
- **Database**: MySQL with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript with Bootstrap
- **Job Scraping**: Custom scrapers for Career24, PNet, Indeed, CareerJunction
- **Email**: Integrated email system for notifications
- **Caching**: Redis for performance optimization
- **Task Queue**: Celery for background job processing

### Project Structure
```
jobfinders/
├── src/                    # Core application code
│   ├── controllers/        # Business logic controllers
│   ├── database/          # Database models and migrations
│   ├── routes/            # Flask route definitions
│   ├── scrappers/         # Job scraping modules
│   ├── utils/             # Utility functions
│   ├── config/            # Configuration management
│   └── main/              # Application factory
├── template/              # Jinja2 templates
│   ├── jobseekers/        # Job seeker interfaces
│   ├── company/           # Employer interfaces
│   ├── admin/             # Admin dashboard
│   ├── jobs/              # Job listing pages
│   ├── ats/               # ATS tools
│   └── layouts/           # Base templates
├── static/                # CSS, JS, images
├── requirements.txt       # Python dependencies
└── app.py                # Application entry point
```

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- MySQL 5.7+ or MariaDB
- Redis (for caching)
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/jobfinders-site/jobfinders.git
   cd jobfinders
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=mysql://username:password@localhost/jobfinders
   REDIS_URL=redis://localhost:6379/0
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

5. **Database Setup**
   ```bash
   # Create database
   mysql -u root -p -e "CREATE DATABASE jobfinders;"
   
   # Run migrations (if using Flask-Migrate)
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Start the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   Open your browser and navigate to `http://localhost:8084`

### Production Deployment

For production deployment, consider:
- Using Gunicorn or uWSGI as the WSGI server
- Nginx as a reverse proxy
- SSL certificate configuration
- Environment-specific configuration files
- Database connection pooling
- Redis configuration for caching

## 📖 Usage

### Job Seekers
1. **Register**: Create an account with email verification
2. **Profile Setup**: Complete your professional profile
3. **Upload CV**: Add your resume and get ATS scoring
4. **Job Search**: Browse jobs or set up job alerts
5. **Apply**: Submit applications with customized cover letters
6. **Track**: Monitor your application status

### Employers
1. **Company Registration**: Create and verify your company profile
2. **Subscription**: Choose an appropriate billing plan
3. **Post Jobs**: Create job listings with AI assistance
4. **Manage Applications**: Review and respond to candidates
5. **Analytics**: Track job performance and hiring metrics

### Administrators
- Access admin dashboard at `/admin`
- Monitor system performance and health
- Manage users, companies, and job listings
- Configure system settings and billing plans

## 🔧 Configuration

### Environment Variables
```env
# Application
SECRET_KEY=your-secret-key
DEBUG=False
BASE_URL=https://jobfinders.site

# Database
DATABASE_URL=mysql://user:pass@host:port/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@domain.com
MAIL_PASSWORD=your-password

# External APIs
PAYFAST_MERCHANT_ID=your-merchant-id
PAYFAST_MERCHANT_KEY=your-merchant-key
```

### Database Configuration
The application uses SQLAlchemy with MySQL. Configure your database connection in `src/config/config.py`.

## 🧪 Testing

Run the test suite:
```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest

# Run with coverage
pytest --cov=src
```

## 📊 Monitoring

The application includes built-in monitoring for:
- Job scraping performance
- Application response times
- Database query performance
- Email delivery status
- User engagement metrics

Access monitoring dashboards through the admin interface.

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting PR

## 🔒 Security

- User authentication with session management
- Password hashing with secure algorithms
- CSRF protection on forms
- Input validation and sanitization
- SQL injection prevention through ORM
- XSS protection in templates

Report security vulnerabilities to: security@jobfinders.site

## 📄 API Documentation

### Job Search API
```
GET /api/jobs?search=python&location=cape-town
```

### User Authentication
```
POST /api/auth/login
POST /api/auth/register
```

### Job Applications
```
POST /api/applications
GET /api/applications/{id}
```

Full API documentation available at `/api/docs` when running the application.

## 🚀 Deployment

### Using Docker
```bash
# Build image
docker build -t jobfinders .

# Run container
docker run -p 8084:8084 jobfinders
```

### Using Docker Compose
```bash
docker-compose up -d
```

## 📈 Performance

- Database query optimization with indexes
- Redis caching for frequently accessed data
- Lazy loading for large datasets
- CDN integration for static assets
- Background job processing with Celery

## 🐛 Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check MySQL service
sudo systemctl status mysql

# Verify connection
mysql -u username -p -h hostname
```

**Job Scraping Issues**
- Check scraper logs in `logs/scraper.log`
- Verify external site accessibility
- Review rate limiting settings

**Email Delivery Problems**
- Verify SMTP credentials
- Check spam filters
- Monitor email delivery logs

## 📞 Support

- **Documentation**: [docs.jobfinders.site](https://docs.jobfinders.site)
- **Email**: support@jobfinders.site
- **Issues**: [GitHub Issues](https://github.com/jobfinders-site/jobfinders/issues)

## 📜 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Flask community for the excellent web framework
- Bootstrap for responsive UI components
- Contributors and beta testers
- South African job boards for data partnerships

---

**Made with ❤️ for the South African job market**

*Last updated: January 2025* 
