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
    page.goto("https://steenwijkerland.varbi.com/nl")
    
    content = []
    vacancyList = page.locator('.table-mobile').first
    allJobs = []
    for job in vacancyList.locator('a').all():
        url = job.get_attribute('href')
        if url.startswith('https://steenwijkerland.varbi.com/') and url not in allJobs:
            allJobs.append(url)
    # print(allJobs)
    for job in allJobs:
        page.goto(job)
        jobTitle = page.locator('div.page-header').locator('h1').text_content()
        jobUrl = job
        employer = 'Gemeente Steenwijkerland'
        source = 'Gemeente Steenwijkerland'    
        jobText = page.locator('.job-desc').text_content()

        page.go_back()

        if not jobUrl in scrapedJobsUrls:
            content.append([now, jobTitle, employer,jobUrl, jobText, source])
        else:
            print(jobUrl + 'is al eerder geparsed.')            


    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    # df.to_csv('test.csv')
    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
