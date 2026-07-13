#!/usr/bin/env python3
"""
Kenyan Job Finder
Merges Kenyan job board scrapers + JobSpy into one pipeline.
Usage:
    python run.py --keywords devops,cloud,backend --days 7
    python run.py --keywords "software developer,devops" --days 3
"""
import argparse
import importlib
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta

try:
    from jobspy.model import Country
    member = object.__new__(Country)
    member._name_ = 'KENYA'
    member._value_ = ("kenya", "ke")
    Country._member_map_['KENYA'] = member
    Country._value2member_map_[("kenya", "ke")] = member
    @classmethod
    def _from_string_ke(cls, country_str):
        s = country_str.strip().lower()
        for c in cls:
            if s in c.value[0].split(","):
                return c
        return member if "kenya" in s else cls.WORLDWIDE
    Country.from_string = _from_string_ke
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
lgr = logging.getLogger()


def parse_args():
    parser = argparse.ArgumentParser(description='Kenyan Job Finder')
    parser.add_argument('--keywords', '-kw', type=str, default='software developer,full stack developer,frontend developer,backend developer,cloud engineer,DevOps engineer,site reliability engineer,platform engineer,data engineer,data scientist,AI engineer,machine learning engineer,solutions architect,IT support,junior developer,Python developer,JavaScript developer,Go developer,API developer,ui/ux,flutter developer,mobile developer',
                        help='Comma-separated keywords to filter jobs')
    parser.add_argument('--days', '-d', type=int, default=7,
                        help='Only keep jobs posted within this many days (0 = no filter)')
    parser.add_argument('--output', '-o', type=str, default='./data',
                        help='Output directory for results')
    parser.add_argument('--skip-jobspy', action='store_true',
                        help='Skip JobSpy scrapers (only Kenya scrapers)')
    parser.add_argument('--skip-kenya', action='store_true',
                        help='Skip Kenya scrapers (only JobSpy)')
    parser.add_argument('--nontech', action='store_true',
                        help='Skip keyword-less sources (CodingKenya, CorporateStaffing)')
    return parser.parse_args()


def run_kenya_scrapers(config, nontech=False):
    scraper_paths = [
        'scrapers.google_jobs.GoogleJobs',
        'scrapers.fuzu.Fuzu',
        'scrapers.myjobmag.MyJobMag',
        'scrapers.corporatestaffing.CorporateStaffing',
        'scrapers.jobwebkenya.Jobwebkenya',
        'scrapers.codingkenya.CodingKenya',
        'scrapers.pigiame.PigiaMe',
        'scrapers.jobiglo.Jobiglo',
        'scrapers.brightermonday.BrighterMonday',
    ]
    if nontech:
        skip = {'CorporateStaffing', 'CodingKenya'}
        scraper_paths = [p for p in scraper_paths if p.split('.')[-1] not in skip]
        lgr.info(f"Non-tech mode: excluding CorporateStaffing, CodingKenya ({len(scraper_paths)} scrapers)")

    all_jobs = []
    for class_path in scraper_paths:
        module_path, cls_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, cls_name)
        name = cls.__name__
        lgr.info(f"Starting {name}")
        try:
            instance = cls(config)
            jobs = instance.scrape()
            lgr.info(f"{name}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            lgr.error(f"{name} failed: {e}", exc_info=True)

    return all_jobs


def run_jobspy_scrapers(keywords, days):
    try:
        from jobspy import scrape_jobs
        import pandas as pd
    except ImportError:
        lgr.error("JobSpy not installed. Run: pip install python-jobspy")
        return pd.DataFrame()

    search_term = ' OR '.join(k.strip() for k in keywords.split(',') if k.strip())
    hours_old = days * 24 if days > 0 else None

    all_dfs = []

    for remote in [True, False]:
        try:
            for offset in range(0, 300, 30):
                lgr.info(f"JobSpy: linkedin remote={remote} offset={offset}")
                df = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=search_term,
                    location="Kenya",
                    is_remote=remote,
                    results_wanted=30,
                    hours_old=hours_old,
                    offset=offset,
                    verbose=0,
                )
                if df is not None and not df.empty:
                    n = len(df)
                    lgr.info(f"  -> {n} jobs")
                    all_dfs.append(df)
                    if n < 30:
                        break
                else:
                    break
        except Exception as e:
            lgr.info(f"  -> skipped (linkedin): {e}")

    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()


def init_db(conn):
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            url TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            date_posted TEXT,
            source TEXT,
            description TEXT,
            first_seen TEXT,
            last_seen TEXT
        )
    ''')
    try:
        c.execute('ALTER TABLE jobs ADD COLUMN job_id TEXT')
    except sqlite3.OperationalError:
        pass
    c.execute('CREATE INDEX IF NOT EXISTS idx_job_id ON jobs(job_id)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_status (
            url TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK(status IN ('applied', 'ignored')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')
    conn.commit()


def upsert_job(conn, job, now):
    """Insert or update a single job record.

    Lookup order:
      1. By ``job_id`` (Google's data-encoded-docid) if present
      2. By ``url``

    Returns 'inserted' or 'updated'.
    """
    c = conn.cursor()
    url = job.get('url', '') or ''
    job_id = job.get('job_id', '') or ''

    if not url and not job_id:
        lgr.debug("  Skipping job with no url and no job_id")
        return 'skipped'

    existing_url = None
    if job_id:
        c.execute('SELECT url FROM jobs WHERE job_id = ?', (job_id,))
        row = c.fetchone()
        if row:
            existing_url = row[0]
    if not existing_url and url:
        c.execute('SELECT url FROM jobs WHERE url = ?', (url,))
        row = c.fetchone()
        if row:
            existing_url = row[0]

    fields = {
        'title': job.get('title', '') or '',
        'company': job.get('company', '') or '',
        'location': job.get('location', '') or '',
        'date_posted': str(job.get('date_posted', '') or ''),
        'source': job.get('source', '') or '',
        'description': job.get('description', '') or '',
    }

    if existing_url:
        c.execute('''UPDATE jobs SET
            url=?, job_id=?, title=?, company=?, location=?, date_posted=?,
            source=?, description=?, last_seen=?
            WHERE url=?''', (
            url, job_id,
            fields['title'], fields['company'], fields['location'],
            fields['date_posted'], fields['source'], fields['description'],
            now, existing_url,
        ))
        lgr.debug("  Updated existing job %s (%s)", job_id or url, fields['source'])
        return 'updated'
    else:
        c.execute('''INSERT INTO jobs
            (url, job_id, title, company, location, date_posted, source, description, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            url, job_id,
            fields['title'], fields['company'], fields['location'],
            fields['date_posted'], fields['source'], fields['description'],
            now, now,
        ))
        lgr.debug("  Inserted new job %s (%s)", job_id or url, fields['source'])
        return 'inserted'


def store_in_sqlite(jobs, db_path):
    conn = sqlite3.connect(db_path)
    init_db(conn)

    conn.execute("DELETE FROM jobs WHERE LOWER(source) LIKE '%bebee%'")
    conn.execute("DELETE FROM jobs WHERE LOWER(source) LIKE '%whatjobs%'")
    conn.execute("DELETE FROM jobs WHERE LOWER(source) LIKE '%cosmoquick%'")
    conn.execute("DELETE FROM jobs WHERE url LIKE '%greatkenyanjobs.com%'")

    now = datetime.now().isoformat(timespec='seconds')
    counts = {'inserted': 0, 'updated': 0, 'skipped': 0}

    for job in jobs:
        action = upsert_job(conn, job, now)
        counts[action] += 1

    conn.commit()
    conn.close()
    lgr.info(f"SQLite: {counts['inserted']} new, {counts['updated']} updated in {db_path}")


def _parse_relative(dp):
    m = re.match(r'(?:Posted\s+)?(\d+)\s+(day|week|month|hour|minute)[s]?\s+ago', str(dp), re.I)
    if m:
        num = int(m.group(1))
        unit = m.group(2).lower()
        now = datetime.now()
        if unit == 'hour':   return now - timedelta(hours=num)
        if unit == 'day':    return now - timedelta(days=num)
        if unit == 'week':   return now - timedelta(weeks=num)
        if unit == 'month':  return now - timedelta(days=num * 30)
        if unit == 'minute': return now - timedelta(minutes=num)
    return None


def _parse_date_loose(dp):
    dp_str = str(dp)[:10]
    try:
        return datetime.strptime(dp_str, '%Y-%m-%d')
    except ValueError:
        pass
    d = _parse_relative(dp)
    if d is not None:
        return d
    from dateutil import parser as dateparser
    try:
        return dateparser.parse(str(dp), fuzzy=True)
    except (ValueError, TypeError):
        pass
    return None


def filter_by_days(jobs, days):
    if days <= 0:
        return jobs
    cutoff = datetime.now() - timedelta(days=days)
    filtered = []
    for job in jobs:
        dp = job.get('date_posted', '')
        if not dp:
            filtered.append(job)
            continue
        job_date = _parse_date_loose(dp)
        if job_date is None or job_date >= cutoff:
            filtered.append(job)
        else:
            continue
    return filtered


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    t_start = time.perf_counter()
    lgr.info("=" * 50)
    lgr.info("Kenyan Job Finder")
    lgr.info(f"Keywords: {args.keywords}")
    lgr.info(f"Days filter: {args.days}")
    lgr.info(f"Output: {args.output}")
    lgr.info("=" * 50)

    config = {
        'output_path': args.output,
        'keywords': args.keywords,
        'days_limit': args.days,
        'delay': True,
        'delay_range': {'min_delay': 1, 'max_delay': 4},
        'pickle_path': os.path.join(args.output, 'kenya_scrape.pkl'),
        'max_pages': 10,
    }

    lgr.info("Ensuring CDP Chrome is running...")
    from scrapers._playwright_common import ensure_cdp
    ensure_cdp()

    lgr.info("Running Kenya scrapers sequentially...")
    kenya_jobs = []
    if not args.skip_kenya:
        kenya_jobs = run_kenya_scrapers(config, nontech=args.nontech)

    jobspy_df = None
    if not args.skip_jobspy:
        lgr.info("Running JobSpy scrapers...")
        jobspy_df = run_jobspy_scrapers(args.keywords, args.days)

    if jobspy_df is None:
        import pandas as pd
        jobspy_df = pd.DataFrame()
    lgr.info(f"Scraping done: {len(kenya_jobs)} Kenya jobs + {len(jobspy_df)} JobSpy jobs")

    from normalize import merge_and_dedupe
    merged = merge_and_dedupe(kenya_jobs, jobspy_df)

    merged = filter_by_days(merged, args.days)

    store_in_sqlite(merged, './data/jobs.db')

    t_elapsed = time.perf_counter() - t_start
    source_counts = {}
    for job in merged:
        s = job.get('source', 'Unknown')
        source_counts[s] = source_counts.get(s, 0) + 1

    print()
    print("=" * 50)
    print(f"  Total unique jobs: {len(merged)}")
    print(f"  Time: {t_elapsed:.1f}s")
    print("  Per source:")
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"    {src}: {cnt}")
    print(f"  API:  python api.py --db ./data/jobs.db")
    print("=" * 50)


if __name__ == '__main__':
    main()
