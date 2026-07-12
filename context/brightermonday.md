## BrighterMonday

- **URL**: `https://www.brightermonday.co.ke/jobs?q={keyword}&page={N}`
- **Method**: requests only
- **Date format**: relative ("5 days ago", "1 month ago"), parsed to ISO
- **Stop condition**: `_page_all_old` — sequential scan, stops when all jobs on page are older than `days_limit`
- **Page cache**: `scanned_pages.py` (url hash dedup)
- **Keyword matching**: Alphanumeric-stripped title-only matching via `_keyword_filter()` at end of scrape (e.g. `dev-ops` matches `devops`). Strips `[^a-z0-9]` from both title and keywords for substring matching. Description matching avoided due to false positives.
- **No `filter_by_keywords()`** — server-side filtering in URL handles most of it; `_keyword_filter()` for additional precision
- **Selectors**:
  - `a[data-cy="listing-title-link"] > p` — title + URL
  - `p.text-blue-700` — company
  - first `span.rounded` in `div.flex-wrap.mt-3` — location
  - `p.text-sm.font-normal.text-gray-700` — date text
