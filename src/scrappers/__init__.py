import re
import asyncio
import uuid
from datetime import timedelta

from bs4 import BeautifulSoup
from flask import Flask
from pydantic import ValidationError
from requests_cache import CachedSession

from src.cache import cached
from src.logger import init_logger
from src.database.models.jobs import Job
from src.utils import format_reference


class Scrapper:
    def __init__(self):
        self.search_terms = [
            'information-technology',
            'office-admin',
            'agriculture',
            'engineering',
            'building-construction',
            'business-management',
            'cleaning-maintenance',
            'community-social-welfare',
            'education',
            'nursing',
            'finance',
            'programming']
        self.headers: dict[str, str] = {
            'user-agent': "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)",
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Accept': '*/*'
        }
        self.request_sessions = CachedSession('jobs.cache', use_cache_dir=False,
                                              cache_control=True,
                                              # Use Cache-Control response headers for expiration, if available
                                              expire_after=timedelta(hours=12),
                                              # Otherwise expire responses after one day
                                              allowable_codes=[200, 400],
                                              # Cache 400 responses as a solemn reminder of your failures
                                              allowable_methods=['GET', 'POST'],
                                              match_headers=['Accept-Language'],
                                              # Cache a different response per language
                                              stale_if_error=True
                                              # In case of request errors, use stale cache data if possible
                                              )

        self.jobs: dict[str, Job] = {}

    async def manage_jobs(self, jobs: list[Job]):
        for job in jobs:
            ref = format_reference(ref=job.job_ref)
            self.jobs[ref] = job

    # noinspection PyBroadException
    async def fetch_url(self, url: str) -> bytes | None:
        try:
            return self.request_sessions.get(url=url, headers=self.headers).content
        except Exception as e:
            return None

    async def job_search(self, job_reference: str):
        """
            :param job_reference:
            :return:
        """
        ref = format_reference(ref=job_reference)
        try:
            return self.jobs[ref]
        except KeyError as e:
            # In case of error return the last job
            return self.jobs[list(self.jobs.keys())[-1]]


class JunctionScrapper:
    """
    Junction Job Scrapper
    """

    def __init__(self, scrapper: Scrapper):
        self._jobs_base_url: str = "https://www.careerjunction.co.za/jobs/"
        self._junction_base_url: str = "https://www.careerjunction.co.za/"
        self.scrapper = scrapper
        self.logger = init_logger(self.__class__.__name__)

    async def init_loader(self):
        # searches = []
        for search_term in self.scrapper.search_terms:
            self.logger.info(f"Searching for : {search_term}")
            jobs_list = await self.junction_scrape(term=search_term)
            await self.scrapper.manage_jobs(jobs=jobs_list)

    def init_app(self, app: Flask):
        asyncio.run(self.init_loader())

    @cached
    async def junction_scrape(self, term: str, page_limit: int = 1) -> list[Job]:
        """
            given one search term scrape jobs
        :param term:
        :param page_limit:
        :return:
        """
        jobs = []
        for page in range(page_limit + 1):
            if page == 0:
                continue

            url = f"{self._jobs_base_url}{term}?page={page}"
            response: bytes | None = await self.scrapper.fetch_url(url=url)

            if not response:
                self.logger.info(f"response : not OK")
                continue

            soup = BeautifulSoup(response, "html.parser")
            job_elements = soup.find_all("div", class_="job-result")

            for job_element in job_elements:
                show_more_link: str = job_element.find("a", class_="show-more")["href"]
                link = f"{self._junction_base_url}{show_more_link.replace('/', '')}"
                job_details: bytes | None = await self.scrapper.fetch_url(link)
                if job_details is None:
                    self.logger.info("Job details not being fetched")
                    continue
                job_soup = BeautifulSoup(job_details, "html.parser")
                jobs.append(self.more_details(job_soup=job_soup, job_link=link, search_term=term))

        jobs_results = await asyncio.gather(*jobs)
        try:
            jobs = [Job(**job) for job in jobs_results if job]
            self.logger.info(f"Gathered a total of {len(jobs)} jobs using {str(self.__class__.__name__)} using search term: {term}")
            return jobs
        except ValidationError as e:
            self.logger.info(f"Error creating Job Model: {str(e)}")
            return []

    @staticmethod
    async def more_details(job_soup, job_link: str, search_term: str):
        try:
            job_element = job_soup.find("div", class_="job-description")

            job_dict = {"search_term": search_term,
                        "logo_link": job_element.find("img")["src"],
                        "title": job_element.find("h1").text.strip(),
                        "job_link": job_link,
                        "company_name": job_element.find("h2").text.strip(),
                        "salary": job_element.find("li", class_="salary").text.strip(),
                        "position": job_element.find("li", class_="position").text.strip(),
                        "location": job_element.find("li", class_="location").text.strip(),
                        "updated_time": job_element.find("li", class_="updated-time").text.strip(),
                        "expires": job_element.find("li", class_="expires").text.strip(),
                        "job_ref": job_element.find("li", class_="cjun-job-ref").text.strip()}

            description_element = job_soup.find("div", class_="job-desc-on-expired")
            job_description = description_element.find("div", class_="job-details").text.strip()

            # Extract and print the desired skills
            try:
                desired_skills_element = description_element.find_all("ul")[0]
                desired_skills = [skill.text.strip() for skill in desired_skills_element.find_all("li") if skill]

            except IndexError:
                desired_skills = []

            job_dict['description'] = job_description
            job_dict['desired_skills'] = desired_skills

            return job_dict
        except AttributeError as e:
            return


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
            expires, job_type, location, updated_time = await self.extra_data_(extra_data)
            try:
                job_link = job.find("i")["data-url"]
            except KeyError:
                continue

            # Now, let's navigate to the apply_link and extract more details about the job
            job_details_response = await self.scrapper.fetch_url(job_link)
            if job_details_response:
                company_name, description, job_ref, salary = await self.extract_job_details(
                    company_name=company_name, job_details_response=job_details_response)
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
        self.logger.info(f"Found {len(jobs)} Jobs with {str(self.__class__.__name__)} using search term : {search_term}")
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

    @staticmethod
    async def extract_job_details(company_name, job_details_response):
        try:
            job_details_soup = BeautifulSoup(job_details_response, 'html.parser')
            vacancy_details = job_details_soup.find("div", class_="c24-vacancy-deatils-container")

            def find_text_or_default(element, default="N/A"):
                return element.text.strip() if element else default

            salary_tag = vacancy_details.find("li", string="Salary:")
            salary = find_text_or_default(salary_tag.find_next("li", class_="elipses")).split(":")[1]

            sectors_tag = vacancy_details.find("li", class_="c24-sectr")
            sectors = [sector.text.strip() for sector in sectors_tag.find_all("a")] if sectors_tag else []

            reference_tags = vacancy_details.find("ul", class_="small-text").find_all("li")
            job_ref = find_text_or_default(reference_tags[-1])
            if not job_ref:
                job_ref = str(uuid.uuid4())
            if "/" in job_ref:
                job_ref = job_ref.split("/")[0]

            description = find_text_or_default(vacancy_details.find("div", class_="v-descrip"))
            if not company_name:
                company_name = find_text_or_default(vacancy_details.find("p", class_="mb-15"), default="N/A")

            return company_name, description, job_ref, salary
        except AttributeError:
            return None, None, None, None

    @staticmethod
    async def parse_posted_date(date_line: str):
        separators = ["\n61", "<br\>", "<br>"]

        for separator in separators:
            if separator in date_line:
                parts = date_line.split(separator)
                if len(parts) == 2:
                    return parts[0].strip(), parts[1].strip()

        return "N/A", "N/A"
