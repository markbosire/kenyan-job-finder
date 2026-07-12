# Browser Access & CDP Technique

## Architecture
All scrapers use Chrome's **Chrome DevTools Protocol (CDP)** on port **9222**. Playwright connects to a running Chrome instance via `connect_over_cdp()` instead of launching its own browser.

## Starting Chrome with CDP

### Automatic (via code)
`scrapers/_playwright_common.py:ensure_cdp()`:
1. Kills any process on port 9222 (`_kill_port()`)
2. Finds Chrome binary (google-chrome, chromium, etc.)
3. Launches Chrome **visibly** (no `--headless`) with `--remote-debugging-port=9222 --user-data-dir=/tmp/chrome_cdp_bot`
4. Waits up to 15s for CDP to respond
5. Called once at the start of `run.py`

### Manual (for debugging)
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_cdp_bot
```

### Shell script
```bash
./start_cdp.sh
```

## How scrapers connect

### Sync scrapers (Fuzu, Google Jobs, etc.)
```python
from scrapers.playwright_base import auto_page

with auto_page() as page:
    page.goto(url)
    html = page.content()
```

`auto_page()` (in `playwright_base.py`):
1. Checks if CDP is available on port 9222
2. If yes: connects via `playwright.chromium.connect_over_cdp(CDP_URL)`, reuses singleton browser
3. If no: falls back to headless Playwright launch

### Existing context for Google Jobs
Google Jobs uses `browser.contexts[0]` instead of creating a new context, so it inherits the existing Chrome session cookies. New contexts trigger Google CAPTCHA.

## Browser tools for debugging

### opencode-chrome-devtools plugin
Configured in `opencode.json` at project root. Provides direct CDP browser tools:

- `browser_list` — list open tabs
- `browser_navigate` — go to a URL
- `browser_eval` — run JS in the page
- `browser_snapshot` — accessibility tree with UIDs
- `browser_click` / `browser_fill` — interact with elements
- `browser_screenshot` — capture page

### Playwright Eval for React pages
Fuzu uses React. Standard `page.fill()` doesn't trigger React state. Instead, use `page.evaluate()` to:
1. Set input value via native setter: `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, term)`
2. Dispatch `input` + `change` events
3. Call React `onClick` directly from `__reactProps` on the button element

## Key files

| File | Role |
|------|------|
| `scrapers/_playwright_common.py` | `CDP_URL`, `ensure_cdp()`, `_kill_port()`, `cdp_available()`, `check_captcha()` |
| `scrapers/playwright_base.py` | `auto_page()`, `cdp_page()`, `new_page()` context managers, browser singleton |
| `scrapers/async_playwright.py` | Async version of CDP connection |
| `start_cdp.sh` | Shell script to manually start Chrome with CDP |
| `opencode.json` | Config for opencode-chrome-devtools plugin |
