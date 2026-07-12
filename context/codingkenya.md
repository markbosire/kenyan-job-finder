# CodingKenya Scraper

**File**: `scrapers/codingkenya.py`  
**Class**: `CodingKenya(ScraperBase)`  
**Source site**: [codingkenya.com](https://codingkenya.com)

## What it scrapes
Kenya tech job listings from CodingKenya — **listing cards only**, no detail page fetches. Each job yields:
- `title`, `company`, `location`, `url`, `date_posted`, `source`

## URL format
Jobs listing with built-in date filter + pagination:
```
https://codingkenya.com/jobs/?posted_before=30-days
https://codingkenya.com/jobs/page/N/?posted_before=30-days
```

`posted_before=30-days` limits results server-side to the last 30 days.

## Pagination
- Loops pages 1–100 sequentially
- Stops when a page has no job listings
- **Page cache**: Each page's job URLs are hashed and stored in `scanned_pages.db`; unchanged pages are skipped
- No keywords needed — all tech jobs returned (no keyword filtering at source)

## Data collection flow
1. **Page load** — Uses Playwright via CDP (`auto_page()`) with 30s timeout + 3s post-load wait (site can be slow)
2. **Card parsing** — Each `li.job_listing` from listing HTML:
   - Title from `h3.job-listing-loop-job__title`
   - Company from `.job-listing-company.company strong` (fallback `img.company_logo[alt]`)
   - Location from `.job-location.location` text
   - Date from `time[datetime]` attribute (ISO format, e.g. `2026-07-06`)
   - URL from wrapping `<a>` href
3. **Days filter** — Inline safety net (URL already limits to 30 days server-side)
4. **No detail pages** — Listing card data is sufficient

## Key details
- Uses CDP Playwright (not `requests`) — site requires JS rendering
- Generous timeout (30s goto + 3s wait) for slow page loads
- Card data is clean: title, company, and date are in separate elements (no text parsing)
- Date is in ISO format directly from `datetime` attribute
