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
    page.goto("https://www.hardenberg.nl/vacatures/")
    
    content = []
    vacancyList = page.locator('.wind-vacancy-wrapper')
    for job in vacancyList.locator('a').all():
        jobTitle = job.locator('.vacancy-title').text_content()
        jobUrl = 'https://hardenberg.nl'+job.get_attribute('href')
        page.goto(jobUrl)
        jobText=page.locator('.vacancy-single').text_content()
        employer = 'Gemeente Hardenberg'
        source = 'Gemeente Hardenberg'
        page.go_back()
        
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
