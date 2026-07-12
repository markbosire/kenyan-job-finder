"""Shared configuration and utilities for Playwright browser management.

Used by both ``playwright_base.py`` (sync API) and ``async_playwright.py``
(async API).

CDP connection
--------------
Chrome is launched via ``start_cdp.sh`` (or manually) on port 9222.
Scrapers connect to ``CDP_URL`` via ``connect_over_cdp``.
"""

import logging
import os
import subprocess
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

lgr = logging.getLogger()

CDP_URL = "http://localhost:9222"
CDP_PORT = 9222

_LAUNCH_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-setuid-sandbox',
    '--disable-accelerated-2d-canvas',
]

CAPTCHA_SITES = {"myjobmag.co.ke"}


def is_captcha_site(url):
    domain = urlparse(url).hostname or ''
    return any(site in domain for site in CAPTCHA_SITES)


_CAPTCHA_PATTERNS = [b'recaptcha', b'hcaptcha', b'challenge', b'cf-browser-verify']

def check_captcha(html, url=None):
    if not html:
        return False
    raw = html if isinstance(html, bytes) else html.encode('utf-8', errors='replace')
    for pattern in _CAPTCHA_PATTERNS:
        if pattern in raw.lower():
            loc = f" for {url}" if url else ""
            lgr.warning("CAPTCHA/challenge pattern '%s' detected in response%s", pattern.decode(), loc)
            return True
    return False


def _find_chrome():
    paths = [
        'google-chrome', 'google-chrome-stable',
        'chromium', 'chromium-browser',
        '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
        '/snap/bin/chromium',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ]
    for path in paths:
        try:
            subprocess.run([path, '--version'], capture_output=True, timeout=5)
            return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _kill_port(port):
    """Kill any process listening on *port*."""
    import signal
    for cmd in (
        ['fuser', '-k', f'{port}/tcp'],
        ['fuser', '-nk', str(signal.SIGKILL), f'{port}/tcp'],
        ['lsof', '-ti', f'tcp:{port}'],
    ):
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split()
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                        lgr.info("Killed process %s on port %s", pid, port)
                    except (OSError, ValueError):
                        pass
                time.sleep(1)
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue


def cdp_available(port=CDP_PORT):
    url = f"http://localhost:{port}/json/version"
    try:
        resp = urllib.request.urlopen(url, timeout=3)
        resp.read()
        return True
    except Exception:
        return False


def ensure_cdp(profile_dir=None, user_data_dir=None):
    """Kill anything on port 9222, then launch Chrome with CDP.

    Args:
        profile_dir: Profile name (e.g. ``'Profile 6'``). Requires ``user_data_dir`` to be the parent.
        user_data_dir: Path to Chrome's User Data parent directory (default ``/tmp/chrome_cdp_bot``).
                     Use ``~/.config/google-chrome`` for real profiles.
    """
    _kill_port(CDP_PORT)
    chrome = _find_chrome()
    if not chrome:
        lgr.warning("Chrome not found — cannot launch CDP")
        return False
    udd = user_data_dir or '/tmp/chrome_cdp_bot'
    lgr.info("Launching Chrome with CDP on port %s (user-data-dir: %s%s)",
             CDP_PORT, udd, f", profile: {profile_dir}" if profile_dir else "")
    cmd = [chrome, f'--remote-debugging-port={CDP_PORT}',
           f'--user-data-dir={udd}',
           '--no-sandbox', '--disable-dev-shm-usage',
           '--disable-gpu', '--disable-software-rasterizer']
    if profile_dir:
        cmd.append(f'--profile-directory={profile_dir}')
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(15):
        time.sleep(1)
        if cdp_available():
            lgr.info("CDP ready on port %s", CDP_PORT)
            return True
    lgr.warning("CDP not ready on port %s after 15s", CDP_PORT)
    return False
