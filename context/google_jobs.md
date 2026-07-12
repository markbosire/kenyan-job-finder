# Google Jobs Scraper

**File**: `scrapers/google_jobs.py`  
**Class**: `GoogleJobs(ScraperBase)`  
**Source site**: Google Search (`ibp=htl;jobs`)

## What it scrapes
Job listings from Google's job search results. Each job yields:
- `title`, `company`, `location`, `url`, `date_posted` (ISO), `source`, `description`, `job_id`

## URL format
Google Jobs search via URL:
```
https://www.google.com/search?q={keyword}&ibp=htl;jobs&hl=en
```

## Pagination
- Uses `<infinity-scrolling>` component — scrolls the container to trigger lazy loading
- Scrolls up to 30 times, stops when no new cards appear after a scroll
- Keywords taken from config, limited to first 15

## Data collection flow
1. **Page load** — Uses Playwright via CDP, uses **existing browser context** (not a new one) to avoid CAPTCHA
2. **Scroll** — `_scroll_all_jobs()` triggers `<infinity-scrolling>` + `window.scrollTo` in a loop
3. **Card parsing** — Each `div[jscontroller="b11o3b"]` parsed via Playwright selectors:
   - **Docid** — Extracted from `<template>` id attribute (strip leading "j")
   - **Title** — `.tNxQIb.PUpOsf` selector
   - **Company** — `.wHYlTd.MKCbgd.a3jPc` selector
   - **Location** — `.wHYlTd.FqK3wc.MKCbgd` selector
   - **Date** — Relative date regex (`"X days ago"`) → converted to ISO via `_relative_to_iso()`
4. **Template parsing** — Description and apply links extracted from `<template>` inner HTML via BeautifulSoup:
   - Description from `.OOyDTc` / `.ejCXj` selectors
   - Apply URL from `a.brKmxb[href]` links (unwraps Google redirect URLs)
5. **No keyword filtering at the end** — search results already filtered at source

## Key details
- Requires Playwright + CDP (visible Chrome on port 9222)
- **Must use existing browser context** (`browser.contexts[0]`) — new contexts trigger Google CAPTCHA
- Uses the visible Chrome window's existing session (cookies, login)
- `data-encoded-docid` no longer exists on cards — docid is in template `id` attribute
- Dedup is by `job_id` (docid extracted from template)
- `check_captcha()` may false-positive on the word "challenge" in normal page content
- `date_posted` normalized to ISO format (`"2026-07-08"`) via `_relative_to_iso()`
