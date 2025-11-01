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
    vacaturesite = 'https://www.hattem.nl/Bestuur_en_organisatie/Werk_van_nu_in_historisch_Hattem/Vacatures/Vacatures'
    page.goto(vacaturesite)
    page.wait_for_timeout(1000)
    content = []
    for job in page.locator('a.external').all():        
        jobUrl = job.get_attribute('href')
        print(jobUrl)
        if jobUrl not in scrapedJobsUrls and jobUrl.startswith('https://vacatures.one/'):
            try:
                employer = 'Gemeente Hattem'
                source = 'Gemeente Hattem'
                page.goto(jobUrl)
                page.wait_for_timeout(300)
                jobTitle = page.locator('div.col-md-8').locator('h1').text_content()
                jobText = page.locator('div.vacancy-description').text_content()
                content.append([now, jobTitle, employer,jobUrl, jobText, source])
                page.go_back()
                page.wait_for_timeout(300)
            except Exception as e:

                print(str(e))
                page.goto(vacaturesite)
        else:
            print(jobUrl + ' is al eerder geparsed.')


    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    
    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
