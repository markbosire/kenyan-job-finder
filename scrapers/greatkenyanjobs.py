import logging
import re
from bs4 import BeautifulSoup
from .base import ScraperBase
from .utils import get_job_id
from .playwright_base import auto_page

lgr = logging.getLogger()


class GreatKenyanJobs(ScraperBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        super().__init__(config)
        self.base_url = 'https://www.greatkenyanjobs.com'
        self.url = 'https://www.greatkenyanjobs.com'
        self.scrape_data = []
        self.name = "GreatKenyanJobs"

    def scrape(self):
        lgr.info(f"Scraping {self.name}")
        html = self._fetch_page(self.url)
        if not html:
            lgr.error("Failed to fetch GreatKenyanJobs")
            return []

        soup = BeautifulSoup(html, 'lxml')
        links = self._extract_links(soup)
        lgr.info(f"Found {len(links)} job links")

        seen = set()
        for job_url in links:
            if job_url in seen:
                continue
            seen.add(job_url)
            job = self._extract_job(job_url)
            if job:
                self.scrape_data.append(job)

        self.scrape_data = self.filter_by_keywords(self.scrape_data)
        return self.scrape_data

    def _fetch_page(self, url):
        try:
            with auto_page() as page:
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(3000)
                html = page.content()
                if len(html) > 1000:
                    return html
        except Exception as e:
            lgr.info(f"Playwright failed ({e}), trying requests")
        return self.send_request(url, 'get')

    def _extract_links(self, soup):
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(kw in href.lower() for kw in ['/job/', '/vacancy/', '/career/', '/position/']):
                if href.startswith('http'):
                    links.add(href)
                elif href.startswith('/'):
                    links.add(self.base_url + href)
        return list(links)

    def _extract_job(self, url):
        html = self._fetch_page(url)
        if not html:
            return None
        soup = BeautifulSoup(html, 'lxml')
        title = ''
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        if not title:
            title_el = soup.find(['h2', 'h3'], class_=lambda c: c and 'title' in (c or '').lower())
            if title_el:
                title = title_el.get_text(strip=True)
        if not title:
            return None
        text = soup.get_text()
        company = ''
        for line in text.split('\n'):
            line = line.strip()
            if re.search(r'(employer|company|organization)[:\s]+(.+)', line, re.I):
                m = re.search(r'(?:employer|company|organization)[:\s]+(.+)', line, re.I)
                if m:
                    company = m.group(1).strip()
                    break
        if not company and ' at ' in title:
            parts = re.split(r'\s+at\s+', title, flags=re.IGNORECASE)
            if len(parts) > 1:
                company = parts[-1].strip()
        location = ''
        for line in text.split('\n'):
            if re.search(r'location[:\s]+', line, re.I):
                m = re.search(r'location[:\s]+(.+)', line, re.I)
                if m:
                    location = m.group(1).strip()
                    break
        date_posted = ''
        for line in text.split('\n'):
            if re.search(r'(date|posted|closing)[:\s]+', line, re.I):
                m = re.search(r'(?:date|posted|closing)[:\s]+(.+)', line, re.I)
                if m:
                    date_posted = m.group(1).strip()[:10]
                    break
        description = soup.get_text(strip=True)[:1000]
        job_id = get_job_id(url, self.name) or ''
        return {
            'title': title, 'company': company, 'location': location,
            'url': url, 'date_posted': date_posted, 'source': self.name,
            'description': description, 'job_id': job_id,
        }