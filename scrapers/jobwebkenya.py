import logging
import re
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base import ScraperBase
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned

lgr = logging.getLogger()


class Jobwebkenya(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.base_url = 'https://jobwebkenya.com'
        self.scrape_data = []
        self.name = "Jobwebkenya"
        self.days_limit = self.config.get('days_limit', 0)

    def _search_url(self, keyword, page):
        if page <= 1:
            return f'{self.base_url}/?s={quote(keyword)}'
        return f'{self.base_url}/page/{page}/?s={quote(keyword)}'

    def _fetch_page_soup(self, url):
        html = self.send_request(url)
        if not html:
            return None
        return BeautifulSoup(html, 'lxml')

    def _parse_date(self, text):
        m = re.search(r'(\d{2}/\w{3}/\d{4})', text)
        if m:
            try:
                return datetime.strptime(m.group(1), '%d/%b/%Y')
            except ValueError:
                pass
        return None

    def _page_all_old(self, soup):
        if self.days_limit <= 0:
            return False
        cutoff = datetime.now() - timedelta(days=self.days_limit)
        job_list = soup.find('ol', class_='jobs')
        if not job_list:
            return True
        items = job_list.find_all('li', recursive=False)
        if not items:
            return True
        for item in items:
            d = self._parse_date(item.get_text())
            if d and d >= cutoff:
                return False
        return True

    def _extract_company(self, title):
        m = re.search(r'\s+at\s+(.+)$', title, re.IGNORECASE)
        return m.group(1).strip() if m else ''

    def _extract_location(self, item_text):
        m = re.search(r'Location:\s*(.+)', item_text)
        return m.group(1).strip() if m else ''

    def scrape(self):
        lgr.info(f"Scraping {self.name}")

        seen_urls = {}
        queries = list(dict.fromkeys(self.keywords)) if self.keywords else []
        queries = list(dict.fromkeys(queries))

        for query in queries:
            for page in range(1, 100):
                page_url = self._search_url(query, page)
                soup = self._fetch_page_soup(page_url)
                if not soup:
                    break

                job_list = soup.find('ol', class_='jobs')
                if not job_list:
                    lgr.info(f"  No job list for '{query}' page {page}")
                    break

                items = job_list.find_all('li', recursive=False)
                if not items:
                    lgr.info(f"  No jobs for '{query}' page {page}")
                    break

                if self.days_limit > 0 and self._page_all_old(soup):
                    lgr.info(f"  All jobs old on '{query}' page {page} \u2014 stopping")
                    break

                page_urls = []
                for item in items:
                    titlo = item.find('div', id='titlo')
                    if not titlo:
                        continue
                    strong = titlo.find('strong')
                    if not strong:
                        continue
                    a = strong.find('a')
                    if a and a.get('href'):
                        page_urls.append(a['href'])

                url_hash = compute_url_hash(page_urls)
                if is_page_unchanged(self.name, page_url, url_hash):
                    lgr.info(f"  Page {page}: unchanged, skipping")
                    continue
                mark_page_scanned(self.name, page_url, url_hash)

                new_count = 0
                for item in items:
                    titlo = item.find('div', id='titlo')
                    if not titlo:
                        continue
                    strong = titlo.find('strong')
                    if not strong:
                        continue
                    a = strong.find('a')
                    if not a or not a.get('href'):
                        continue

                    url = a['href']
                    if url in seen_urls:
                        continue

                    title = a.get_text(strip=True)
                    if not title:
                        continue

                    company = self._extract_company(title)
                    item_text = item.get_text()

                    date_posted = ''
                    d = self._parse_date(item_text)
                    if d:
                        date_posted = d.strftime('%Y-%m-%d')
                        if self.days_limit > 0 and d < datetime.now() - timedelta(days=self.days_limit):
                            continue

                    location = self._extract_location(item_text)
                    desc_div = item.find('div', id='exc')
                    description = desc_div.get_text(strip=True) if desc_div else ''

                    seen_urls[url] = {
                        'title': title, 'company': company, 'location': location,
                        'url': url, 'date_posted': date_posted, 'source': self.name,
                        'description': description, 'job_id': '',
                    }
                    new_count += 1

                lgr.info(f"  '{query}' page {page}: {len(items)} items, {new_count} new")

        self.scrape_data = list(seen_urls.values())
        lgr.info(f"Jobwebkenya: {len(self.scrape_data)} jobs")
        return self.scrape_data
