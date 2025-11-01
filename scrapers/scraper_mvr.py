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
scrapedJobs = pd.read_sql('select * from jobs_scraped', engine)
scrapedJobsUrls = list(scrapedJobs[['job_url']].values)

now = datetime.datetime.now()

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://mvr.nl/werken-bij-ons/")
    content = []
    listWithJobs = page.locator('div.oxy-dynamic-list')
    for job in listWithJobs.locator('div.ct-div-block').all():
        job.get_by_role('link').click()

        job_title = page.locator('h1.ct-headline').text_content()

        jobText = page.locator('section.ct-section').first.text_content()

        jobUrl = page.url
        if not jobUrl in scrapedJobsUrls:
            content.append([now, job_title, 'MvR',jobUrl, jobText, 'MvR'])
        else:
            print(jobUrl + 'is al eerder geparsed.')            




        page.go_back()



    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    
    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)

    

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
