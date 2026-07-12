import os
import csv
import pickle
import re
import requests
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from .utils import validate_and_parse_url, get_job_id

lgr = logging.getLogger()


def matches_keywords(text, keywords):
    if not keywords:
        return True
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False


class ScraperBase:
    def __init__(self, config=None):
        if config is None:
            config = {}
        self.config = config
        self.output_path = self.config.get('output_path')
        self.delay = self.config.get('delay', False)
        self.min_delay = self.config.get('delay_range', {}).get('min_delay', 0)
        self.max_delay = self.config.get('delay_range', {}).get('max_delay', 10)
        self.pickle_path = self.config.get("pickle_path")
        self.keywords = self.config.get('keywords', [])
        if isinstance(self.keywords, str):
            self.keywords = [kw.strip() for kw in self.keywords.split(',')]

    def scrape(self):
        raise NotImplementedError

    def filter_by_keywords(self, jobs):
        if not self.keywords:
            return jobs
        filtered = []
        for job in jobs:
            title = job.get('title', '') or ''
            description = job.get('description', '') or ''
            combined = title + ' ' + description
            if matches_keywords(combined, self.keywords):
                filtered.append(job)
        lgr.info(f'Keyword filter: {len(jobs)} -> {len(filtered)} jobs kept')
        return filtered

    def save_csv(self, scrape_data):
        try:
            if scrape_data and self.output_path:
                fieldnames = [
                    "title", "company", "location", "url", "date_posted",
                    "source", "description", "job_id"
                ]
                with open(os.path.join(self.output_path, "data.csv"), "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
                    writer.writeheader()
                    for row in scrape_data:
                        data = {k: row.get(k, '') for k in fieldnames}
                        writer.writerow(data)
                lgr.info(f"Saved {len(scrape_data)} results to {self.output_path}/data.csv")
                return True
        except Exception as e:
            lgr.error(f"Failed to save CSV: {e}")
        return False

    def load_csv(self):
        saved_data = []
        if not self.output_path:
            return saved_data
        filepath = os.path.join(self.output_path, "data.csv")
        if not os.path.exists(filepath):
            return saved_data
        try:
            with open(filepath, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    saved_data.append(dict(row))
        except Exception as e:
            lgr.error(f"Failed to load CSV: {e}")
        return saved_data

    def save_pickle(self, scrape_data):
        try:
            if scrape_data and self.pickle_path:
                with open(self.pickle_path, "wb") as f:
                    pickle.dump(scrape_data, f)
                lgr.info(f"Saved pickle at {self.pickle_path}")
                return True
        except Exception as e:
            lgr.error(f"Failed to save pickle: {e}")
        return False

    def load_pickle(self):
        scrape_data = []
        if not self.pickle_path:
            return scrape_data
        try:
            with open(self.pickle_path, "rb") as f:
                scrape_data = pickle.load(f)
            lgr.info(f"Loaded {len(scrape_data)} from pickle")
            return scrape_data
        except Exception:
            return scrape_data

    def recover_scraped_data(self):
        scraped_data = self.load_pickle()
        self.save_csv(scraped_data)

    def merge_scrape_data(self, scrape_data):
        try:
            if scrape_data:
                csv_data = self.load_csv()
                dups = {}
                for job in csv_data:
                    jid = job.get("job_id", "")
                    if jid:
                        dups[jid] = job
                for job in scrape_data:
                    jid = job.get("job_id", "")
                    if jid:
                        dups[jid] = job
                scrape_data = list(dups.values())
                return scrape_data
        except Exception as e:
            lgr.error(f"Failed to merge data: {e}")
        return scrape_data

    def run_pre_scrape_filters(self, job_links, source):
        if not self.output_path:
            return job_links
        filtered_links = []
        scraped_ids = {}
        for link in job_links:
            jid = get_job_id(link, source)
            if jid:
                scraped_ids[jid] = link
            else:
                scraped_ids[link] = link
        lgr.info(f'Parsed {len(scraped_ids)} ids from {len(job_links)} links')
        try:
            saved_ids = set()
            for job in self.load_csv():
                if job.get("source", "").lower() == source.lower():
                    jid = job.get("job_id", "")
                    if jid:
                        saved_ids.add(jid)
            filtered_links = [
                scraped_ids[jid] for jid in scraped_ids
                if jid not in saved_ids and jid is not None
            ]
            lgr.info(f'Scraping {len(filtered_links)} new links from {len(job_links)} total')
            return filtered_links
        except Exception as e:
            lgr.error(f"Failed to filter job_ids: {e}")
        return filtered_links

    @staticmethod
    def send_request(url, method='get', return_raw=False, retries=3):
        last_err = None
        for attempt in range(retries):
            try:
                ua = UserAgent()
                headers = {
                    'User-Agent': ua.random,
                    'Accept-Language': 'en-GB,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Referer': 'https://www.google.co.ke',
                }
                req = getattr(requests, method.lower(), requests.get)
                resp = req(url, headers=headers, timeout=15)
                status = resp.status_code
                if status != 200:
                    if 400 <= status < 500:
                        lgr.info(f'{method} {url} -> {status} (client error, not retrying)')
                        return None
                    lgr.info(f'{method} {url} -> {status}')
                    last_err = f'status {status}'
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                    continue
                return resp if return_raw else resp.text
            except requests.ConnectionError as e:
                last_err = f'Connection error: {e}'
            except requests.Timeout:
                last_err = f'Timeout: {url}'
            except requests.RequestException as e:
                last_err = f'Request failed: {e}'
            if attempt < retries - 1:
                lgr.info(f"  Retry {attempt+1}/{retries} for {url}")
                time.sleep(2 ** attempt)
        lgr.error(f"Failed after {retries} retries: {last_err}")
        return None

    def process_job_details(self, class_instance, target_method, job_links, **kwargs):
        if not job_links:
            return
        with ThreadPoolExecutor(max_workers=5) as executor:
            try:
                method_instance = getattr(class_instance, target_method)
            except AttributeError as e:
                lgr.error(f"Method {target_method} not found: {e}")
                return
            futures = [
                executor.submit(
                    method_instance, link,
                    delay=random.randrange(self.min_delay, self.max_delay) if self.delay else 0,
                    **kwargs
                ) for link in job_links
            ]
            for future in as_completed(futures):
                res = future.result()
                if res is not None:
                    getattr(class_instance, 'scrape_data').append(res)
