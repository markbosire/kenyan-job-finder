"""Async Playwright browser for parallel scraping (async API).

Connects to a local Chrome via CDP (port 9222).
Falls back to headless Playwright launch if CDP is unavailable.
"""

import asyncio

from ._playwright_common import (
    CDP_URL,
    _LAUNCH_ARGS,
    cdp_available,
    lgr,
)

_browser = None
_pw = None


async def _clear_browser():
    global _browser, _pw
    for obj in (_browser, _pw):
        if obj is not None:
            try:
                await obj.close()
            except Exception:
                pass
    _browser = None
    _pw = None


async def _get_browser():
    """Get a browser connection.

    If CDP is available, connects to that endpoint.
    Otherwise returns the singleton headless browser (fallback).
    """
    if cdp_available():
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(CDP_URL)
        lgr.info("Connected to CDP browser on port 9222 (async)")
        return browser, pw

    global _browser, _pw
    if _browser is not None:
        try:
            if _browser.is_connected():
                return _browser, _pw
        except Exception:
            pass
        await _clear_browser()

    from playwright.async_api import async_playwright
    _pw = await async_playwright().start()
    _browser = await _pw.chromium.launch(headless=True, args=_LAUNCH_ARGS)
    lgr.info("Launched headless async Playwright browser")
    return _browser, _pw


async def _fetch_with_context(browser, url, *, timeout):
    ctx = None
    try:
        ctx = await browser.new_context(
            service_workers="block",
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        page = await ctx.new_page()
        await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
        await page.wait_for_timeout(1500)
        html = await page.content()
        if len(html) > 1000:
            return html
    except Exception as e:
        lgr.info("Playwright attempt failed for %s: %s", url, e)
    finally:
        if ctx:
            await ctx.close()
    return None


async def fetch_page_html(url, *, timeout=15000, retries=2):
    """Fetch rendered HTML via Playwright.

    Uses CDP if available, otherwise headless launch.
    """
    browser, pw = await _get_browser()
    for attempt in range(1 + retries):
        html = await _fetch_with_context(browser, url, timeout=timeout)
        if html:
            return html
        if attempt < retries:
            await asyncio.sleep(1)
    return None
