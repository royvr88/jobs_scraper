from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime
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

WEBDAV_PATH = c['webdavPathForXml']

sql = """ SELECT 
  job_title, 
  employer, 
  job_url, 
  scored_at, 
  score, 
  a.summary AS summary_score, 
  b.summary, 
  verdict, 
  payment, 
  job_text_summary,
  b.enddate            
FROM jobs_scored a 
LEFT JOIN jobs_scraped b 
  ON a.job_id = b.id
where score >=75 and lower(verdict) not in ('ignore','negeren')
"""

df = pd.read_sql(sql, engine)


rss = Element("rss", version="2.0")
channel = SubElement(rss, "channel")
SubElement(channel, "title").text = "Job Scores"
SubElement(channel, "link").text = f"{c['RSS_Hyperlink']}"
SubElement(channel, "description").text = "Filtered and scored job postings"


for _, row in df.iterrows():
    item = SubElement(channel, "item")
    
    SubElement(item, "title").text = f"{row['job_title']} ({row['employer']}) - {row['payment']}"
    SubElement(item, "link").text = row['job_url']
    SubElement(item, "description").text = f"""
<strong>Vacature omschrijving:</strong><br>
{row["summary"]}<br><br>
<strong>Salaris:</strong><br>
{row['payment']}<br><br>
<strong>Overweging:</strong><br>
{row['summary_score']}<br><br>
<strong>Score:</strong> {row['score']}<br><br>
<strong>Oordeel:</strong> {row['verdict']}
"""
    SubElement(item, "pubDate").text = row["scored_at"].strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    if pd.notna(row["enddate"]):
        # rij kan datetime of string zijn, normaliseer:
        if isinstance(row["enddate"], (datetime, )):
            end_str = row["enddate"].strftime("%Y-%m-%d")
        else:
            end_str = str(row["enddate"])
        SubElement(item, "enddate").text = end_str   # <<<<<

xml_bytes = tostring(rss, encoding="utf-8")
with open(WEBDAV_PATH, "wb") as f:
    f.write(xml_bytes)