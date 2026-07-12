"""Google Jobs scraper using local Chrome via CDP.

Scrapes ``google.com/search?ibp=htl;jobs`` using stable CSS selectors
that do not change across sessions (no jsdata, jsaction, or hashed IDs).
"""

import logging
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse, parse_qs

from ._playwright_common import CDP_URL, check_captcha
from .base import ScraperBase
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned

lgr = logging.getLogger()

INSTRUCTIONS = """
====================================================================
  Google Jobs requires a real Chrome profile with CDP enabled.
  If auto-launch fails, start Chrome manually:
    google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_cdp_bot
  Then log into your Google account.
====================================================================
"""


class GoogleJobs(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.name = "GoogleJobs"
        self.scrape_data = []

    def scrape(self):
        lgr.info(f"Scraping {self.name}")
        try:
            return self._scrape_via_cdp()
        except Exception as e:
            lgr.error(f"{self.name} failed: {e}", exc_info=True)
            return []

    def _scrape_via_cdp(self):
        from playwright.sync_api import sync_playwright

        urls = self._build_search_urls()

        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for url in urls:
            lgr.info(f"  Loading: {url}")
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
            except Exception as e:
                lgr.info("  Page load failed (%s), skipping", e)
                continue
            page.wait_for_timeout(3000)

            check_captcha(page.content(), url)

            docid_hash = self._scroll_all_jobs(page)

            if is_page_unchanged(self.name, url, docid_hash):
                lgr.info(f"  Cache hit — skipping (same docids as last run)")
                continue
            mark_page_scanned(self.name, url, docid_hash)

            jobs = self._extract_jobs(page)
            before = len(jobs)
            jobs = self._filter_recent(jobs)
            if before != len(jobs):
                lgr.info(f"  Date filter: {before} -> {len(jobs)} (removed {before - len(jobs)} older than 7 days)")
            before = len(jobs)
            jobs = [j for j in jobs if 'codingkenya.com' not in j.get('url', '')]
            if before != len(jobs):
                lgr.info(f"  Domain filter: {before} -> {len(jobs)} (removed {before - len(jobs)} codingkenya.com)")
            self.scrape_data.extend(jobs)
            lgr.info(f"  -> {len(jobs)} jobs from {url}")

        pw.stop()
        return self.scrape_data

    def _build_search_urls(self):
        keywords = self.config.get('keywords', [])
        if isinstance(keywords, str):
            keywords = [kw.strip() for kw in keywords.split(',')]
        base = list(dict.fromkeys(keywords)) if keywords else ['software developer']
        return [f'https://www.google.com/search?q={quote(k)}+in+the+last+week&ibp=htl;jobs&hl=en' for k in base]

    def _scroll_all_jobs(self, page):
        scroll_hashes = []
        for _ in range(30):
            docids = []
            cards = page.query_selector_all('div[jscontroller="b11o3b"]')
            for card in cards:
                template = card.query_selector('template')
                if template:
                    tid = template.get_attribute('id') or ''
                    if tid.startswith('j'):
                        docids.append(tid[1:])
            h = compute_url_hash(docids)
            scroll_hashes.append(h)

            if len(scroll_hashes) >= 3:
                last3 = scroll_hashes[-3:]
                if len(set(last3)) == 1:
                    lgr.info(f"  3 consecutive scrolls unchanged — stopping ({len(cards)} cards)")
                    break

            page.evaluate("""
                () => {
                    const inf = document.querySelector('infinity-scrolling');
                    if (inf) inf.scrollIntoView({block: 'end'});
                    window.scrollTo(0, document.body.scrollHeight);
                }
            """)
            page.wait_for_timeout(2000)

        return scroll_hashes[-1] if scroll_hashes else ''

    def _extract_jobs(self, page):
        jobs = []
        seen_docids = set()

        cards = page.query_selector_all('div[jscontroller="b11o3b"]')
        if not cards:
            lgr.info("  No job cards found with primary selector")
            return []

        lgr.info(f"  Found {len(cards)} job cards")

        for card in cards:
            try:
                job = self._parse_card(card)
                if job:
                    docid = job.get('job_id', '')
                    if docid and docid in seen_docids:
                        continue
                    if docid:
                        seen_docids.add(docid)
                    jobs.append(job)
            except Exception as e:
                lgr.debug("  Skipping card: %s", e)
                continue

        return jobs

    @staticmethod
    def _relative_to_iso(date_str):
        if not date_str:
            return ''
        m = re.match(r'(?:Posted\s+)?(\d+)\s+(day|week|month|hour|minute)[s]?\s+ago', date_str, re.I)
        if m:
            num = int(m.group(1))
            unit = m.group(2).lower()
            now = datetime.now()
            if unit == 'hour':   d = now - timedelta(hours=num)
            elif unit == 'day':  d = now - timedelta(days=num)
            elif unit == 'week': d = now - timedelta(weeks=num)
            elif unit == 'month':d = now - timedelta(days=num * 30)
            elif unit == 'minute':d = now - timedelta(minutes=num)
            else: return date_str
            return d.strftime('%Y-%m-%d')
        return date_str

    @staticmethod
    def _filter_recent(jobs, days=7):
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.strftime('%Y-%m-%d')
        return [j for j in jobs if not j.get('date_posted') or j['date_posted'] >= cutoff_str]

    def _parse_card(self, card):
        template = card.query_selector('template')
        docid = ''
        if template:
            tid = template.get_attribute('id') or ''
            if tid.startswith('j'):
                docid = tid[1:]

        title_el = card.query_selector('.tNxQIb.PUpOsf')
        title = title_el.inner_text().strip() if title_el else ''

        company_el = card.query_selector('.wHYlTd.MKCbgd.a3jPc')
        company = company_el.inner_text().strip() if company_el else ''

        loc_el = card.query_selector('.wHYlTd.FqK3wc.MKCbgd')
        location = loc_el.inner_text().strip() if loc_el else ''

        card_text = card.inner_text()
        date_posted = ''
        for pat in [
            r'(?:Posted\s+)?(\d+\s+(day|week|month|hour|minute)[s]?\s+ago)',
        ]:
            m = re.search(pat, card_text, re.I)
            if m:
                date_posted = self._relative_to_iso(m.group(1))
                break

        apply_url = ''
        source = ''
        description = ''

        if template:
            try:
                content = template.inner_html()
                if content:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')

                    for sel in ['.OOyDTc', '.ejCXj']:
                        el = soup.select_one(sel)
                        if el:
                            t = el.get_text(strip=True)
                            if t:
                                description = (description + '\n' + t) if description else t

                    for a in soup.select('a.brKmxb[href]'):
                        href = a.get('href') or ''
                        if not href or href.startswith('#'):
                            continue
                        if 'google.com/url' in href or href.startswith('/url'):
                            q_param = parse_qs(urlparse(href).query).get('q')
                            if q_param:
                                href = q_param[0]
                        if not apply_url:
                            apply_url = href
                        title_attr = a.get('title') or ''
                        m = re.search(r'Apply on\s+(.+)', title_attr, re.I)
                        if m and not source:
                            source = m.group(1).strip()
                        if 'google.com' not in href:
                            break
            except Exception as e:
                lgr.debug("Error parsing template: %s", e)

        listing_url = apply_url or (f'https://google.com/jobs?docid={docid}' if docid else '')

        return {
            'title': title,
            'company': company,
            'location': location,
            'url': listing_url,
            'date_posted': date_posted,
            'source': source or self.name,
            'description': description,
            'job_id': docid,
        }
