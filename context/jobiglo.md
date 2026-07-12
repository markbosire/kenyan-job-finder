# Jobiglo Scraper

**File**: `scrapers/jobiglo.py`
**Class**: `Jobiglo(ScraperBase)`
**Source site**: [ke.jobiglo.com](https://ke.jobiglo.com)

## What it scrapes
Kenya job listings from Jobiglo — **listing cards only**, no detail page fetches. Each job yields:
- `title`, `company`, `url`, `date_posted`, `source`

## URL format
Keyword converted to URL slug + date sort + pagination:
```
https://ke.jobiglo.com/{slug}-jobs?sort=date
https://ke.jobiglo.com/{slug}-jobs?sort=date&page=N
```

`sort=date` orders results by most recent first (roughly sorted, not strict).
Slug: keyword spaces → hyphens, append `-jobs` (e.g. `"software developer"` → `/software-developer-jobs`).

## Pagination
- Loops pages 1–100 per keyword
- Keywords taken from config, limited to first 3
- **Date-based stop**: Sequential pages scanned until ALL jobs on a page are older than `--days` limit
- **Page cache**: Each page's job URLs are hashed and stored in `scanned_pages.db`; unchanged pages are skipped

## Data collection flow
1. **Page load** — Uses `requests` via `send_request()` with 3 retries
2. **Card parsing** — Each `div.bg-white.rounded-xl.shadow-sm.p-5` from listing HTML:
   - Title from `h3 > a` text
   - Company from `p.text-gray-500` text
   - URL from `h3 > a[href]`
3. **Date parsing** — `span.text-xs.text-gray-400` text converted to ISO:
   - `"New"` → today
   - `"X hours ago"` → relative
   - `"X days ago"` → relative
   - `"X weeks ago"` → relative
   - `"X months ago"` → relative
4. **Days filter** — Per-job inline check after date parsing; stop-when-all-old on each page
5. **No detail pages** — Listing card data is sufficient

## Key details
- Uses `requests` only (no Playwright/CDP needed)
- Results are NOT strictly date-sorted → sequential pagination, not binary search
- Generous timeout (default `send_request()` 15s + 3 retries)
- Company and date are in separate `<p>` / `<span>` elements
- Location field always empty (not available on listing cards)
