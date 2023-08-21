from pprint import pprint
import asyncio

if __name__ == "__main__":
    from src.scrappers import JunctionScrapper
    scraper = JunctionScrapper()
    print(asyncio.run(scraper.scrape(term="Programming")))
    # scrape_career_junction_jobs()
