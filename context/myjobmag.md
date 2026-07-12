# MyJobMag Scraper

**File**: `scrapers/myjobmag.py`  
**Class**: `MyJobMag(ScraperBase)`  
**Source site**: [myjobmag.co.ke](https://www.myjobmag.co.ke)

## What it scrapes
Kenya tech job listings from MyJobMag — **listing cards only**, no detail page fetches. Each job yields:
- `title`, `company`, `location`, `url`, `date_posted`, `source`, `description`, `job_id`

## URL format
Search + pagination via URL query params:
```
https://www.myjobmag.co.ke/search?q={keyword}&currentpage={page}
```

## Pagination
- Loops pages 1–100 per keyword (`currentpage=N`)
- Keywords taken from config, limited to first 3
- **Page cache**: Each page's job URLs are hashed and stored in `scanned_pages.db`. If 2 consecutive pages have unchanged hashes, pagination stops early (sorted by date, so content is stable)
- Ad cards (`#adbox`) inside `li.job-list-li` are skipped (no `<h2>`, no `#job-date`)

## Data collection flow
1. **Listing page** — `send_request()` fetches search results (3 retries with backoff)
2. **Card parsing** — Each result card parsed from the listings HTML:
   - Title + URL from `<h2>` link
   - Location from `Location:` text in card, or text after `–`/`—` in title
   - Company from `<img alt>` in `li.job-logo`, or `at CompanyName` in title
   - Date from `#job-date` (`"DD Mon"` — no year, inferred as current year, adjusted back 1 year if >60 days ahead)
3. **Days filter** — Listing date parsed with inferred year, jobs older than `--days` are dropped inline
4. **No detail pages** — Listing card data is sufficient; user clicks through manually

## Key details
- Uses `requests` only — no Playwright dependency
- `send_request()` has 3 retries with exponential backoff
- `scanned_pages.db` stores per-page URL hashes for cache; old entries can be pruned with `prune_old_entries(30)`
- No CAPTCHA issues (simple HTML scraper)
