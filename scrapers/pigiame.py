import logging
import re
import requests
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from .base import ScraperBase
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned
from .playwright_base import auto_page

lgr = logging.getLogger()


class PigiaMe(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.base_url = 'https://www.pigiame.co.ke'
        self.scrape_data = []
        self.name = "PigiaMe"
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
        base = f'{self.base_url}/jobs?q={quote(keyword)}&sort=latest'
        if page <= 1:
            return base
        return f'{base}&page={page}'

    def _fetch_page(self, url):
        try:
            with auto_page() as page:
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(2000)
                html = page.content()
                if len(html) > 1000:
                    return html
        except Exception as e:
            lgr.info(f"Playwright failed ({e}), falling back to requests")
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if resp.status_code == 200 and len(resp.text) > 1000:
                return resp.text
        except Exception:
            pass
        return None

    def _parse_date(self, text):
        text = text.strip()
        if not text:
            return None
        today = datetime.now()

        if text.startswith('Today'):
            return today

        if text.startswith('Yesterday'):
            return today - timedelta(days=1)

        m = re.match(r'(\d+)\s+days?\s+ago', text, re.I)
        if m:
            return today - timedelta(days=int(m.group(1)))

        m = re.match(r"(\d+)\.\s*(\w+)\s+'(\d+),\s*(\d+:\d+)", text)
        if m:
            day, mon, yr_short = m.group(1), m.group(2), m.group(3)
            year = 2000 + int(yr_short)
            try:
                return datetime.strptime(f"{day} {mon} {year}", '%d %b %Y')
            except ValueError:
                try:
                    return datetime.strptime(f"{day} {mon} {year}", '%d %B %Y')
                except ValueError:
                    pass

        days_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
        }
        for name, idx in days_map.items():
            if text.lower().startswith(name):
                current = today.weekday()
                days_ago = (current - idx) % 7
                if days_ago == 0:
                    days_ago = 7
                return today - timedelta(days=days_ago)

        return None

    def _page_all_old(self, soup):
        if self.days_limit <= 0:
            return False
        cutoff = datetime.now() - timedelta(days=self.days_limit)
        cards = soup.find_all('div', class_='listing-card')
        if not cards:
            return True
        for card in cards:
            date_el = card.find('div', class_='listing-card__header__date')
            if not date_el:
                continue
            d = self._parse_date(date_el.get_text())
            if d and d >= cutoff:
                return False
        return True

    def _extract_location(self, card):
        loc_el = card.find('div', class_='listing-card__header__location')
        if loc_el:
            text = ' '.join(loc_el.get_text(strip=True).split())
            if text:
                return text
        a = card.find('a', class_='listing-card__inner')
        if a and a.get('data-t-listing_location_title'):
            return a['data-t-listing_location_title'].strip()
        return ''

    def scrape(self):
        lgr.info(f"Scraping {self.name}")

        seen_urls = {}
        queries = list(dict.fromkeys(self.keywords)) if self.keywords else []
        queries = list(dict.fromkeys(queries))

        for query in queries:
            for page in range(1, 100):
                page_url = self._search_url(query, page)
                html = self._fetch_page(page_url)
                if not html:
                    break
                soup = BeautifulSoup(html, 'lxml')

                body = soup.get_text()
                if "couldn't find a match" in body or "Did you mean" in body or "We're sorry." in body:
                    lgr.info(f"  Empty results for '{query}' page {page} — stopping")
                    break

                cards = soup.find_all('div', class_='listing-card')
                if not cards:
                    lgr.info(f"  No cards for '{query}' page {page}")
                    break

                if self.days_limit > 0 and self._page_all_old(soup):
                    lgr.info(f"  All jobs old on '{query}' page {page} \u2014 stopping")
                    break

                page_urls = []
                for card in cards:
                    a = card.find('a', class_='listing-card__inner')
                    if a and a.get('href'):
                        page_urls.append(a['href'])

                if not page_urls:
                    lgr.info(f"  No job links on '{query}' page {page} \u2014 stopping")
                    break

                unseen = [u for u in page_urls if u not in seen_urls]
                if not unseen:
                    lgr.info(f"  All {len(page_urls)} links already seen on '{query}' page {page} \u2014 stopping")
                    break

                url_hash = compute_url_hash(page_urls)
                if is_page_unchanged(self.name, page_url, url_hash):
                    lgr.info(f"  Page {page}: unchanged, skipping")
                    continue
                mark_page_scanned(self.name, page_url, url_hash)

                new_count = 0
                for card in cards:
                    a = card.find('a', class_='listing-card__inner')
                    if not a:
                        continue
                    url = a.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    title_el = card.find('div', class_='listing-card__header__title')
                    title = title_el.get_text(strip=True) if title_el else ''

                    company = ''
                    tags = card.find_all('span', class_=lambda c: c and 'employer' in (c or ''))
                    for tag in tags:
                        company = tag.get_text(strip=True)
                        if company:
                            break

                    location = self._extract_location(card)
                    date_el = card.find('div', class_='listing-card__header__date')

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

                lgr.info(f"  '{query}' page {page}: {len(cards)} items, {new_count} new")

        self.scrape_data = list(seen_urls.values())
        self.scrape_data = self._keyword_filter(self.scrape_data, self.keywords)
        lgr.info(f"PigiaMe: {len(self.scrape_data)} jobs")
        return self.scrape_data
