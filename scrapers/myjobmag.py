import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
from .base import ScraperBase
from .utils import get_job_id
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned

lgr = logging.getLogger()


class MyJobMag(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.base_url = 'https://www.myjobmag.co.ke'
        self.scrape_data = []
        self.name = "MyJobMag"
        self.days_limit = self.config.get('days_limit', 0)

    def _parse_listing_date(self, date_str):
        date_str = date_str.strip()
        if not date_str:
            return None
        today = datetime.now()
        for fmt in ['%d %B', '%d %b']:
            try:
                d = datetime.strptime(date_str, fmt).replace(year=today.year)
                if d > today + timedelta(days=60):
                    d = d.replace(year=today.year - 1)
                return d
            except ValueError:
                continue
        return None

    def _is_old_from_listing(self, date_str):
        if self.days_limit <= 0 or not date_str:
            return False
        d = self._parse_listing_date(date_str)
        if d is None:
            return False
        return d < datetime.now() - timedelta(days=self.days_limit)

    def _date_to_iso(self, date_str):
        d = self._parse_listing_date(date_str)
        return d.strftime('%Y-%m-%d') if d else date_str

    def scrape(self):
        lgr.info(f"Scraping {self.name}")

        seen_urls = {}
        queries = list(dict.fromkeys(self.keywords)) if self.keywords else []
        queries = list(dict.fromkeys(queries))

        for query in queries:
            consecutive_unchanged = 0
            for page in range(1, 100):
                search_url = f'{self.base_url}/search?q={quote(query)}&currentpage={page}'
                res = self.send_request(search_url, 'get')
                if not res:
                    break
                soup = BeautifulSoup(res, 'lxml')
                items = soup.find_all('li', class_='job-list-li')
                if not items:
                    lgr.info(f"  No more results for '{query}' at page {page}")
                    break

                page_urls = []
                for item in items:
                    a_tag = item.find('h2')
                    if not a_tag:
                        continue
                    a = a_tag.find('a')
                    if not a:
                        continue
                    url = self.base_url + a['href'] if a['href'].startswith('/') else a['href']
                    page_urls.append(url)

                url_hash = compute_url_hash(page_urls)
                if is_page_unchanged(self.name, search_url, url_hash):
                    consecutive_unchanged += 1
                    if consecutive_unchanged >= 2:
                        lgr.info(f"  Two consecutive unchanged pages — stopping '{query}'")
                        break
                    continue

                consecutive_unchanged = 0
                mark_page_scanned(self.name, search_url, url_hash)

                new_count = 0
                for item in items:
                    title_el = item.find('h2')
                    if not title_el:
                        continue
                    a_tag = title_el.find('a')
                    if not a_tag:
                        continue
                    url = self.base_url + a_tag['href'] if a_tag['href'].startswith('/') else a_tag['href']
                    if url in seen_urls:
                        continue

                    title = title_el.get_text(strip=True)
                    if not title:
                        continue

                    date_el = item.find('li', id='job-date')
                    date_posted = date_el.get_text(strip=True) if date_el else ""

                    if self._is_old_from_listing(date_posted):
                        continue

                    company = self._extract_company(item, title)
                    desc_el = item.find('li', class_='job-desc')
                    desc_snippet = desc_el.get_text(strip=True) if desc_el else ""
                    location = self._extract_location(item)
                    job_id = get_job_id(url, self.name) or ""

                    seen_urls[url] = {
                        'title': title, 'company': company, 'location': location,
                        'url': url, 'date_posted': self._date_to_iso(date_posted),
                        'source': self.name, 'description': desc_snippet, 'job_id': job_id,
                    }
                    new_count += 1

                lgr.info(f"  '{query}' page {page}: {len(items)} items, {new_count} new")

        self.scrape_data = list(seen_urls.values())
        lgr.info(f"MyJobMag: {len(self.scrape_data)} jobs")
        return self.scrape_data

    def _extract_company(self, item, title):
        company_el = item.find('li', class_='job-logo')
        if company_el:
            img = company_el.find('img')
            if img and img.get('alt') and img['alt'].strip():
                return img['alt'].strip()
            a_tag = company_el.find('a')
            if a_tag:
                path = urlparse(a_tag['href']).path
                if '/jobs-at/' in path:
                    return path.replace('/jobs-at/', '').replace('-', ' ').title()
        m = re.search(r'\bat\s+(.+)$', title)
        return m.group(1).strip() if m else ""

    def _extract_location(self, item):
        text = item.get_text()
        m = re.search(r'Location[:\s]+(\w+(?:\s+\w+)?)', text)
        if m:
            return m.group(1).strip()
        title_el = item.find('h2')
        if title_el:
            m = re.search(r'[–—]\s*(.+)$', title_el.get_text())
            if m:
                return m.group(1).strip()
        return ""
