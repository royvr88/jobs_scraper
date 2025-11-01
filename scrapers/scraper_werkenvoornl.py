

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
    #baseUrl = "https://www.werkenvoornederland.nl/vacatures?functietype=CFT.08&salarisniveau=10%2C11%2C12%2C13%2F&type=vacature&vakgebied=CVG.08&dienstverband=CSD.02%2CCSD.10&werkdenkniveau=CWD.08"
    # hierboven is zonder filter van afgelopen 5 dagen.
    baseUrl = 'https://www.werkenvoornederland.nl/vacatures?functietype=CFT.08&salarisniveau=10%2C11%2C12%2C13%2F&type=vacature&vakgebied=CVG.08&dienstverband=CSD.02%2CCSD.10&werkdenkniveau=CWD.08&sinds=5d'
    page.goto(baseUrl)
    page.wait_for_timeout(1000)
    content = []
    totaalJobs = page.locator('.vacancy-result-bar__totals').text_content().split(' ')[2]
    for i in range(int(totaalJobs)):
        page.wait_for_timeout(10)
        page.keyboard.press("PageDown")
    listWithJobs = page.locator('div.vacancy-list')
    x = 0
    for job in listWithJobs.locator('.vacancy').all():
        try:
            for i in range(int(totaalJobs)):
                page.wait_for_timeout(10)
                page.keyboard.press("PageDown")        
            job_title = job.locator('h2.vacancy__title')
            parentDiv = job_title.locator('..')
            jobTitle = job_title.text_content()
            # print(jobTitle)
            employer = job.locator('p.vacancy__employer').text_content()
            # print(employer)
            page.wait_for_timeout(500)
            jobUrl = f"https://www.werkenvoornederland.nl{parentDiv.locator('a').first.get_attribute('href')}"
            if not jobUrl in scrapedJobsUrls:        
                parentDiv.get_by_role('link').first.click()
                page.wait_for_timeout(500)
                # jobUrl = page.url
                jobText = page.locator('.job-container').text_content()
                page.go_back()
                page.wait_for_timeout(500)
            # print(jobText)

            # print('jobtext length', len(jobText))
                print(jobTitle, jobUrl)
                scrapedJobsUrls.append(jobUrl)
                content.append([now, jobTitle, employer,jobUrl, jobText, 'Werken voor Nederland'])
            else:
                print(jobUrl + 'is al eerder geparsed.')            
        except Exception as e:
            print(str(e))
            page.goto(baseUrl)




            page.wait_for_timeout(500)
        x += 1

        if x >=10:



            df = pd.DataFrame(data=content, columns = ['scraped_at', 'job_title','employer','job_url','description','source'])
            # df.to_csv('test.csv')
            df.to_sql("jobs_scraped", engine, if_exists="append", index=False)
            content = []
            x = 0
    

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
