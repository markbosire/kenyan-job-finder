# Kenyan Job Finder

Aggregates tech jobs from Kenyan job boards + LinkedIn into a single SQLite DB, with a REST API + web UI for browsing and tracking applied/ignored status.

## Requirements

- **Python 3.10+**
- **Chrome/Chromium** (for CDP-based scrapers: GoogleJobs, Fuzu, CodingKenya, PigiaMe)

---

## Setup

### Linux

```bash
# 1. Clone & enter
git clone https://github.com/markbosire/kenyan-job-finder.git jobscraper
cd jobscraper

# 2. Create virtualenv & activate
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python packages
pip install --upgrade pip
pip install --only-binary :all: -r requirements.txt

# 4. Install Playwright browser binaries
playwright install chromium

# 5. (Optional) Install Chrome/Chromium for CDP
# Debian/Ubuntu:
sudo apt update && sudo apt install -y chromium-browser
# Fedora:
sudo dnf install -y chromium
# Arch:
sudo pacman -S chromium

# 6. Verify
python run.py --help
```

### Windows

```powershell
# 1. Clone & enter
git clone https://github.com/markbosire/kenyan-job-finder.git jobscraper
cd jobscraper

# 2. Create virtualenv & activate
python -m venv .venv
.venv\Scripts\activate

# 3. Install Python packages
pip install --upgrade pip
pip install --only-binary :all: -r requirements.txt

# 4. Install Playwright browser binaries
playwright install chromium

# 5. Install Chrome
# Download from https://www.google.com/chrome/ and install normally

# 6. Verify
python run.py --help
```

---

## How to Use

### 1. Run scrapers

```bash
# Activate virtualenv first (if not already)
source .venv/bin/activate         # Linux
.venv\Scripts\activate            # Windows

# Scrape with default keywords (22 tech roles), 7-day cutoff
python run.py

# Custom keywords
python run.py --keywords "python developer,devops engineer" --days 14

# Non-tech keywords (skip CorporateStaffing & CodingKenya — they dump all jobs)
python run.py --nontech --keywords "sales,marketing,accountant" --days 7

# Skip LinkedIn (faster, only Kenyan boards)
python run.py --skip-jobspy

# Skip Kenyan boards (LinkedIn only)
python run.py --skip-kenya
```

What happens:
- Scrapers run in order: GoogleJobs → Fuzu → MyJobMag → CorporateStaffing → JobWebKenya → CodingKenya → PigiaMe → Jobiglo → BrighterMonday
- Each scraper fetches listing pages, extracts job cards, filters by date (last 7 days) and keyword match
- Results are merged, deduplicated, and stored in `data/jobs.db`
- Old jobs (>7 days) and blocked sources (BeBee, WhatJobs, CosmoQuick) are automatically cleaned

### 2. Start the web UI

```bash
python api.py --port 9090
```

Open http://127.0.0.1:9090 in your browser. You can:
- Browse all jobs with search, source, and location filters
- Mark jobs as **Applied** or **Ignored** (persisted in DB)
- Filter by status tab (All / Applied / Ignored)

### 3. Scrape again later

```bash
python run.py
```

Re-runs are safe — only new/updated jobs are upserted. Old jobs stay in the DB unless they exceed the age limit.

---

## Scrapers

| Source | Method | URL Filter |
|--------|--------|------------|
| GoogleJobs | CDP (existing Chrome) | `+in+the+last+week` + post-filter |
| Fuzu | CDP (Playwright) | `filters[published]=week` |
| MyJobMag | requests | keyword search |
| CorporateStaffing | requests | category URL, binary search |
| JobWebKenya | requests | keyword search |
| CodingKenya | CDP (Playwright) | `posted_before=7-days` |
| PigiaMe | CDP/requests | keyword search + title filter |
| Jobiglo | requests | keyword slug + city filter |
| BrighterMonday | requests | keyword search + title filter |

---

## Project structure

```
jobscraper/
├── api.py               # REST API + web UI server
├── run.py               # Scraper pipeline + DB store
├── normalize.py         # Merge + dedup + source/URL skip filters
├── report.py            # HTML report generator
├── requirements.txt     # Python dependencies
├── start_cdp.sh         # Chrome CDP launcher (Linux)
├── scrapers/            # Individual scraper modules
│   ├── base.py
│   ├── google_jobs.py
│   ├── fuzu.py
│   ├── pigiame.py
│   ├── brightermonday.py
│   ├── codingkenya.py
│   ├── ...
│   ├── playwright_base.py
│   └── scanned_pages.py
├── data/
│   └── jobs.db          # SQLite database (auto-created)
└── context/             # Scraper documentation
```
