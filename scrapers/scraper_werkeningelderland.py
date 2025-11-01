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
    vacaturesite = 'https://www.werkeningelderland.nl/vacatures/'
    page.goto(vacaturesite)
    page.wait_for_timeout(300)
    navigator = page.locator('nav.pagination')

    aantalPages = int(navigator.locator('li.pagination__item').nth(-2).text_content().replace(' ',''))
    content = []
    for i in range(aantalPages):
        
        page.goto(f'{vacaturesite}page/{str(i+1)}')
        page.wait_for_timeout(300)
        for job in page.locator('ul.vacancies__listing').locator('li.vacancies__item.listing__item').all():
            try:
                jobUrl = job.locator('a').get_attribute('href')
                if jobUrl not in scrapedJobsUrls:
                    jobTitle = job.locator('h1.vacancy__title').text_content()
                    source = 'Werken in Gelderland'
                    page.goto(jobUrl)
                    page.wait_for_timeout(300)
                    employer = page.locator('ul.single-vacancy__details.single-vacancy__detail--primary').locator('li.single-vacancy__detail').first.locator('.single-vacancy__detail__value').text_content()
                    jobText = page.locator('section.single-vacancy__content.content.content--small').text_content()
                    content.append([now, jobTitle, employer,jobUrl, jobText, source])
                    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
                    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)                    
                    page.go_back()
                    page.wait_for_timeout(300)
                else:
                    print(jobUrl + ' is al eerder geparsed.')     
            except Exception as e:
                print(str(e))
                page.goto(f'{vacaturesite}page/{str(i+1)}')
                page.wait_for_timeout(300)
            




    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    
    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
