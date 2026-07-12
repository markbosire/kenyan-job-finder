import hashlib
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'scanned_pages.db')


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS scanned_pages (
            scraper TEXT NOT NULL,
            page_url TEXT NOT NULL,
            url_hash TEXT NOT NULL,
            last_scanned TEXT NOT NULL,
            PRIMARY KEY (scraper, page_url)
        )
    ''')
    conn.commit()
    return conn


def compute_url_hash(urls):
    sorted_urls = sorted(set(u for u in urls if u))
    h = hashlib.sha256()
    for u in sorted_urls:
        h.update(u.encode('utf-8'))
    return h.hexdigest()


def is_page_unchanged(scraper, page_url, url_hash):
    conn = _get_conn()
    row = conn.execute(
        'SELECT url_hash FROM scanned_pages WHERE scraper = ? AND page_url = ?',
        (scraper, page_url)
    ).fetchone()
    conn.close()
    return row is not None and row[0] == url_hash


def mark_page_scanned(scraper, page_url, url_hash):
    conn = _get_conn()
    conn.execute('''
        INSERT OR REPLACE INTO scanned_pages (scraper, page_url, url_hash, last_scanned)
        VALUES (?, ?, ?, ?)
    ''', (scraper, page_url, url_hash, datetime.now().isoformat(timespec='seconds')))
    conn.commit()
    conn.close()


def prune_old_entries(days=30):
    conn = _get_conn()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec='seconds')
    deleted = conn.execute('DELETE FROM scanned_pages WHERE last_scanned < ?', (cutoff,)).rowcount
    conn.commit()
    conn.close()
    if deleted:
        import logging
        logging.getLogger().info(f"Pruned {deleted} old scanned_pages entries")
