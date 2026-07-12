#!/bin/sh
# Launch Chrome with CDP on port 9222 for Playwright connect_over_cdp.
# Uses the first available Chrome/Chromium binary.
set -e

for bin in google-chrome google-chrome-stable chromium chromium-browser \
           /usr/bin/google-chrome /usr/bin/google-chrome-stable /snap/bin/chromium; do
    if command -v "$bin" >/dev/null 2>&1 || [ -x "$bin" ]; then
        echo "Starting $bin with CDP on port 9222..." >&2
        exec "$bin" --remote-debugging-port=9222 --headless \
            --no-sandbox --disable-dev-shm-usage \
            --disable-gpu --disable-software-rasterizer \
            "$@"
    fi
done

echo "ERROR: No Chrome/Chromium binary found. Install Chrome or chromium-browser." >&2
exit 1
