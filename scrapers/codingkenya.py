import logging
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from .base import ScraperBase
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned
from .playwright_base import auto_page

lgr = logging.getLogger()


class CodingKenya(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.base_url = 'https://codingkenya.com'
        self.scrape_data = []
        self.name = "CodingKenya"
        self.days_limit = self.config.get('days_limit', 0)

    def _page_url(self, num):
        base = f'{self.base_url}/jobs/'
        if num <= 1:
            return f'{base}?posted_before=7-days'
        return f'{base}page/{num}/?posted_before=7-days'

    def _fetch_page(self, url):
        try:
            with auto_page() as page:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(3000)
                html = page.content()
                if len(html) > 1000:
                    return html
        except Exception as e:
            lgr.info(f"Playwright failed ({e}), falling back to requests")
        return self.send_request(url, 'get')

    def _parse_date(self, item):
        t = item.find('time')
        if t and t.get('datetime'):
            raw = t['datetime'][:10]
            try:
                return datetime.strptime(raw, '%Y-%m-%d')
            except ValueError:
                pass
        return None

    def scrape(self):
        lgr.info(f"Scraping {self.name}")

        seen_urls = {}
        for page in range(1, 100):
            page_url = self._page_url(page)
            html = self._fetch_page(page_url)
            if not html:
                break
            soup = BeautifulSoup(html, 'lxml')
            items = soup.find_all('li', class_='job_listing')
            if not items:
                lgr.info(f"  No jobs on page {page}")
                break

            page_urls = []
            for item in items:
                a = item.find('a')
                if a and a.get('href'):
                    page_urls.append(a['href'])

            url_hash = compute_url_hash(page_urls)
            if is_page_unchanged(self.name, page_url, url_hash):
                lgr.info(f"  Page {page}: unchanged, skipping")
                continue
            mark_page_scanned(self.name, page_url, url_hash)

            new_count = 0
            for item in items:
                a = item.find('a')
                if not a:
                    continue
                url = a.get('href', '')
                if not url or url in seen_urls:
                    continue

                title_el = item.find('h3', class_='job-listing-loop-job__title')
                title = title_el.get_text(strip=True) if title_el else ''

                company = ''
                company_div = item.find('div', class_='company')
                if company_div:
                    strong = company_div.find('strong')
                    if strong:
                        company = strong.get_text(strip=True)
                if not company:
                    img = item.find('img', class_='company_logo')
                    if img and img.get('alt'):
                        company = img['alt'].strip()

                loc_el = item.find('div', class_='job-location')
                location = loc_el.get_text(strip=True) if loc_el else ''

                date_posted = ''
                d = self._parse_date(item)
                if d:
                    date_posted = d.strftime('%Y-%m-%d')
                    if self.days_limit > 0 and d < datetime.now() - timedelta(days=self.days_limit):
                        continue

                seen_urls[url] = {
                    'title': title, 'company': company, 'location': location,
                    'url': url, 'date_posted': date_posted, 'source': self.name,
                    'description': '', 'job_id': '',
                }
                new_count += 1

            lgr.info(f"  Page {page}: {len(items)} items, {new_count} new")

        self.scrape_data = list(seen_urls.values())
        lgr.info(f"CodingKenya: {len(self.scrape_data)} jobs")
        return self.scrape_data
