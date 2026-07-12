import logging
import re
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from .base import ScraperBase
from .playwright_base import auto_page
from .scanned_pages import compute_url_hash, is_page_unchanged, mark_page_scanned

lgr = logging.getLogger()


class Fuzu(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.base_url = 'https://www.fuzu.com'
        self.scrape_data = []
        self.name = "Fuzu"

    def _is_closed_card(self, card):
        t = card.get_text()
        return 'Closed for applications' in t or 'Expired' in t

    def scrape(self):
        lgr.info(f"Scraping {self.name}")

        base = f"{self.base_url}/kenya/job/nairobi"
        search_terms = list(dict.fromkeys(self.keywords)) if self.keywords else ['']

        with auto_page() as page:
            for kw in search_terms:
                term = urllib.parse.quote(kw)
                lgr.info(f"Fuzu search: '{kw}'")
                seen = set()
                consecutive_unchanged = 0
                for page_num in range(1, 51):
                    url = f"{base}?filters[term]={term}&filters[published]=week&page={page_num}"
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_timeout(3000)

                    html = page.content()
                    if len(html) <= 2000:
                        break

                    soup = BeautifulSoup(html, 'lxml')
                    cards = soup.find_all('div', class_=lambda c: c and 'b2c-card' in (c.split() if c else []))
                    if not cards:
                        break

                    all_closed = all(self._is_closed_card(c) for c in cards)
                    if all_closed:
                        lgr.info(f"  Page {page_num}: all {len(cards)} cards closed — stopping")
                        break

                    page_urls = []
                    for card in cards:
                        link = self._card_link(card)
                        if link:
                            page_urls.append(link)

                    url_hash = compute_url_hash(page_urls)
                    if is_page_unchanged(self.name, url, url_hash):
                        consecutive_unchanged += 1
                        if consecutive_unchanged >= 2:
                            lgr.info(f"  Page {page_num}: 2 consecutive unchanged pages — stopping")
                            break
                        lgr.info(f"  Page {page_num}: unchanged, skipping")
                        continue
                    else:
                        consecutive_unchanged = 0
                    mark_page_scanned(self.name, url, url_hash)

                    before = len(self.scrape_data)
                    for card in cards:
                        if self._is_closed_card(card):
                            continue
                        job = self._extract_card(card)
                        if job and job.get('title'):
                            self.scrape_data.append(job)

                    after = len(self.scrape_data)
                    new_this_page = after - before
                    lgr.info(f"  Page {page_num}: {len(cards)} cards, {new_this_page} new")

                    if new_this_page == 0:
                        break

                    links_this_page = set(j['url'] for j in self.scrape_data[before:after])
                    if links_this_page.issubset(seen):
                        break
                    seen.update(links_this_page)

        self._deduplicate()
        lgr.info(f"Found {len(self.scrape_data)} jobs on Fuzu")
        return self.scrape_data

    def _card_link(self, card):
        h2 = card.find('h2')
        if h2:
            a = h2.find('a')
            if a and a.get('href'):
                return a['href']
        return ''

    def _deduplicate(self):
        seen = set()
        unique = []
        for job in self.scrape_data:
            url = job.get('url', '')
            if url and url not in seen:
                seen.add(url)
                unique.append(job)
        self.scrape_data = unique

    def _extract_card(self, card):
        title_el = card.find('h2')
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title:
            return None

        link = title_el.find('a')
        job_url = link.get('href') if link else ''
        if job_url and not job_url.startswith('http'):
            job_url = self.base_url + job_url

        company = self._extract_company(card)

        location = card.get('location', '') or ''
        if not location:
            loc_el = card.find('div', class_=lambda c: c and 'bWqTnA' in (c or ''))
            if loc_el:
                location = loc_el.get_text(strip=True).replace('\n', ' ').replace('•', ',').strip()

        date_posted = self._extract_date(card)

        return {
            'title': title,
            'company': company,
            'location': location,
            'url': job_url,
            'date_posted': date_posted,
            'source': self.name,
        }

    def _extract_company(self, card):
        children = card.find_all(['div', 'h2'], recursive=False)
        for child in children:
            text = child.get_text(strip=True)
            if text and child.name == 'div':
                h2 = card.find('h2')
                if h2 and h2.get_text(strip=True) in text:
                    continue
                return text
        return ''

    def _extract_date(self, card):
        text = card.get_text()
        m = re.search(r'Posted:\s*(.+?)(?:\s*\d+\s*days?\s*left|\s*Closing\s*today|\s*Closed|\s*$)', text)
        if m:
            raw = m.group(1).strip()
            for fmt in ['%b %d, %Y', '%B %d, %Y']:
                try:
                    return datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
                except ValueError:
                    continue
            return raw
        m = re.search(r'(\d+\s+(day|week|month|hour|minute)[s]?\s+ago)', text, re.I)
        if m:
            return m.group(1)
        return ''
