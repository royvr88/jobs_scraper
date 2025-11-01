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
    baseUrl = 'https://werkenbij.alliander.com/vacatures/?functies_it[]=agile&functies_it[]=architectuur&functies_it[]=data-analytics&functies_it[]=development&functies_it[]=functioneel-beheer&functies_staf[]=planning&functies_staf[]=support&functies_staf[]=teamleider&functies_staf[]=projectmanagement&job_branch[]=it&job_branch[]=staf_support'
    page.goto(baseUrl)
    content = []
    jobs = []

    page.wait_for_timeout(3000)
    for loc in page.locator('h2').all():
        if 'vacatures gevonden' in loc.text_content():
            string = loc.text_content()
            aantalVacatures = int(string.split(' ')[3])
            break
    aantalPages = -(-aantalVacatures // 10)

    for pageNum in range(1, aantalPages + 1):
        page.wait_for_timeout(500)

        for i in range(10):
            page.wait_for_timeout(50)
            page.keyboard.press("PageDown")         
        for link in page.locator('a.Link').all():
            if link.get_attribute('data-x') == 'link-to-vacancy':
                jobUrl = 'https://werkenbij.alliander.com'+link.get_attribute('href')
                print(jobUrl)
                jobs.append(jobUrl)
        for link in page.locator('a').all():
            if link.get_attribute('data-x') == 'goto-next-page':
                try:
                    link.click(timeout=2000) 
                    
                except:
                    pass
                break
    x = 0
    for job in jobs:
        if not job in scrapedJobsUrls:
            page.goto(job)
            page.wait_for_timeout(500)
            jobTitle = page.locator('h1.JobMeta-title').text_content()
            jobUrl = job
            jobText = page.locator('div.SingleJob-description').text_content()
            source = 'Alliander'
            employer = 'Alliander'
            content.append([now, jobTitle, employer,jobUrl, jobText, source])
            print(jobTitle, employer, jobUrl, len(jobText), source)
        if x > 20:
            print('20 jobs wegschrijven..')
            x = 0
            df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
            df.to_sql("jobs_scraped", engine, if_exists="append", index=False)
            content = []
        x += 1
    df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
    
    df.to_sql("jobs_scraped", engine, if_exists="append", index=False)

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
