#!/bin/bash
cd /home/spidey/projects/jobscraper
source .venv/bin/activate

python -c "from scrapers._playwright_common import ensure_cdp; ensure_cdp()"

python run.py --days 7 >> ./data/cron.log 2>&1

pgrep -f "api.py.*9090" > /dev/null || \
  nohup python api.py --port 9090 >> ./data/api.log 2>&1 &