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
    page.goto("https://www.werkenvoorlelystad.nl/Werken-voor-Lelystad/Vacatures.html")
    
    content = []
    for job in page.locator('div.card').all():
        try:
            jobTitle = job.locator('h2.card-title').text_content()
            jobUrl = 'https://www.werkenvoorlelystad.nl/' + job.get_by_role('link').get_attribute('href')

            # print(jobTitle, jobUrl)

            if jobUrl not in scrapedJobsUrls:
                employer = 'Gemeente Lelystad'
                source = 'Gemeente Lelystad'
                page.goto(jobUrl)
                page.wait_for_timeout(300)
                jobText = page.locator('body').text_content()
                content.append([now, jobTitle, employer,jobUrl, jobText, source])

                # print(jobTitle,jobUrl,len(jobText))
                page.go_back()
            else:
                print(jobUrl + 'is al eerder geparsed.') 

        except Exception as e:
            print(str(e))
    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    
    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
