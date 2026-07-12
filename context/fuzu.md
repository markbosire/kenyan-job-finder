# Fuzu Scraper

**File**: `scrapers/fuzu.py`  
**Class**: `Fuzu(ScraperBase)`  
**Source site**: [fuzu.com](https://www.fuzu.com)

## What it scrapes
Kenya tech job listings from Fuzu, filtered to Nairobi. Each job yields:
- `title`, `company`, `location`, `url`, `date_posted`, `source`

## URL format
Search + published filter + pagination via URL query params:
```
https://www.fuzu.com/kenya/job/nairobi?filters[term]={keyword}&filters[published]=month&page={N}
```
`filters[published]=month` limits results to jobs posted in the last 30 days.

## Pagination
- Loops pages 1–50 per keyword
- **Stops when ALL cards on a page say "Closed for applications" or "Expired"**
- Stops when all URLs on a page are already seen (URL dedup)
- Keywords taken from config, limited to first 5
- No page cache (sorts by relevance, content changes dynamically)

## Data collection flow
1. **Page load** — Uses Playwright via CDP (`auto_page()`) to load the JS-rendered page
2. **Card parsing** — Each `.b2c-card` parsed from the DOM HTML (BeautifulSoup):
   - **Title** — `<h2>` text
   - **Company** — 2nd direct child `<div>` text (skips empty and h2-matching divs)
   - **Location** — `location` attribute on the card, fallback to `.bWqTnA` div text
   - **URL** — `<h2> <a>` href attribute (slug-based): `/kenya/jobs/{slug}`
   - **Date** — Regex for `Posted: MMM D, YYYY` (e.g. `Posted: Jul 5, 2026`)
3. **Closed card filter** — Cards containing `"Closed for applications"` or `"Expired"` are skipped
4. **All-closed stop** — If every card on a page is closed, pagination ends
5. **No keyword filtering at the end** — search results already filtered at source

## Key details
- Requires Playwright + CDP (visible Chrome on port 9222)
- Page uses React — URL-encoded `filters[term]` works directly in URL
- Results always show `page=1` in URL (React cosmetic rewrite), but content changes correctly per page
- Job URL is slug-based (not the `job_id` parameter in the URL)
- `job_id` from the URL params is ignored — not used for dedup
- Dedup is by `url` (built from slug)
- No detail page fetching — only listing card data
