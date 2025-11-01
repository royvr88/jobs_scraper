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
    vacaturesite = 'https://www.werkeninfriesland.nl/vacatures/'
    page.goto(vacaturesite)
    
    content = []
    source = 'Werken in Friesland'
    for job in page.locator('div.col-sm-6.col-md-4').all():
        jobUrl = job.locator('a').get_attribute('href')
        jobTitle = job.locator('div.caption').locator('h3').text_content()
        employer = job.locator('div.caption').locator('p').nth(0).text_content()
        if jobUrl not in scrapedJobsUrls:
            try:
                page.goto(jobUrl)
                page.wait_for_timeout(300)
                jobText = page.locator('div.col-sm-12.col-md-8.detail').text_content()
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

                # print('werkt niet')
        # if jobUrl not in scrapedJobsUrls:
        #     try:
        #         jobTitle = job.text_content()
        #         employer = 'Gemeente Ommen'
        #         source = 'Gemeente Ommen'
        #         page.goto(jobUrl)
        #         page.wait_for_timeout(300)
        #         jobText = page.locator('div.container.yard-blocks-grid.pattern-standard-page').text_content()
        #         # print(jobText)
        #         content.append([now, jobTitle, employer,jobUrl, jobText, source])

        #         page.go_back()
        #         page.wait_for_timeout(300)
        #     except Exception as e:

        #         print(str(e))
        #         page.goto(vacaturesite)
        # else:
        #     print(jobUrl + ' is al eerder geparsed.')


    # df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    
    # df.to_sql("jobs_scraped", engine, if_exists="append", index=False)


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
