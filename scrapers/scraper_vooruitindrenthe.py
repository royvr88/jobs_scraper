import re
from playwright.sync_api import Playwright, sync_playwright, expect
from bs4 import BeautifulSoup
import requests
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
# If using Transaction Pooler or Session Pooler, we want to ensure we disable SQLAlchemy client side pooling -
# https://docs.sqlalchemy.org/en/20/core/pooling.html#switching-pool-implementations
# engine = create_engine(DATABASE_URL, poolclass=NullPool)



scrapedJobs = pd.read_sql('select * from jobs_scraped', engine)
scrapedJobsUrls = list(scrapedJobs[['job_url']].values)

now = datetime.datetime.now()

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.vooruitindrenthe.nl/vacatures")


    html = page.content()

    content = []
    for job in page.get_by_role("button").all():
        
        
        if 'favorite_border' in job.text_content() and 'share' in job.text_content():
            # print(job.text_content())
            job.click()
            jobTitle = page.locator("h1.vacature-paginatitel").text_content()
            employer = page.locator("a.general-link").nth(1).text_content()
            jobText = page.locator("#vacature-detail").text_content()
            jobUrl = page.url
            page.go_back()
            # page.goto("https://www.vooruitindrenthe.nl/vacatures")

            if not jobUrl in scrapedJobsUrls:
                content.append([now, jobTitle, employer,jobUrl, jobText, 'Vooruit in Drenthe'])
            else:
                print(jobUrl + 'is al eerder geparsed.')
        else:
            pass


    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    
    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)



    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
