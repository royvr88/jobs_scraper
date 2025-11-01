import feedparser

from playwright.sync_api import Playwright, sync_playwright, expect
import datetime

import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus


import json
with open('configuration.json', 'r') as f:
    c = json.loads(f.read())

USER = c['postgresUser']
PASSWORD = quote_plus(c['postgresPassword'])
HOST = c['postgresHost']
PORT = c['postgresPort']
DBNAME = c['postgresDatabaseName']
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)
scrapedJobs = pd.read_sql('select * from jobs_scraped', engine)
scrapedJobsUrls = list(scrapedJobs[['job_url']].values)

now = datetime.datetime.now()



url = "https://www.dalfsen.nl/rss/content-list?type%5B%5D=vacancy&tags%5B%5D=1284&sort_by=published_at&sort_order=DESC"  # replace with actual RSS feed URL
feed = feedparser.parse(url)



def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    content = []
    for item in feed.entries:
        page.goto(item.link)
        page.wait_for_timeout(200)

        jobTitle = item.title
        employer = 'Gemeente Dalfsen'
        jobText = page.locator('article.main-content').text_content()
        jobUrl = item.link
        source = 'Gemeente Dalfsen'

        if not jobUrl in scrapedJobsUrls:
            content.append([now, jobTitle, employer,jobUrl, jobText, source])
        else:
            print(jobUrl + 'is al eerder geparsed.')            

    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    
    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
