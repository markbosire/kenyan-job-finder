"""Playwright-based scraper base for JS-rendered sites (sync API).

Connects to a local Chrome via CDP (port 9222) launched by ``start_cdp.sh``.
Falls back to headless Playwright launch if CDP is unavailable.
"""

import threading
from contextlib import contextmanager

from ._playwright_common import (
    CDP_URL,
    _LAUNCH_ARGS,
    cdp_available,
    lgr,
)

_cdp_browser = None
_cdp_pw = None


def _close_cdp():
    global _cdp_browser, _cdp_pw
    for obj in (_cdp_browser, _cdp_pw):
        if obj is not None:
            try:
                obj.close()
            except Exception:
                pass
    _cdp_browser = None
    _cdp_pw = None


def _reconnect_cdp():
    global _cdp_browser, _cdp_pw
    _close_cdp()
    from playwright.sync_api import sync_playwright
    _cdp_pw = sync_playwright().start()
    _cdp_browser = _cdp_pw.chromium.connect_over_cdp(CDP_URL)
    lgr.info("Connected to CDP browser on port 9222")
    return _cdp_browser, _cdp_pw


def _ensure_headless_browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=_LAUNCH_ARGS)
    lgr.info("Launched headless Playwright browser")
    return browser, pw


def _get_browser():
    global _cdp_browser, _cdp_pw
    if _cdp_browser is not None:
        try:
            if _cdp_browser.is_connected():
                return _cdp_browser, _cdp_pw
        except Exception:
            pass
        _close_cdp()
    if not cdp_available():
        lgr.warning("CDP not available")
        return None, None
    return _reconnect_cdp()


def _make_context(browser):
    ctx = browser.new_context(
        service_workers="block",
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
    )
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return ctx, page


@contextmanager
def new_page():
    """Headless-launch page (fallback when no CDP)."""
    browser, pw = _ensure_headless_browser()
    ctx, page = _make_context(browser)
    try:
        yield page
    finally:
        ctx.close()
        browser.close()
        pw.stop()


@contextmanager
def cdp_page(url=None):
    """Page from CDP-connected Chrome.

    Falls back to headless if CDP is not available.
    """
    if not cdp_available():
        lgr.debug("CDP not available — using headless fallback")
        with new_page() as page:
            yield page
        return

    browser, pw = _get_browser()
    ctx, page = _make_context(browser)
    try:
        yield page
    finally:
        ctx.close()


@contextmanager
def auto_page(url=None):
    """Best-effort page for the given URL.

    Uses CDP if available, otherwise headless.
    """
    if cdp_available():
        with cdp_page(url) as page:
            yield page
    else:
        with new_page() as page:
            yield page


@contextmanager
def cdp_browser():
    """Legacy alias: same as new_page()."""
    with new_page() as page:
        yield page


@contextmanager
def playwright_browser(headless=True):
    """Legacy alias: same as new_page()."""
    with new_page() as page:
        yield page
