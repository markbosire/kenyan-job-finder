#!/usr/bin/env python3
"""REST API for jobs + applied/ignored status. Single source of truth (SQLite).
Usage:
    python api.py [--db ./data/jobs.db] [--port 9090]
"""

import argparse
import base64
import json
import logging
import os
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

lgr = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

DB_PATH = None


def init_db(db_path):
    conn = sqlite3.connect(db_path)
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_status (
            url TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK(status IN ('applied', 'ignored')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')
    conn.commit()
    conn.close()
    lgr.info(f"Initialized DB: {db_path}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        lgr.info(f"{self.client_address[0]} - {fmt % args}")

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _serve_html(self):
        html_path = os.path.join(os.path.dirname(__file__), 'data', 'index.html')
        try:
            with open(html_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._send_json({'error': 'report.html not found'}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self._serve_html()
        elif parsed.path == '/api/jobs':
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                SELECT j.url, j.title, j.company, j.location, j.date_posted,
                       j.source, j.description, s.status
                FROM jobs j
                LEFT JOIN job_status s ON j.url = s.url
                ORDER BY j.last_seen DESC, j.date_posted DESC
            ''')
            rows = c.fetchall()
            conn.close()
            jobs = [{
                'url': r[0], 'title': r[1], 'company': r[2],
                'location': r[3], 'date_posted': r[4], 'source': r[5],
                'description': r[6], 'status': r[7],
            } for r in rows]
            self._send_json(jobs)
        elif parsed.path == '/api/status':
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT url, status FROM job_status')
            result = {}
            for url, st in c.fetchall():
                key = base64.b64encode(f"{url}|".encode('utf-8')).decode('ascii')
                result[key] = st
            conn.close()
            self._send_json(result)
        else:
            self._send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/status':
            self._send_json({'error': 'Not found'}, 404)
            return

        length = int(self.headers.get('Content-Length', 0))
        if not length:
            self._send_json({'error': 'No data'}, 400)
            return

        body = self.rfile.read(length).decode('utf-8')
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON'}, 400)
            return

        raw_url = data.get('url', '')
        key = data.get('key', '')
        status = data.get('status')

        # Derive URL from key if not provided directly
        if not raw_url and key:
            try:
                decoded = base64.b64decode(key).decode('utf-8', errors='replace')
                raw_url = decoded.split('|')[0]
            except Exception:
                pass

        if not raw_url:
            self._send_json({'error': 'Missing url'}, 400)
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        if status is None:
            c.execute('DELETE FROM job_status WHERE url = ?', (raw_url,))
            msg = 'cleared'
        elif status in ('applied', 'ignored'):
            c.execute('''
                INSERT INTO job_status (url, status, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(url) DO UPDATE SET status = excluded.status, updated_at = datetime('now')
            ''', (raw_url, status))
            msg = 'saved'
        else:
            conn.close()
            self._send_json({'error': f'Invalid status: {status}'}, 400)
            return

        conn.commit()
        conn.close()
        self._send_json({'ok': True, 'url': raw_url, 'status': status, 'action': msg})

    def do_PUT(self):
        self.do_POST()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api/status/'):
            raw_url = parsed.path[len('/api/status/'):]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('DELETE FROM job_status WHERE url = ?', (raw_url,))
            conn.commit()
            conn.close()
            self._send_json({'ok': True, 'url': raw_url, 'action': 'deleted'})
        else:
            self._send_json({'error': 'Not found'}, 404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='./data/jobs.db')
    parser.add_argument('--port', type=int, default=9090)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()

    global DB_PATH
    DB_PATH = os.path.abspath(args.db)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db(DB_PATH)

    server = HTTPServer((args.host, args.port), Handler)
    lgr.info(f"API running on http://{args.host}:{args.port}")
    lgr.info(f"  GET  /api/jobs    — all jobs with status")
    lgr.info(f"  GET  /api/status  — status dict (backward compat)")
    lgr.info(f"  POST /api/status  — set/clear status ({'{url, status}'})")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == '__main__':
    main()