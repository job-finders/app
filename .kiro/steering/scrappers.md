# Scrappers Steering File

## Overview
The `src/scrappers/` module handles automated job data collection from major South African job sites. This system provides the foundation for Job Finders' comprehensive job aggregation service.

## Target Job Sites
- **Career24** - Primary SA job board
- **PNet** - Professional network jobs
- **Indeed** - International with SA listings
- **Career Junction** - Enterprise-focused positions

## Core Principles

### 1. Respectful Scraping
```python
# Minimum delay between requests (milliseconds)
MIN_REQUEST_DELAY = 2000  # 2 seconds
MAX_REQUEST_DELAY = 5000  # 5 seconds

# Maximum concurrent requests per site
MAX_CONCURRENT_REQUESTS = 2

# Respectful user agent identification
USER_AGENT = "JobFinders-Bot/1.0 (South African job aggregator; contact@jobfinders.co.za)"
```

### 2. Error Handling & Recovery
- **Graceful degradation**: Continue scraping other sites if one fails
- **CAPTCHA detection**: Pause scraping and alert monitoring system
- **Rate limit compliance**: Back-off strategies with exponential delays
- **Data integrity**: Validate all scraped fields before storage

### 3. Data Consistency
All scrapers must extract standardized fields:
```python
class JobData:
    title: str
    company: str
    location: str
    description: str
    salary: Optional[str]
    job_type: str  # "Full-time", "Part-time", "Contract", "Internship"
    posted_date: datetime
    external_id: str  # Original job ID from source site
    source_url: str
    source_site: str  # "career24", "pnet", "indeed", "careerjunction"
```

## File Structure
```
src/scrappers/
├── __init__.py
├── base_scraper.py          # Abstract base class for all scrapers
├── career24_scraper.py      # Career24.com scraper
├── pnet_scraper.py          # PNet.co.za scraper  
├── indeed_scraper.py        # Indeed.co.za scraper
├── career_junction_scraper.py # CareerJunction.co.za scraper
├── scraper_factory.py       # Factory for creating scraper instances
├── data_validator.py        # Job data validation utilities
└── utils/
    ├── selenium_utils.py    # Selenium WebDriver utilities
    ├── requests_utils.py    # HTTP client with retries
    ├── parsing_utils.py     # HTML parsing helpers
    └── cache_utils.py       # Scraping cache management
```

## Base Scraper Pattern

### Abstract Base Class
```python
from abc import ABC, abstractmethod
from typing import List, Generator
import time
import random

class BaseScraper(ABC):
    def __init__(self):
        self.session = self._create_session()
        self.delay_range = (MIN_REQUEST_DELAY, MAX_REQUEST_DELAY)
        
    @abstractmethod
    def get_job_urls(self, search_term: str, location: str) -> List[str]:
        """Extract job URLs from search results"""
        pass
        
    @abstractmethod  
    def scrape_job(self, job_url: str) -> JobData:
        """Extract job details from individual job page"""
        pass
        
    def scrape_jobs(self, search_terms: List[str], locations: List[str]) -> Generator[JobData, None, None]:
        """Main scraping orchestrator with rate limiting"""
        for term in search_terms:
            for location in locations:
                urls = self.get_job_urls(term, location)
                for url in urls:
                    try:
                        job_data = self.scrape_job(url)
                        yield job_data
                        self._respectful_delay()
                    except Exception as e:
                        self._handle_scraping_error(e, url)
    
    def _respectful_delay(self):
        """Implement random delay between requests"""
        delay = random.uniform(*self.delay_range) / 1000
        time.sleep(delay)
```

## Site-Specific Implementation Guidelines

### Career24 Scraper
```python
class Career24Scraper(BaseScraper):
    BASE_URL = "https://www.career24.com"
    SEARCH_URL = f"{BASE_URL}/jobs"
    
    def get_job_urls(self, search_term: str, location: str) -> List[str]:
        # Use search filters: ?keywords={term}&location={location}
        # Parse pagination: look for "Next" buttons
        # Extract job URLs from search result listings
        pass
        
    def scrape_job(self, job_url: str) -> JobData:
        # Parse job title from <h1> or equivalent
        # Extract company name, location, description
        # Handle salary parsing (often in various formats)
        # Parse posting date (may need date format conversion)
        pass
```

### PNet Scraper Considerations
- Often requires JavaScript execution (use Selenium)
- May have different pagination patterns
- Salary information often in different formats

### Indeed Scraper Notes  
- Well-structured HTML, easier to parse
- Good pagination support
- Rate limiting is more aggressive - use longer delays

## Caching Strategy

### Cache Structure
```
cache/
├── career24/
│   ├── search_results_2025-01-15.json
│   └── job_details_2025-01-15.json
├── pnet/
├── indeed/
└── career_junction/
```

### Cache Implementation
```python
class ScrapingCache:
    def __init__(self, cache_dir: str = "cache/"):
        self.cache_dir = Path(cache_dir)
        
    def cache_search_results(self, site: str, search_key: str, results: List[str]):
        """Cache job URLs from search results"""
        pass
        
    def cache_job_data(self, site: str, job_data: JobData):
        """Cache individual job details"""
        pass
        
    def get_cached_job_urls(self, site: str, search_key: str) -> Optional[List[str]]:
        """Retrieve cached search results (24-hour TTL)"""
        pass
```

## Data Validation

### Required Field Validation
```python
class JobDataValidator:
    REQUIRED_FIELDS = ['title', 'company', 'location', 'description', 'source_url']
    
    @staticmethod
    def validate_job_data(job_data: JobData) -> bool:
        """Ensure all required fields are present and valid"""
        for field in JobDataValidator.REQUIRED_FIELDS:
            if not getattr(job_data, field, None):
                return False
        return True
        
    @staticmethod
    def normalize_job_type(job_type_raw: str) -> str:
        """Standardize job type classifications"""
        # Map various formats to: "Full-time", "Part-time", "Contract", "Internship"
        pass
```

## Error Handling Patterns

### Common Error Scenarios
1. **CAPTCHA Encountered**
   ```python
   def _handle_captcha(self, response):
       logger.warning(f"CAPTCHA detected on {self.site_name}")
       # Pause scraping for this site
       # Send alert to monitoring system
       raise CaptchaDetectedError("Manual intervention required")
   ```

2. **Rate Limiting**
   ```python
   def _handle_rate_limit(self, response):
       if response.status_code == 429:
           retry_after = response.headers.get('Retry-After', 300)
           logger.info(f"Rate limited. Waiting {retry_after} seconds")
           time.sleep(int(retry_after))
   ```

3. **Page Structure Changes**
   ```python
   def _validate_page_structure(self, soup):
       expected_selectors = ['.job-title', '.company-name', '.job-description']
       for selector in expected_selectors:
           if not soup.select(selector):
               raise PageStructureChangedError(f"Missing selector: {selector}")
   ```

## Task Integration

### Scheduled Scraping
```python
# Integration with src/tasks/ background job system
from src.tasks import schedule_job

@schedule_job(cron="0 */6 * * *")  # Every 6 hours
def run_all_scrapers():
    """Orchestrate scraping across all job sites"""
    search_terms = get_popular_search_terms()
    locations = get_south_african_cities()
    
    for scraper_class in [Career24Scraper, PNetScraper, IndeedScraper]:
        scraper = scraper_class()
        jobs = scraper.scrape_jobs(search_terms, locations)
        for job in jobs:
            if JobDataValidator.validate_job_data(job):
                save_to_database(job)
```

## Monitoring & Alerts

### Key Metrics to Track
- Jobs scraped per hour per site
- Error rates by site
- CAPTCHA encounters
- Cache hit/miss ratios
- Data quality scores

### Alert Conditions
- Zero jobs scraped from any site for 2+ hours
- Error rate > 20% for any scraper
- CAPTCHA detection
- Significant drop in job volume compared to historical average

## Configuration

### Environment Variables
```env
# Scraping Configuration
SCRAPING_ENABLED=true
SCRAPING_DELAY_MIN=2000
SCRAPING_DELAY_MAX=5000
SCRAPING_MAX_CONCURRENT=2

# Site-specific toggles
CAREER24_ENABLED=true
PNET_ENABLED=true
INDEED_ENABLED=true
CAREER_JUNCTION_ENABLED=true

# Cache settings
SCRAPING_CACHE_TTL=86400  # 24 hours
SCRAPING_CACHE_DIR=cache/
```

## Legal & Compliance

### robots.txt Compliance
- Always check and respect robots.txt files
- Implement robots.txt parser before scraping any site
- Document any sites that explicitly disallow scraping

### Data Usage Rights
- Only scrape publicly available job postings
- Respect copyright on job descriptions
- Attribute job sources appropriately in the Job Finders platform
- Implement takedown procedures for employer requests

## Testing Strategy

### Unit Tests
```python
def test_career24_job_parsing():
    """Test job data extraction from Career24 HTML"""
    html = load_test_fixture('career24_job_sample.html')
    scraper = Career24Scraper()
    job_data = scraper.parse_job_html(html)
    
    assert job_data.title == "Software Developer"
    assert job_data.company == "TechCorp"
    assert job_data.source_site == "career24"
```

### Integration Tests
```python
def test_end_to_end_scraping():
    """Test complete scraping workflow with real sites (using test data)"""
    # Use staging/test endpoints when available
    # Validate complete data pipeline from scrape to database
```

This steering file establishes the foundation for reliable, respectful, and maintainable job scraping operations that align with Job Finders' business requirements and technical standards.