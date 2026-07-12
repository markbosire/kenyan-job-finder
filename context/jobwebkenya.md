# JobWebKenya Scraper

**File**: `scrapers/jobwebkenya.py`  
**Class**: `Jobwebkenya(ScraperBase)`  
**Source site**: [jobwebkenya.com](https://jobwebkenya.com)

## What it scrapes
Kenya tech job listings from JobWebKenya — **listing cards only**, no detail page fetches. Each job yields:
- `title`, `company`, `location`, `url`, `date_posted`, `source`, `description`

## URL format
Search + pagination via WordPress-style query params:
```
https://jobwebkenya.com/?s={keyword}
https://jobwebkenya.com/page/N/?s={keyword}
```

## Pagination
- Loops pages 1–100 per keyword
- Keywords taken from config, limited to first 3
- **Sequential stop**: pages are scanned one-by-one until ALL jobs on a page are older than `--days` limit (NOT binary search — results are NOT strictly date-sorted)
- **Page cache**: Each page's job URLs are hashed and stored in `scanned_pages.db`; unchanged pages are skipped
- When `days_limit == 0`, all pages up to 100 are scanned per keyword

## Data collection flow
1. **Search page** — `send_request()` fetches `/?s={keyword}` (3 retries with backoff)
2. **Card parsing** — Each job card from `ol.jobs > li`:
   - Title + URL from `div#titlo > strong > a`
   - Company from title text: split on `" at "` (e.g. `"Engineer at Company"` → `"Company"`)
   - Date from card text: regex `(\d{2}/\w{3}/\d{4})` parsed as `%d/%b/%Y` → ISO `YYYY-MM-DD`
   - Location from card text: regex `Location:\s*(.+)`
   - Description from `div#exc`
3. **Days filter** — Per-job inline check: if parsed date is older than `--days`, job is dropped
4. **No detail pages** — Listing card data is sufficient; user clicks through manually

## Key details
- Uses `requests` only — no Playwright dependency
- `send_request()` has 3 retries with exponential backoff
- `scanned_pages.db` stores per-page URL hashes for cache
- Date format on site: `DD/MMM/YYYY` (e.g. `08/Jul/2026`)
