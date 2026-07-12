# PigiaMe Scraper

**File**: `scrapers/pigiame.py`  
**Class**: `PigiaMe(ScraperBase)`  
**Source site**: [pigiame.co.ke](https://www.pigiame.co.ke)

## What it scrapes
Kenya job listings from PigiaMe — **listing cards only**, no detail page fetches. Each job yields:
- `title`, `company`, `location`, `url`, `date_posted`, `source`

## URL format
Search with date sort + pagination via URL query params:
```
https://www.pigiame.co.ke/jobs?q={keyword}&sort=latest
https://www.pigiame.co.ke/jobs?q={keyword}&sort=latest&page=N
```

`sort=latest` orders results by most recent first (roughly sorted, not strict).

## Pagination
- Loops pages 1–100 per keyword
- Keywords taken from config, limited to first 3
- **Date-based stop**: Sequential pages are scanned until ALL jobs on a page are older than `--days` limit
- **Page cache**: Each page's job URLs are hashed and stored in `scanned_pages.db`; unchanged pages are skipped
- Falls back to `max_pages` when `days_limit == 0`

## Data collection flow
1. **Page load** — Uses Playwright via CDP (`auto_page()`) with 20s timeout + 2s wait
2. **Card parsing** — Each `.listing-card` from listing HTML:
   - Title from `.listing-card__header__title`
   - Company from `.listing-card__header__tags__item--employer`
   - Location from `.listing-card__header__location` text (cleaned), fallback `data-t-listing_location_title`
   - URL from `a.listing-card__inner[href]`
3. **Date parsing** — `.listing-card__header__date` text converted to ISO:
   - `"Today, HH:MM"` → today
   - `"Yesterday, HH:MM"` → yesterday
   - `"Thursday"` (day-of-week) → most recent occurrence of that day
   - `"X days ago"` → relative
   - `"D. Mon 'YY, HH:MM"` → specific date (e.g. `30. Jan '23, 09:05`)
4. **Days filter** — Per-job inline check after date parsing; stop-when-all-old on each page
5. **No detail pages** — Listing card data is sufficient

## Key details
- Uses CDP Playwright (not `requests`) — site requires JS rendering
- Results are NOT strictly date-sorted → sequential pagination, not binary search
- Date formats are varied; all normalized to ISO `YYYY-MM-DD`
- Non-job listings (housing, services) may appear in results for broad keywords
