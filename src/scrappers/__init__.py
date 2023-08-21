import asyncio
import aiohttp
from bs4 import BeautifulSoup
from flask import Flask
from pydantic import ValidationError

from src.database.models.jobs import Job

_default_jobs = ['information-technology',
                 'office-admin',
                 'agriculture',
                 'engineering',
                 'building-construction',
                 'business-management',
                 'cleaning-maintenance',
                 'business-management',
                 'community-social-welfare',
                 'education',
                 'nursing',
                 'finance',
                 'programming']


class JunctionScrapper:
    """
    Junction Job Scrapper
    """

    def __init__(self):

        self._jobs_base_url: str = "https://www.careerjunction.co.za/jobs/"
        self._junction_base_url: str = "https://www.careerjunction.co.za/"

        self.headers: dict[str, str] = {
            'user-agent': "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)",
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Accept': '*/*'
        }
        pass

    def init_app(self, app: Flask):
        pass

    async def fetch_url(self, url: str, timeout: int = 5) -> str | None:
        try:
            # return requests.get(url).content
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url=url, timeout=timeout) as response:
                    response.raise_for_status()
                    return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Error raised : {str(e)}")
            return None

    async def scrape(self, term: str, page_limit: int = 1) -> list[Job]:
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
            response: str = await self.fetch_url(url=url)
            print(f"Response : OK")
            if not response:
                continue

            soup = BeautifulSoup(response, "html.parser")
            job_elements = soup.find_all("div", class_="job-result")

            for job_element in job_elements:
                show_more_link: str = job_element.find("a", class_="show-more")["href"]
                link = f"{self._junction_base_url}{show_more_link}"
                job_details = await self.fetch_url(link)
                if job_details is None:
                    continue
                print(f"job details OK")
                job_soup = BeautifulSoup(job_details, "html.parser")
                jobs.append(self.more_details(job_soup=job_soup, job_link=link))

        jobs_results = await asyncio.gather(*jobs)
        try:
            print(type(jobs_results))
            return [Job(**job) for job in jobs_results if job]
        except ValidationError as e:
            print(str(e))
            return []

    @staticmethod
    async def more_details(job_soup, job_link):
        try:
            job_element = job_soup.find("div", class_="job-description")

            job_dict = {"logo_link": job_element.find("img")["src"],
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
