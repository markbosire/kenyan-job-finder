import logging
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from .base import ScraperBase
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned

lgr = logging.getLogger()


class CorporateStaffing(ScraperBase):
    BASE = 'https://www.corporatestaffing.co.ke'
    CATEGORY = 'it-jobs-in-kenya'

    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.scrape_data = []
        self.name = "CorporateStaffing"
        self.days_limit = self.config.get('days_limit', 0)

    def _page_url(self, num):
        if num <= 1:
            return f'{self.BASE}/category/{self.CATEGORY}/'
        return f'{self.BASE}/category/{self.CATEGORY}/page/{num}/'

    def _fetch_page_soup(self, url):
        html = self.send_request(url)
        if not html:
            return None
        return BeautifulSoup(html, 'lxml')

    def _parse_date(self, item):
        t = item.find('time', class_='entry-date published')
        if t and t.get('datetime'):
            raw = t['datetime'][:10]
            try:
                return datetime.strptime(raw, '%Y-%m-%d')
            except ValueError:
                pass
        return None

    def _page_all_old(self, soup):
        if self.days_limit <= 0:
            return False
        cutoff = datetime.now() - timedelta(days=self.days_limit)
        items = soup.find_all('li', class_='entry-list-item')
        if not items:
            return True
        for item in items:
            d = self._parse_date(item)
            if d and d >= cutoff:
                return False
        return True

    def _page_has_any_new(self, soup):
        if self.days_limit <= 0:
            return True
        cutoff = datetime.now() - timedelta(days=self.days_limit)
        items = soup.find_all('li', class_='entry-list-item')
        for item in items:
            d = self._parse_date(item)
            if d and d >= cutoff:
                return True
        return False

    def _find_boundary_page(self, max_page=250):
        if self.days_limit <= 0:
            return max_page
        low, high = 1, max_page
        while low <= high:
            mid = (low + high) // 2
            soup = self._fetch_page_soup(self._page_url(mid))
            if soup is None:
                high = mid - 1
                continue
            if self._page_has_any_new(soup):
                low = mid + 1
            else:
                high = mid - 1
        return high

    def _extract_company(self, title):
        m = re.search(r'\s+Job\s+(.+)$', title)
        if m:
            comp = m.group(1).strip()
            if not comp.startswith('('):
                return comp
        return ''

    def scrape(self):
        lgr.info(f"Scraping {self.name}")

        boundary = self._find_boundary_page()
        lgr.info(f"Date boundary: page {boundary}" + (f" ({self.days_limit}-day limit)" if self.days_limit > 0 else ""))

        max_pages = boundary if boundary > 0 else 0
        max_to_scan = min(max_pages, 250)

        seen_urls = {}
        for page in range(1, max_to_scan + 1):
            page_url = self._page_url(page)
            url_hash = compute_url_hash([page_url])
            if is_page_unchanged(self.name, page_url, url_hash):
                lgr.info(f"  Page {page}: unchanged, skipping")
                continue

            soup = self._fetch_page_soup(page_url)
            if not soup:
                break

            mark_page_scanned(self.name, page_url, url_hash)

            items = soup.find_all('li', class_='entry-list-item')
            if not items:
                break

            count = 0
            for item in items:
                title_el = item.find('h2', class_='entry-title')
                if not title_el:
                    continue
                a = title_el.find('a')
                if not a:
                    continue

                url = a.get('href', '')
                if url in seen_urls:
                    continue

                title = a.get_text(strip=True)
                if not title:
                    continue

                date_posted = ''
                d = self._parse_date(item)
                if d:
                    date_posted = d.strftime('%Y-%m-%d')
                    if self.days_limit > 0 and d < datetime.now() - timedelta(days=self.days_limit):
                        continue

                company = self._extract_company(title)
                desc_el = item.find('div', class_='entry-summary')
                description = desc_el.get_text(strip=True) if desc_el else ''

                seen_urls[url] = {
                    'title': title, 'company': company, 'location': '',
                    'url': url, 'date_posted': date_posted, 'source': self.name,
                    'description': description, 'job_id': '',
                }
                count += 1

            lgr.info(f"  Page {page}: {len(items)} items, {count} new")

        self.scrape_data = list(seen_urls.values())
        lgr.info(f"CorporateStaffing: {len(self.scrape_data)} jobs")
        return self.scrape_data
