import hashlib
import logging
from datetime import datetime

lgr = logging.getLogger()

SHARED_FIELDS = ['title', 'company', 'location', 'url', 'date_posted', 'source', 'description', 'job_id']


def dedup_hash(job):
    key = f"{str(job.get('title', '')).lower()}|{str(job.get('company', '')).lower()}|{str(job.get('location', '')).lower()}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def normalize_jobspy_row(row):
    row = {k: v for k, v in row.items()}
    return {
        'title': str(row.get('title') or ''),
        'company': str(row.get('company') or ''),
        'location': str(row.get('location') or ''),
        'url': str(row.get('job_url') or ''),
        'date_posted': str(row.get('date_posted') or '')[:10],
        'source': f"JobSpy/{str(row.get('site', '')).capitalize()}" if row.get('site') else 'JobSpy',
        'description': str(row.get('description') or ''),
        'job_id': str(row.get('id') or ''),
    }


def normalize_kenya_row(row):
    return {
        'title': str(row.get('title') or ''),
        'company': str(row.get('company') or ''),
        'location': str(row.get('location') or ''),
        'url': str(row.get('url') or '') or str(row.get('job_link') or ''),
        'date_posted': str(row.get('date_posted') or ''),
        'source': str(row.get('source') or 'Kenya'),
        'description': str(row.get('description') or row.get('desc') or ''),
        'job_id': str(row.get('job_id') or ''),
    }


SKIP_SOURCES = {'bebee', 'whatjobs', 'cosmoquick'}
SKIP_URLS = {'greatkenyanjobs.com', 'bebee.com', 'cosmoquick.com', 'whatjobs.com'}


def _skip_source(job):
    src = str(job.get('source', '')).lower().strip()
    for skip in SKIP_SOURCES:
        if skip in src:
            return True
    return False


def _skip_url(job):
    url = str(job.get('url', '')).lower().strip()
    for skip in SKIP_URLS:
        if skip in url:
            return True
    return False


def merge_and_dedupe(kenya_jobs, jobspy_jobs):
    seen = {}
    merged = []

    for job in kenya_jobs:
        if _skip_source(job) or _skip_url(job):
            continue
        normalized = normalize_kenya_row(job)
        h = dedup_hash(normalized)
        if h not in seen:
            seen[h] = normalized
            merged.append(normalized)

    for _, row in jobspy_jobs.iterrows():
        normalized = normalize_jobspy_row(row.to_dict())
        if _skip_source(normalized) or _skip_url(normalized):
            continue
        h = dedup_hash(normalized)
        if h not in seen:
            seen[h] = normalized
            merged.append(normalized)

    lgr.info(f"Kenya jobs: {len(kenya_jobs)}, JobSpy jobs: {len(jobspy_jobs)}, Merged deduped: {len(merged)}")
    return merged
