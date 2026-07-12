# JobSpy LinkedIn Scraper

**File**: `run.py` (function `run_jobspy_scrapers`)  
**Library**: [python-jobspy](https://github.com/Bunsly/JobSpy)  
**Source site**: LinkedIn (via JobSpy)

## What it scrapes
LinkedIn job listings matching the keyword search. Each job yields:
- `title`, `company`, `location`, `url`, `date_posted` (ISO), `source` (site), `description`

## URL format
JobSpy handles the API internally — no direct URL construction. Configured via:
```python
scrape_jobs(
    site_name=["linkedin"],
    search_term="{ OR-ed keywords }",
    location="Kenya",
    is_remote=True,  # or False
    results_wanted=30,
    hours_old=N,
    offset=N,
)
```

## Pagination
- Offset loop: `offset=0, 30, 60, ...` up to 300
- Stops when fewer than 30 results returned (no more pages)
- Runs for both remote=True and remote=False

## Data collection flow
1. **Search term** — All keywords from config OR-ed together: `"software OR developer OR devops"`
2. **API call** — JobSpy's `scrape_jobs()` queries LinkedIn's internal API (no browser needed)
3. **Results** — Returns a pandas DataFrame with columns: `title`, `company`, `location`, `job_url`, `date_posted`, `site`, `description`, etc.
4. **Normalization** — `normalize.py:normalize_jobspy_row()` maps DataFrame columns to the common schema:
   - `url` ← `job_url`
   - `source` ← `site`
   - `date_posted` ← `date_posted` (already ISO from API)
5. **Merge** — Combined with Kenya scraper results via `normalize.py:merge_and_dedupe()` (dedup by URL)

## Key details
- Uses JobSpy library (not direct scraping) — no browser, no Playwright
- Default is remote-first (calls `is_remote=True` before `False`)
- 30 results per page, up to 10 pages (300 max per remote/onsite)
- LinkedIn may rate-limit — offset requests may return fewer than 30
- `hours_old` parameter (derived from `--days` flag) filters at the API level — only jobs within N hours are returned
- `date_posted` comes in ISO format from LinkedIn API — no conversion needed
