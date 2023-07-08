from pprint import pprint

import requests
from bs4 import BeautifulSoup

_default_jobs = ['information-technology', 'office-admin',
                 'agriculture', 'engineering', 'building-construction',
                 'business-management', 'cleaning-maintenance', 'business-management',
                 'community-social-welfare', 'education', 'nursing', 'finance']


def scrape_career_junction_jobs(job_terms=None, limit_pages: int = 10):
    """

    :param job_terms:
    :param limit_pages:
    :return:
    """
    if job_terms is None:
        job_terms = _default_jobs

    for search_term in job_terms:
        jobs = []
        for page in range(limit_pages):
            if page == 0:
                continue
            url = f"https://www.careerjunction.co.za/jobs/{search_term}?page={page}"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, "html.parser")

            job_elements = soup.find_all("div", class_="job-result")

            for job_element in job_elements:
                show_more_link: str = job_element.find("a", class_="show-more")["href"]
                link = f"https://www.careerjunction.co.za/{show_more_link}"
                job_details = requests.get(link)
                job_soup = BeautifulSoup(job_details.content, "html.parser")
                jobs.append(more_details(job_soup=job_soup))

        print(f"total jobs found : {len(jobs)}")
        return jobs


def more_details(job_soup):
    try:
        job_element = job_soup.find("div", class_="job-description")

        job_dict = {"logo_link": job_element.find("img")["src"], "title": job_element.find("h1").text.strip(),
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
        desired_skills_element = description_element.find_all("ul")[0]
        desired_skills = [skill.text.strip() for skill in desired_skills_element.find_all("li")]
        job_dict['description'] = job_description
        job_dict['desired_skills'] = desired_skills
        pprint(job_dict)
        return job_dict
    except AttributeError as e:
        return


if __name__ == "__main__":
    scrape_career_junction_jobs()
