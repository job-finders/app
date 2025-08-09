# Technology Stack

## Backend Framework
- **Flask 3.1.0**: Python web framework with blueprint-based routing
- **SQLAlchemy 2.0.40**: ORM with MySQL database backend
- **Pydantic 2.11.4**: Data validation and settings management
- **PyMySQL 1.1.1**: MySQL database connector

## Frontend & Styling
- **Jinja2 Templates**: Server-side rendering with custom filters
- **CSS3**: Modern CSS with CSS variables and flexbox/grid layouts
- **JavaScript**: Vanilla JS with modular organization
- **FontAwesome**: Icon library for UI elements

## AI & Machine Learning
- **spaCy 3.8.5**: NLP for job matching and text analysis
- **scikit-learn 1.6.1**: Machine learning algorithms for matching
- **OpenRouter API**: LLM integration for AI agents

## Data Processing
- **BeautifulSoup4**: Web scraping for job aggregation
- **requests-cache**: HTTP caching for scraper optimization
- **Levenshtein**: String similarity matching

## Infrastructure
- **Redis**: Caching and session management
- **APScheduler**: Background task scheduling
- **Resend**: Email service integration
- **PayFast**: Payment processing for South African market

## Security & Monitoring
- **Flask-Bcrypt**: Password hashing
- **Custom Firewall**: Rate limiting, CSRF protection, security headers
- **Logging**: Comprehensive security and application logging

## Common Commands

### Development
```bash
# Start development server
python app.py

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Database migrations (manual via boot.py)
python -c "from src.main.boot import boot; boot()"
```

### Production
```bash
# Run with gunicorn (recommended)
gunicorn -w 4 -b 0.0.0.0:8084 app:app

# Environment setup
cp .env.developer.example .env.developer
# Edit .env.developer with your configuration
```

### Cache Management
```bash
# Clear Redis cache
redis-cli FLUSHALL

# Clear file cache
rm -rf cache/*
rm -rf backup_cache/*
```