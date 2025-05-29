import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
import uuid  # Added for UUID generation

from bs4 import BeautifulSoup
from pydantic import HttpUrl, ValidationError
from requests_cache import CachedSession

# Import your models
from src.database.models.jobs_model import Company, Job, JobStatusEnum
from src.logger import init_logger
from src.main import companies_controller, jobs_controller


class ScrapedCompanyDTO:
    """
    Data Transfer Object (DTO) for holding scraped company information.
    Acts as an intermediate representation before conversion to the Company model.
    
    Attributes:
        name (str): Company name (required)
        logo_url (Optional[HttpUrl]): URL to company logo
        industry (Optional[str]): Industry sector the company operates in
        website (Optional[HttpUrl]): Company website URL
    """
    def __init__(self, 
                 name: str, 
                 logo_url: Optional[HttpUrl] = None,
                 industry: Optional[str] = None,
                 website: Optional[HttpUrl] = None):
        self.name = name
        self.logo_url = logo_url
        self.industry = industry
        self.website = website


class ScrapedJobDTO:
    """
    Data Transfer Object (DTO) for holding scraped job information.
    Acts as an intermediate representation before conversion to the Job model.
    
    Attributes:
        source_id (str): Unique identifier from the source platform
        title (str): Job title
        description (str): Full job description
        company (ScrapedCompanyDTO): Company DTO associated with the job
        job_url (HttpUrl): URL to the job posting
        salary_text (str): Raw salary information text
        location (str): Job location string
        position_type (str): Employment type (e.g., Full-time, Part-time)
        expires (str): Expiration date text
        skills (List[str]): List of required skills
        external_source (str): Source platform name (default: "careerjunction")
    """
    def __init__(self,
                 source_id: str,
                 title: str,
                 description: str,
                 company: ScrapedCompanyDTO,
                 job_url: HttpUrl,
                 salary_text: str,
                 location: str,
                 position_type: str,
                 expires: str,
                 skills: List[str],
                 external_source: str = "careerjunction"):
        self.source_id = source_id
        self.title = title
        self.description = description
        self.company = company
        self.job_url = job_url
        self.salary_text = salary_text
        self.location = location
        self.position_type = position_type
        self.expires = expires
        self.skills = skills
        self.external_source = external_source


class Scraper:
    """
    Base scraper class providing core functionality for web scraping jobs.
    Implements caching, HTTP requests, and data transformation using DTO pattern.
    
    Attributes:
        search_terms (List[str]): Job categories to scrape
        headers (Dict[str, str]): HTTP headers for requests
        request_session (CachedSession): Cached HTTP session
        logger: Logger instance
        job_cache (Dict[str, Job]): In-memory cache of Job objects
        company_cache (Dict[str, Company]): In-memory cache of Company objects
    """
    
    def __init__(self):
        # Job categories to scrape
        self.search_terms = [
            'information-technology', 'office-admin', 'agriculture',
            'engineering', 'building-construction', 'business-management',
            'cleaning-maintenance', 'community-social-welfare', 'education',
            'nursing', 'finance', 'programming'
        ]
        
        # HTTP headers to mimic browser behavior
        self.headers: dict[str, str] = {
            'user-agent': "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)",
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Accept': '*/*'
        }

        # Configure cached HTTP session
        self.request_session = CachedSession(
            'jobs_cache',
            expire_after=timedelta(hours=24),  # Cache duration
            allowable_codes=[200, 400],        # Status codes to cache
            allowable_methods=['GET'],          # HTTP methods to cache
            stale_if_error=True                 # Use cache on request errors
        )
        self.logger = init_logger(self.__class__.__name__)
        
        # Initialize in-memory caches
        self.job_cache: Dict[str, Job] = {}
        self.company_cache: Dict[str, Company] = {}

    async def update_cache(self) -> None:
        """
        Refresh in-memory caches from database.
        Loads all jobs and companies into memory for quick access.
        """
        self.job_cache.clear()
        self.company_cache.clear()
        
        # Load all jobs from database
        jobs = await jobs_controller.get_all_jobs()
        for job in jobs:
            # Cache jobs by reference ID
            self.job_cache[job.job_ref] = job
        
        # Load all companies from database
        companies = await companies_controller.get_all_companies()
        for company in companies:
            # Cache companies by normalized name
            self.company_cache[company.name.lower()] = company

    async def fetch_url(self, url: str) -> Optional[bytes]:
        """
        Fetch URL content with caching and error handling.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response content as bytes or None if request fails
        """
        try:
            # Make HTTP GET request with timeout
            response = self.request_session.get(
                url, 
                headers=self.headers,
                timeout=10  # 10-second timeout
            )
            # Raise exception for HTTP errors
            response.raise_for_status()
            return response.content
        except Exception as e:
            self.logger.error(f"Request failed for {url}: {str(e)}")
            return None

    async def find_or_create_company(self, dto: ScrapedCompanyDTO) -> Company:
        """
        Find existing company or create new one from DTO.
        Checks cache and database before creating new company.
        
        Args:
            dto: ScrapedCompanyDTO with company information
            
        Returns:
            Company instance (existing or newly created)
        """
        # Normalize name for cache key
        cache_key = dto.name.lower()
        
        # Check in-memory cache first
        if cache_key in self.company_cache:
            return self.company_cache[cache_key]
        
        # Check database if not in cache
        existing = await companies_controller.get_company_by_name(dto.name)
        if existing:
            # Add to cache for future access
            self.company_cache[cache_key] = existing
            return existing
        
        # Create new company with minimal validation
        new_company = Company(
            company_id=str(uuid.uuid4()),  # Generate unique ID
            name=dto.name,
            logo_url=dto.logo_url,
            industry=dto.industry,
            website=dto.website,
            is_verified=False  # Scraped companies are not verified
        )
        
        # Save to database
        created = await companies_controller.create_company(new_company)
        # Add to cache for future access
        self.company_cache[cache_key] = created
        return created

    def parse_salary(self, salary_text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Parse salary range from text.
        Handles various formats like "R20,000 - R30,000" or "R50000".
        
        Args:
            salary_text: Raw salary string from source
            
        Returns:
            Tuple of (min_salary, max_salary) or (None, None) if unparseable
        """
        try:
            # Extract all numeric values preceded by 'R'
            numbers = re.findall(r'R\s*([\d,]+)', salary_text)
            if not numbers:
                return None, None
                
            # Convert to floats (remove commas)
            salaries = [float(num.replace(',', '')) for num in numbers]
            
            # Handle single value vs range
            if len(salaries) == 1:
                return salaries[0], salaries[0]  # min = max
            return min(salaries), max(salaries)  # min and max
        except Exception:
            return None, None

    def parse_location(self, location: str) -> Tuple[str, str, str]:
        """
        Parse location string into city, province, and country components.
        Uses simple comma-based splitting with fallbacks.
        
        Args:
            location: Raw location string from source
            
        Returns:
            Tuple of (city, province, country)
        """
        # Split and clean parts
        parts = [p.strip() for p in location.split(',') if p.strip()]
        
        # Handle different part counts with fallbacks
        if len(parts) == 0:
            return "Unknown", "Unknown", "South Africa"
        if len(parts) == 1:
            return parts[0], "Unknown", "South Africa"
        if len(parts) == 2:
            return parts[0], parts[1], "South Africa"
        return parts[0], parts[1], parts[2]

    def parse_expiry(self, expires_text: str) -> datetime:
        """
        Parse expiration date text into datetime object.
        Tries multiple formats before falling back to 30 days from now.
        
        Args:
            expires_text: Raw expiration date string
            
        Returns:
            Parsed datetime or 30 days from now as fallback
        """
        try:
            # Try common date formats
            for fmt in ("%d %B %Y", "%d/%m/%Y", "%Y-%m-%d"):  # e.g., "15 January 2023"
                try:
                    return datetime.strptime(expires_text, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        # Fallback: 30 days from current time
        return datetime.utcnow() + timedelta(days=30)

    def convert_to_job_model(self, dto: ScrapedJobDTO, company: Company) -> Job:
        """
        Convert ScrapedJobDTO to validated Job model.
        Applies business rules and fallbacks for missing data.
        
        Args:
            dto: ScrapedJobDTO with job information
            company: Associated Company model instance
            
        Returns:
            Validated Job model instance
        """
        # Parse salary and location
        salary_min, salary_max = self.parse_salary(dto.salary_text)
        city, province, country = self.parse_location(dto.location)
        
        # Determine position type from text
        position_type = "FULL_TIME"
        lower_position = dto.position_type.lower()
        if "part" in lower_position:
            position_type = "PART_TIME"
        elif "contract" in lower_position:
            position_type = "CONTRACT"
        
        # Determine experience level from text
        experience_level = "MID"
        if "junior" in lower_position or "entry" in lower_position:
            experience_level = "ENTRY"
        elif "senior" in lower_position:
            experience_level = "SENIOR"
        
        # Create and return Job model instance
        return Job(
            job_id=str(uuid.uuid4()),  # Generate unique ID
            job_ref=dto.source_id,
            external_source=dto.external_source,
            company_id=company.company_id,
            title=dto.title,
            description=dto.description,
            position_type=position_type,
            remote_policy="ONSITE",  # Default assumption
            category=dto.external_source,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency="ZAR",  # Default to South African Rand
            salary_confidential=salary_min is None,  # Confidential if no salary
            city=city,
            province=province,
            country=country,
            posted_at=datetime.utcnow(),  # Use current time as posted
            expires_at=self.parse_expiry(dto.expires),
            experience_level=experience_level,
            required_skills=dto.skills,
            application_url=dto.job_url,
            application_instructions=f"Apply via {dto.external_source}",
            required_questionnaire=[],
            status=JobStatusEnum.ACTIVE.value  # Default to active status
        )


class JunctionScraper(Scraper):
    """
    CareerJunction-specific scraper implementation.
    Extends base Scraper with platform-specific extraction logic.
    
    Attributes:
        BASE_URL (str): CareerJunction base URL
        JOBS_PATH (str): Path segment for job listings
        semaphore (asyncio.Semaphore): Concurrency limiter
    """
    
    BASE_URL = "https://www.careerjunction.co.za"
    JOBS_PATH = "/jobs/"

    def __init__(self):
        super().__init__()
        # Limit concurrent requests to 10
        self.semaphore = asyncio.Semaphore(10)

    async def scrape_and_store_jobs(self) -> None:
        """
        Main scraping workflow: 
        1. Updates caches
        2. Processes each search term
        3. Scrapes jobs for each term
        4. Creates companies and jobs in database
        """
        # Refresh from database
        await self.update_cache()
        
        # Process each job category
        for term in self.search_terms:
            self.logger.info(f"Scraping term: {term}")
            # Scrape job DTOs for this category
            job_dtos = await self.scrape_term_jobs(term)
            
            # Process each scraped job
            for dto in job_dtos:
                # Find or create associated company
                company = await self.find_or_create_company(dto.company)
                
                # Convert to Job model
                job_model = self.convert_to_job_model(dto, company)
                
                # Check if job already exists
                existing = await jobs_controller.get_job_by_reference(job_model.job_ref)
                if not existing:
                    # Create new job in database
                    await jobs_controller.create_job(job_model)
            
            self.logger.info(f"Processed {len(job_dtos)} jobs for {term}")

    async def scrape_term_jobs(self, term: str, max_pages: int = 5) -> List[ScrapedJobDTO]:
        """
        Scrape all jobs for a specific search term.
        
        Args:
            term: Job category to scrape
            max_pages: Maximum number of listing pages to process
            
        Returns:
            List of ScrapedJobDTO objects
        """
        # Generate listing page URLs
        listing_urls = [
            f"{self.BASE_URL}{self.JOBS_PATH}{term}?page={page}"
            for page in range(1, max_pages + 1)
        ]
        
        # Process all listing pages concurrently
        all_jobs = []
        results = await asyncio.gather(*[
            self.process_listing_page(url, term)
            for url in listing_urls
        ])
        
        # Flatten results
        for jobs in results:
            all_jobs.extend(jobs)
            
        return all_jobs

    async def process_listing_page(self, url: str, term: str) -> List[ScrapedJobDTO]:
        """
        Process a single listing page and extract job previews.
        
        Args:
            url: Listing page URL
            term: Current search term
            
        Returns:
            List of ScrapedJobDTO objects from this page
        """
        # Limit concurrency with semaphore
        async with self.semaphore:
            # Fetch page content
            content = await self.fetch_url(url)
            if not content:
                return []
            
            # Parse HTML
            soup = BeautifulSoup(content, "html.parser")
            # Find all job elements on page
            job_elements = soup.find_all("div", class_="job-result")
            
            # Process each job element concurrently
            return await asyncio.gather(*[
                self.extract_job_dto(element, term)
                for element in job_elements
            ])

    async def extract_job_dto(self, element, term: str) -> Optional[ScrapedJobDTO]:
        """
        Extract job DTO from a listing element.
        
        Args:
            element: BeautifulSoup element containing job preview
            term: Current search term
            
        Returns:
            ScrapedJobDTO or None if extraction fails
        """
        try:
            # Extract detail page URL
            detail_path = element.find("a", class_="show-more")["href"].strip("/")
            detail_url = urljoin(self.BASE_URL, detail_path)
            
            # Fetch detail page
            content = await self.fetch_url(detail_url)
            if not content:
                return None
                
            # Parse detail page
            soup = BeautifulSoup(content, "html.parser")
            # Extract full job details
            return self.parse_job_page(soup, detail_url, term)
        except (TypeError, KeyError, AttributeError) as e:
            self.logger.error(f"Element parsing error: {str(e)}")
            return None

    def parse_job_page(self, soup: BeautifulSoup, url: str, term: str) -> Optional[ScrapedJobDTO]:
        """
        Parse detailed job page into ScrapedJobDTO.
        
        Args:
            soup: BeautifulSoup instance of job detail page
            url: Job detail URL
            term: Current search term
            
        Returns:
            ScrapedJobDTO or None if parsing fails
        """
        # Find main job description container
        container = soup.find("div", class_="job-description")
        if not container:
            return None
            
        # --- Extract company information ---
        company_name = container.find("h2").text.strip()
        logo_elem = container.find("img")
        # Build absolute URL for logo
        logo_url = urljoin(self.BASE_URL, logo_elem["src"]) if logo_elem else None
        
        # Create company DTO
        company_dto = ScrapedCompanyDTO(
            name=company_name,
            logo_url=logo_url
        )
        
        # --- Extract job information ---
        # Find various job attributes
        salary_elem = container.find("li", class_="salary")
        location_elem = container.find("li", class_="location")
        position_elem = container.find("li", class_="position")
        expires_elem = container.find("li", class_="expires")
        ref_elem = container.find("li", class_="cjun-job-ref")
        
        # --- Extract skills ---
        skills_container = soup.find("div", class_="job-desc-on-expired")
        skills = []
        if skills_container:
            try:
                # First unordered list is assumed to be skills
                skills_list = skills_container.find_all("ul")[0]
                skills = [li.text.strip() for li in skills_list.find_all("li")]
            except (IndexError, AttributeError):
                pass
        
        # Create and return job DTO
        return ScrapedJobDTO(
            source_id=ref_elem.text.strip() if ref_elem else str(uuid.uuid4()),
            title=container.find("h1").text.strip(),
            description=self.get_job_description(soup),
            company=company_dto,
            job_url=url,
            salary_text=salary_elem.text.strip() if salary_elem else "",
            location=location_elem.text.strip() if location_elem else "",
            position_type=position_elem.text.strip() if position_elem else "",
            expires=expires_elem.text.strip() if expires_elem else "",
            skills=skills,
            external_source="careerjunction"
        )

    def get_job_description(self, soup: BeautifulSoup) -> str:
        """
        Extract job description from page.
        
        Args:
            soup: BeautifulSoup instance of job detail page
            
        Returns:
            Cleaned description text or empty string
        """
        container = soup.find("div", class_="job-desc-on-expired")
        if not container:
            return ""
            
        details = container.find("div", class_="job-details")
        return details.text.strip() if details else ""

    async def periodic_loader(self, interval_minutes: int = 60) -> None:
        """
        Background task for periodic job loading.
        Runs indefinitely with specified interval.
        
        Args:
            interval_minutes: Minutes between scraping cycles
        """
        while True:
            try:
                # Run main scraping workflow
                await self.scrape_and_store_jobs()
            except Exception as e:
                self.logger.error(f"Scraping failed: {str(e)}")
            # Wait before next cycle
            await asyncio.sleep(interval_minutes * 60)




# ---- Needs to Update Career Scrapper to make it compatible with other Scrappers
class CareerScrapper:
    def __init__(self, scrapper: Scrapper):
        super().__init__()
        self.scrapper = scrapper
        self.logger = init_logger(self.__class__.__name__)

    async def init_loader(self):
        searches = []
        for search_term in self.scrapper.search_terms:
            jobs_list = await self.career_scrape(search_term=search_term)
            await self.scrapper.manage_jobs(jobs=jobs_list)

    def init_app(self, app: Flask):
        asyncio.run(self.init_loader())

    # noinspection PyBroadException
    @cached
    async def career_scrape(self, search_term: str) -> list[Job]:
        base_url = f"https://www.careers24.com/jobs/kw-{search_term}/"
        response = await self.scrapper.fetch_url(url=base_url)
        if response is None:
            return []

        soup = BeautifulSoup(response, 'html.parser')
        job_listings = soup.find_all("div", class_="job-card")
        jobs = []
        for job in job_listings:
            title = job.find("h2").text.strip()
            image_tag = job.find("img")

            if image_tag:
                company_name = job.find("img")["alt"]
                logo_link = job.find("img")["src"]
            else:
                company_name = None
                logo_link = None

            extra_data = job.find_all("li")
            # self.logger.info(f"Extra Data: {extra_data}")

            expires, job_type, location, updated_time = await self.extra_data_(extra_data)

            # /self.logger.info(f"JOB PRINTER: {job}")
            job_link_data = job.find("i")
            job_link = job_link_data.get('data-url')

            # Now, let's navigate to the apply_link and extract more details about the job
            job_details_response = await self.scrapper.fetch_url(job_link)

            if job_details_response:
                company_name, description, job_ref, salary = await self.extract_job_details(
                    company_name=company_name, job_details_response=job_details_response)
                self.logger.info(f""" 
                Company Name : {company_name} 
                description: {description} 
                salary : {salary}
                """)

                if salary is None and job_ref is None:
                    continue

                jobs.append(Job(**dict(search_term=search_term,
                                       title=title,
                                       logo_link=logo_link,
                                       job_link=job_link,
                                       company_name=company_name,
                                       salary=salary, position=job_type, location=location,
                                       updated_time=updated_time,
                                       expires=expires, job_ref=job_ref, description=description)))

        self.logger.info(
            f"Found {len(jobs)} Jobs with {str(self.__class__.__name__)} using search term : {search_term}")
        return jobs

    async def extra_data_(self, extra_data):
        if len(extra_data) >= 3:
            location = extra_data[0].get_text(strip=True)
            job_type = extra_data[1].get_text(strip=True)
            job_type = job_type.split(":")[1]
            posted_date_line = extra_data[2].get_text(strip=False)
            updated_time, expires = await self.parse_posted_date(date_line=posted_date_line.strip())
        else:
            location = "N/A"
            job_type = "N/A"
            updated_time = "N/A"
            expires = "N/A"
        return expires, job_type, location, updated_time

    async def extract_job_details(self, company_name, job_details_response):
        job_details_soup = BeautifulSoup(job_details_response, 'html.parser')
        vacancy_details = job_details_soup.find("div", class_="c24-vacancy-deatils-container")

        async def find_text_or_default_async(element, default="N/A"):
            return element.text.strip() if element else default

        async def extract_sectors_async(vacancy_details):
            sectors_tag = vacancy_details.find("li", class_="c24-sectr")
            sectors = [sector.text.strip() for sector in sectors_tag.find_all("a")] if sectors_tag else []
            return sectors

        salary_tag = vacancy_details.find("li", string="Salary:")
        self.logger.info(f"SALARY : {salary_tag}")
        if salary_tag:
            salary = (await find_text_or_default_async(salary_tag.find_next("li", class_="elipses"))).split(":")[1]
        else:
            salary = "Undisclosed"

        sectors = await extract_sectors_async(vacancy_details)

        reference_tags = vacancy_details.find("ul", class_="small-text").find_all("li")
        job_ref = (await find_text_or_default_async(reference_tags[-1]))
        if not job_ref:
            job_ref = str(uuid.uuid4())
        if "/" in job_ref:
            job_ref = job_ref.split("/")[0]

        description = (await find_text_or_default_async(vacancy_details.find("div", class_="v-descrip")))
        if not company_name:
            company_name = (
                await find_text_or_default_async(vacancy_details.find("p", class_="mb-15"), default="N/A"))

        return company_name, description, job_ref, salary

    @staticmethod
    async def parse_posted_date(date_line: str):
        separators = ["\n61", "<br\>", "<br>"]

        for separator in separators:
            if separator in date_line:
                parts = date_line.split(separator)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()

        return "N/A", "N/A"
