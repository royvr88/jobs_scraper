# 🧠 Municipal Job Intelligence Pipeline

A complete end-to-end solution to automatically scrape, summarize, score, and publish municipal job vacancies — all orchestrated via **n8n**, powered by **Python**, and stored in **PostgreSQL**.

---

## ⚙️ Overview

This project automates the entire lifecycle of job postings:

1. **Scraping**  
   - Collects vacancies from multiple municipal career sites via Playwright-based Python scripts.
   - Stores raw job descriptions (HTML text) into a PostgreSQL database (local or Supabase).

2. **Summarization & Scoring (AI)**  
   - Uses `n8n` to call AI models (e.g., via OpenAI or Hugging Face) to summarize job text.  
   - Each summary is scored against a personal profile and stored alongside metadata.

3. **Feed Generation (XML)**  
   - Generates RSS-style XML feeds using the `xml_builder` scripts.  
   - These feeds can be imported directly into **FreshRSS**, so you can “subscribe” to personalized job listings.

4. **Automation**  
   - All workflows are orchestrated by `n8n`:
     - Scraping jobs
     - Summarizing & scoring
     - XML feed generation
     - (Optionally) triggering a FreshRSS update via Docker.

---

## 🧩 Architecture

```
                ┌──────────────────┐
                │ n8n Orchestrator │
                └───────┬──────────┘
                        │
                        ▼
          ┌─────────────────────────────┐
          │ Python Scrapers (Playwright)│
          │  - Runs via SSH on remote   │
          │  - Saves to PostgreSQL      │
          └───────────┬────────────────┘
                      │
                      ▼
             ┌────────────────────┐
             │ AI Summarization   │
             │ + Scoring via n8n  │
             └───────────┬────────┘
                         │
                         ▼
               ┌────────────────┐
               │ XML Builder    │
               │ + FreshRSS     │
               └────────────────┘
```

---

## 🧱 Components

### 1. Python Scrapers

Playwright-based scripts that scrape municipal job sites.  
Each script writes new vacancies to the `jobs_scraped` table in PostgreSQL.

Example:
```
python scraper_zwolle.py
python scraper_vooruitindrenthe.py
python scraper_kampen.py
```

All scripts use SQLAlchemy for database I/O:
```
from sqlalchemy import create_engine
engine = create_engine("postgresql+psycopg2://user:pass@host:5432/jobs")
df.to_sql("jobs_scraped", engine, if_exists="append", index=False)
```

---

### 2. n8n Workflows

Each stage of the process is automated via modular n8n workflows.

| Workflow | Purpose |
|-----------|----------|
| `workflow_jobs_scraper.json` | Runs all scraper scripts sequentially over SSH |
| `workflow_jobs_summarize_and_score.json` | Summarizes and scores job texts with AI |
| `workflow_jobs_create_xml.json` | Builds multiple XML feeds and optionally refreshes FreshRSS |
| `workflow_jobs_orchestrator.json` | The master orchestrator running every 5 days via cron |
| `workflow_error_messages.json` | Handles any errors or failed jobs |

Each workflow uses environment variables for SSH connections:
```
$SCRAPER_SSH_USER
$SCRAPER_HOST
$PYTHON_ENV
$SCRAPER_DIR
```

---

### 3. Database Schema

| Table | Description |
|--------|-------------|
| `jobs_scraped` | Raw job listings (title, description, source, scraped_at) |
| `jobs_scored` | Summaries and scores per job ID |
| `jobs_summary` | Optional intermediate summaries |
| `jobs_error_log` | Logged errors from n8n or scraping |

---

### 4. XML Feed Builder

The XML builder scripts generate RSS-compatible feeds consumed by **FreshRSS** or any RSS reader.

```
ssh $SCRAPER_SSH_USER@$SCRAPER_HOST -C "$PYTHON_ENV $SCRAPER_DIR/xml_builder.py"
ssh $SCRAPER_SSH_USER@$SCRAPER_HOST -C "$PYTHON_ENV $SCRAPER_DIR/xml_builder_relevant_jobs.py"
ssh $SCRAPER_SSH_USER@$SCRAPER_HOST -C "$PYTHON_ENV $SCRAPER_DIR/xml_builder_sam.py"
```

Output examples:
- `/media/feeds/jobs.xml`
- `/media/feeds/jobs_relevant.xml`
- `/media/feeds/jobs_sam.xml`

Each feed item contains:
- Title + Employer + Pay info
- AI-generated summary
- Matching score
- Verdict (“fit”, “maybe”, “skip”)

---

## 🧠 Example Flow (Simplified)

```
1. n8n trigger (every 5 days)
2. Run all Python scrapers (via SSH)
3. Summarize + score in n8n
4. Write results to PostgreSQL
5. Run xml_builder.py → generate `jobs.xml`
6. (Optional) Refresh FreshRSS Docker container
```

---

## 🧰 Example Configuration

**Database connection (SQLAlchemy)**  
```
USER = "postgres"
PASSWORD = "mypassword"
HOST = "localhost"
PORT = "5432"
DBNAME = "jobs"
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"
```

**n8n Environment variables (in `.env`)**  
```
SCRAPER_SSH_USER=user
SCRAPER_HOST=myserver.local
PYTHON_ENV=/opt/envs/playwright/bin/python
SCRAPER_DIR=/srv/jobs
```

---

## 🧩 Example Files

| File | Purpose |
|------|----------|
| `scraper_zwolle.py` | Scrape Zwolle job portal |
| `scraper_kampen.py` | Scrape Kampen job portal |
| `xml_builder.py` | Build complete XML feed |
| `xml_builder_relevant_jobs.py` | Filtered feed based on personal scoring |
| `xml_builder_sam.py` | Alternative feed for second profile |
| `workflow_jobs_scraper.json` | n8n job scraper orchestration |
| `workflow_jobs_create_xml.json` | n8n XML builder workflow |
| `workflow_jobs_orchestrator.json` | Cron-based main orchestration |

---

## 🔐 Security Notes

- No credentials are stored in code.  
- SSH connections are environment-based and must use **key authentication**.  
- Supabase (if used) should apply **row-level security**.  
- Local PostgreSQL setups should enforce **minimum TLS or socket auth**.

---

## 📦 Deployment

You can host this setup on:
- **Local Raspberry Pi / Linux server**
- **Dockerized PostgreSQL + n8n + FreshRSS stack**
- **Supabase backend** (if you want managed Postgres with REST access)

To start the orchestrator:
```
n8n import:workflow --input=workflows/workflow_jobs_orchestrator.json
n8n start
```
> Optionally you can copy the whole contents of the JSON in a blank n8n sheet and use the cron of n8n.


---

## 🧩 Example Result in FreshRSS

Feed URL (example):

```
https://rss.example.com/jobs.xml
```

FreshRSS will automatically show the latest scored jobs:
- 🟢 Perfect fit (Score > 8)
- 🟡 Partial match (Score 5–8)
- 🔴 Not relevant (< 5)

---

## 🧾 License

MIT License – free to use, modify, and adapt.  
Just credit the repo if you reuse large portions.

---

**Author:** Roy  
**Stack:** Python · Playwright · BeautifulSoup · SQLAlchemy · PostgreSQL · n8n · Supabase · FreshRSS
