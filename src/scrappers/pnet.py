import requests
from bs4 import BeautifulSoup
headers: dict[str, str] = {
    'user-agent': "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)",
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.google.com',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Accept': '*/*'
}

def scrape_pnet_jobs():
    url = "https://www.pnet.co.za/jobs/information-technology"
    response = requests.get(url=url, headers=headers)
    print(response)
    soup = BeautifulSoup(response.content, "html.parser")
    print(soup)
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




if __name__ == "__main__":
    scrape_pnet_jobs()