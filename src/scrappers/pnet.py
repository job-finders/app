import requests
from bs4 import BeautifulSoup

def scrape_pnet_jobs():
    url = "https://www.pnet.co.za/5/job-search-detailed.html?ke=&li=100&of=0&suid=cef3a793-10e4-41be-8d84-dc43a00c4b11&an=facets"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    job_elements = soup.find_all("li", class_="result")

    for job_element in job_elements:
        title = job_element.find("a", class_="jobLink").text.strip()
        company = job_element.find("div", class_="company").text.strip()
        location = job_element.find("span", class_="location").text.strip()
        salary = job_element.find("span", class_="salary").text.strip()

        print("Title:", title)
        print("Company:", company)
        print("Location:", location)
        print("Salary:", salary)
        print("------------------------------------")

scrape_pnet_jobs()
