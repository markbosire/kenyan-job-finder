# CorporateStaffing Scraper

**File**: `scrapers/corporatestaffing.py`  
**Class**: `CorporateStaffing(ScraperBase)`  
**Source site**: [corporatestaffing.co.ke](https://www.corporatestaffing.co.ke)

## What it scrapes
Kenya IT job listings from CorporateStaffing — **listing cards only**, no detail page fetches. Each job yields:
- `title`, `company`, `location`, `url`, `date_posted`, `source`, `description`

## URL format
Category-based URL with pagination:
```
https://www.corporatestaffing.co.ke/category/it-jobs-in-kenya/
https://www.corporatestaffing.co.ke/category/it-jobs-in-kenya/page/N/
```

## Pagination
- **Binary search** via `_find_boundary_page()` — exploits the fact that results are strictly date-sorted
- Finds the last page containing any job within `--days` limit using binary search over pages 1–250
- Scans pages 1..boundary sequentially
- When `days_limit == 0`, scans up to 250 pages
- **Page cache**: Each page's job URLs hashed in `scanned_pages.db`; unchanged pages skipped

## Data collection flow
1. **Binary search** — `_find_boundary_page()` does O(log N) fetches to find the page boundary
2. **Sequential scan** — Pages 1..boundary fetched via `send_request()`
3. **Card parsing** — Each item from `li.entry-list-item`:
   - Title + URL from `h2.entry-title > a`
   - Company from title: regex `r'\s+Job\s+(.+)$'` (title format: `"Title Job Company"`)
   - Date from `time.entry-date.published[datetime]` attribute (ISO format, e.g. `2025-03-25T...`)
   - Description from `div.entry-summary`
4. **Days filter** — Per-job inline check against parsed datetime
5. **No detail pages** — Listing card data is sufficient; user clicks through manually

## Key details
- Uses `requests` only — no Playwright dependency
- `send_request()` has 3 retries with exponential backoff
- `scanned_pages.db` stores per-page URL hashes for cache
- Binary search is safe because results are published in date-descending order
