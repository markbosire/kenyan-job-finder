import logging
import re
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base import ScraperBase
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned

lgr = logging.getLogger()


class Jobiglo(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.base_url = 'https://ke.jobiglo.com'
        self.scrape_data = []
        self.name = "Jobiglo"
        self.days_limit = self.config.get('days_limit', 0)

    def _search_url(self, keyword, page):
        slug = re.sub(r'\s+', '-', keyword.strip().lower())
        base = f'{self.base_url}/{slug}-jobs?city=Nairobi&sort=date'
        if page <= 1:
            return base
        return f'{base}&page={page}'

    def _parse_date(self, text):
        if not text:
            return None
        text = text.strip()
        today = datetime.now()
        if text.lower() == 'new':
            return today
        m = re.match(r'(\d+)\s+(hour|day|week|month)[s]?\s+ago', text, re.I)
        if m:
            num = int(m.group(1))
            unit = m.group(2).lower()
            if unit == 'hour':   return today - timedelta(hours=num)
            if unit == 'day':    return today - timedelta(days=num)
            if unit == 'week':   return today - timedelta(weeks=num)
            if unit == 'month':  return today - timedelta(days=num * 30)
        return None

    def _page_all_old(self, soup):
        if self.days_limit <= 0:
            return False
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=self.days_limit)
        cards = soup.find_all('div', class_=lambda c: c and 'rounded-xl' in (c or '') and 'shadow-sm' in (c or '') and 'p-5' in (c or ''))
        if not cards:
            return True
        for card in cards:
            date_el = card.find('span', class_=lambda c: c and 'text-xs' in (c or '') and 'text-gray-400' in (c or ''))
            if date_el:
                d = self._parse_date(date_el.get_text())
                if d and d.replace(hour=0, minute=0, second=0, microsecond=0) >= cutoff:
                    return False
                continue
            if card.find('span', string='New'):
                return False
        return True

    def scrape(self):
        lgr.info(f"Scraping {self.name}")

        seen_urls = {}
        queries = list(dict.fromkeys(self.keywords)) if self.keywords else []
        queries = list(dict.fromkeys(queries))

        for query in queries:
            consecutive_zero = 0
            for page in range(1, 100):
                page_url = self._search_url(query, page)
                html = self.send_request(page_url)
                if not html:
                    break
                soup = BeautifulSoup(html, 'lxml')
                cards = soup.find_all('div', class_=lambda c: c and 'rounded-xl' in (c or '') and 'shadow-sm' in (c or '') and 'p-5' in (c or ''))
                if not cards:
                    lgr.info(f"  No jobs for '{query}' page {page}")
                    break

                if self.days_limit > 0 and self._page_all_old(soup):
                    lgr.info(f"  All jobs old on '{query}' page {page} \u2014 stopping")
                    break

                page_urls = []
                for card in cards:
                    a = card.find('h3')
                    if a:
                        link = a.find('a')
                        if link and link.get('href'):
                            page_urls.append(link['href'])

                url_hash = compute_url_hash(page_urls)
                if is_page_unchanged(self.name, page_url, url_hash):
                    lgr.info(f"  Page {page}: unchanged, skipping")
                    consecutive_zero += 1
                    if consecutive_zero >= 2:
                        lgr.info(f"  2 consecutive unchanged pages \u2014 stopping")
                        break
                    continue
                else:
                    consecutive_zero = 0
                mark_page_scanned(self.name, page_url, url_hash)

                new_count = 0
                for card in cards:
                    h3 = card.find('h3')
                    if not h3:
                        continue
                    a = h3.find('a')
                    if not a:
                        continue
                    url = a.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    title = a.get_text(strip=True)
                    if not title:
                        continue

                    company_el = card.find('p', class_=lambda c: c and 'text-gray-500' in (c or ''))
                    company = company_el.get_text(strip=True) if company_el else ''

                    date_el = card.find('span', class_=lambda c: c and 'text-xs' in (c or '') and 'text-gray-400' in (c or ''))
                    date_posted = ''
                    if date_el:
                        d = self._parse_date(date_el.get_text())
                        if d:
                            date_posted = d.strftime('%Y-%m-%d')
                            if self.days_limit > 0 and d.replace(hour=0, minute=0, second=0, microsecond=0) < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=self.days_limit):
                                continue
                    elif card.find('span', string='New'):
                        date_posted = datetime.now().strftime('%Y-%m-%d')

                    seen_urls[url] = {
                        'title': title, 'company': company, 'location': '',
                        'url': url, 'date_posted': date_posted, 'source': self.name,
                        'description': '', 'job_id': '',
                    }
                    new_count += 1

                lgr.info(f"  '{query}' page {page}: {len(cards)} items, {new_count} new")

        self.scrape_data = list(seen_urls.values())
        lgr.info(f"Jobiglo: {len(self.scrape_data)} jobs")
        return self.scrape_data
