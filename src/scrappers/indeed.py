import requests
from bs4 import BeautifulSoup


def scrape_indeed_jobs():
    url = "https://www.indeed.co.za/jobs?q=&l=South+Africa"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    job_elements = soup.find_all("div", class_="jobsearch-SerpJobCard")

    for job_element in job_elements:
        title = job_element.find("a", class_="jobtitle").text.strip()
        company = job_element.find("span", class_="company").text.strip()
        location = job_element.find("span", class_="location").text.strip()
        summary = job_element.find("div", class_="summary").text.strip()

        print("Title:", title)
        print("Company:", company)
        print("Location:", location)
        print("Summary:", summary)
        print("------------------------------------")



if __name__ == "__main__":
    scrape_indeed_jobs()