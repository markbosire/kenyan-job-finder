import logging
import re
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base import ScraperBase
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned

lgr = logging.getLogger()


class BrighterMonday(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.base_url = 'https://www.brightermonday.co.ke'
        self.scrape_data = []
        self.name = "BrighterMonday"
        self.days_limit = self.config.get('days_limit', 0)

    @staticmethod
    def _clean(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())

    def _keyword_filter(self, jobs, query_keywords):
        clean_kws = [self._clean(k) for k in query_keywords if self._clean(k)]
        if not clean_kws:
            return jobs
        filtered = []
        for job in jobs:
            clean_title = self._clean(job.get('title', ''))
            if any(kw in clean_title for kw in clean_kws):
                filtered.append(job)
        if len(jobs) != len(filtered):
            lgr.info(f"  Title filter: {len(jobs)} -> {len(filtered)} kept")
        return filtered

    def _search_url(self, keyword, page):
        base = f'{self.base_url}/jobs?q={quote(keyword)}'
        if page <= 1:
            return base
        return f'{base}&page={page}'

    def _parse_date(self, text):
        text = text.strip().lower()
        if not text:
            return None
        today = datetime.now()
        if text == 'today':
            return today
        if text == 'yesterday':
            return today - timedelta(days=1)
        m = re.match(r'(\d+)\s+(day|week|month)[s]?\s+ago', text)
        if m:
            num = int(m.group(1))
            unit = m.group(2)
            if unit == 'day':   return today - timedelta(days=num)
            if unit == 'week':  return today - timedelta(weeks=num)
            if unit == 'month': return today - timedelta(days=num * 30)
        return None

    def _page_all_old(self, soup):
        if self.days_limit <= 0:
            return False
        cutoff = datetime.now() - timedelta(days=self.days_limit)
        for el in soup.find_all('p', class_=lambda c: c and 'text-gray-700' in (c or '') and 'text-loading-animate' in (c or '')):
            d = self._parse_date(el.get_text())
            if d and d >= cutoff:
                return False
        return True

    def scrape(self):
        lgr.info(f"Scraping {self.name}")

        seen_urls = {}
        queries = list(dict.fromkeys(self.keywords)) if self.keywords else []
        queries = list(dict.fromkeys(queries))

        for query in queries:
            for page in range(1, 100):
                page_url = self._search_url(query, page)
                html = self.send_request(page_url)
                if not html:
                    break
                soup = BeautifulSoup(html, 'lxml')
                links = soup.find_all('a', attrs={'data-cy': 'listing-title-link'})
                if not links:
                    lgr.info(f"  No jobs for '{query}' page {page}")
                    break

                if self.days_limit > 0 and self._page_all_old(soup):
                    lgr.info(f"  All jobs old on '{query}' page {page} \u2014 stopping")
                    break

                page_urls = [l['href'] for l in links if l.get('href')]
                url_hash = compute_url_hash(page_urls)
                if is_page_unchanged(self.name, page_url, url_hash):
                    lgr.info(f"  Page {page}: unchanged, skipping")
                    continue
                mark_page_scanned(self.name, page_url, url_hash)

                new_count = 0
                for link in links:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    title_el = link.find('p')
                    title = title_el.get_text(strip=True) if title_el else ''
                    if not title:
                        continue

                    parent = link.parent.parent
                    company_el = parent.find('p', class_=lambda c: c and 'text-blue-700' in (c or ''))
                    company = company_el.get_text(strip=True) if company_el else ''

                    location = ''
                    flex_div = parent.find('div', class_=lambda c: c and 'flex-wrap' in (c or '') and 'mt-3' in (c or ''))
                    if flex_div:
                        spans = flex_div.find_all('span')
                        if spans:
                            location = spans[0].get_text(strip=True)

                    card = parent.parent.parent.parent
                    date_el = card.find('p', string=lambda s: s and re.search(r'\d+\s+(day|week|month)[s]?\s+ago', str(s)))
                    date_posted = ''
                    if date_el:
                        d = self._parse_date(date_el.get_text())
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

                lgr.info(f"  '{query}' page {page}: {len(links)} items, {new_count} new")

        self.scrape_data = list(seen_urls.values())
        self.scrape_data = self._keyword_filter(self.scrape_data, self.keywords)
        lgr.info(f"BrighterMonday: {len(self.scrape_data)} jobs")
        return self.scrape_data
