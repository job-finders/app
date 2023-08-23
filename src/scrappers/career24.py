# import asyncio
# import requests
# from bs4 import BeautifulSoup
# from pydantic import ValidationError
#
# from src.database.models import Job


# async def scrape_careers24(keyword):
#     base_url = f"https://www.careers24.com/jobs/kw-{keyword}/"
#     response = requests.get(base_url)
#
#     if response.status_code == 200:
#         soup = BeautifulSoup(response.content, 'html.parser')
#         job_listings = soup.find_all("div", class_="job-card")
#         jobs = []
#         for job in job_listings:
#
#             title = job.find("h2").text.strip()
#             image_tag = job.find("img")
#
#             if image_tag:
#                 company_name = job.find("img")["alt"]
#                 logo_link = job.find("img")["src"]
#             else:
#                 company_name = None
#                 logo_link = None
#
#             extra_data = job.find_all("li")
#             expires, job_type, location, updated_time = await extra_data_(extra_data)
#
#             job_link = job.find("i")["data-url"]
#
#             # Now, let's navigate to the apply_link and extract more details about the job
#             job_details_response = requests.get(job_link)
#             if job_details_response.status_code == 200:
#                 company_name, description, job_ref, salary = await extract_job_details(company_name, job_details_response)
#
#                 job_dict = dict(title=title, logo_link=logo_link, job_link=job_link, company_name=company_name,
#                                 salary=salary, position=job_type, location=location, updated_time=updated_time,
#                                 expires=expires, job_ref=job_ref, description=description)
#                 jobs.append(Job(**job_dict))
#                 print(f"Job Created")
#         for _job in jobs:
#             print(_job)
#     else:
#         print("Failed to retrieve data from Careers24.")
#
#
# async def extra_data_(extra_data):
#     if len(extra_data) >= 3:
#         location = extra_data[0].get_text(strip=True)
#         job_type = extra_data[1].get_text(strip=True)
#         job_type = job_type.split(":")[1]
#         posted_date_line = extra_data[2].get_text(strip=False)
#         updated_time, expires = await parse_posted_date(date_line=posted_date_line.strip())
#     else:
#         location = "N/A"
#         job_type = "N/A"
#         updated_time = "N/A"
#         expires = "N/A"
#     return expires, job_type, location, updated_time
#
#
# async def extract_job_details(company_name, job_details_response):
#     job_details_soup = BeautifulSoup(job_details_response.content, 'html.parser')
#     vacancy_details = job_details_soup.find("div", class_="c24-vacancy-deatils-container")
#     salary_tag = vacancy_details.find("li", string="Salary:")
#     salary = vacancy_details.find("li", class_="elipses").text.strip().split(":")[1]
#
#     sectors_tag = vacancy_details.find("li", class_="c24-sectr")
#     sectors = [sector.text.strip() for sector in sectors_tag.find_all("a")] if sectors_tag else []
#     reference_tags = vacancy_details.find("ul", class_="small-text").find_all("li")
#     job_ref = reference_tags[-1].text.strip()
#     description = vacancy_details.find("div", class_="v-descrip").text.strip()
#     if not company_name:
#         try:
#             company_name = vacancy_details.find("p", class_="mb-15").text.strip()
#         except AttributeError:
#             company_name = "N/A"
#     return company_name, description, job_ref, salary
#
#
# async def parse_posted_date(date_line: str):
#
#     if "\n61" in date_line:
#         parts = date_line.split("\n61")
#     elif "<br\>" in date_line:
#         parts = date_line.split("\n61")
#     else:
#         parts = []
#
#     if len(parts) == 2:
#         return parts[0].strip(), parts[1].strip()
#     return "N/A", "N/A"


# if __name__ == "__main__":
#     keyword = input("Enter a keyword to search for jobs on Careers24: ")
#     asyncio.run(scrape_careers24(keyword))
#
# # < div
# #
# #
# # class ="c24-vacancy-deatils-container pt-15" >
# #
# # < div
# #
# #
# #
# # Deputy Nursing Manager
# # Johannesburg
# # Salary: R25 000.00 - R41 667.00 Per Month
# # Job Type: Permanent
# # Sectors: Medical General
# # Reference: 2058454
# # Apply before Oct 22 2023 | 61 Days left
