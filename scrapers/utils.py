import os
import re
import logging
import validators
from urllib.parse import urlparse
from datetime import datetime

lgr = logging.getLogger()


def validate_and_parse_url(url):
    url = str(url)
    if validators.url(url):
        parsed_url = urlparse(url)
        return {
            'scheme': parsed_url.scheme,
            'base': parsed_url.netloc,
            'path': parsed_url.path,
            'params': parsed_url.params,
            'query': parsed_url.query,
        }
    return None


def get_job_id(url, source):
    parsed_url = validate_and_parse_url(url)
    if parsed_url is None:
        lgr.info(f'Failed to parse url {url}')
        return None
    source_lower = source.lower()
    if source_lower == "glassdoor":
        job_url = parsed_url.get("query")
        if job_url:
            try:
                parsed_params = dict(x.split("=") for x in job_url.split('&'))
                return parsed_params.get("jobListingId", None)
            except (IndexError, ValueError):
                pass
    elif source_lower == "brightermonday":
        try:
            return parsed_url.get("path").split("-")[-1]
        except IndexError:
            pass
    elif source_lower == "myjobmag":
        try:
            return parsed_url.get("path").split("/")[-1]
        except IndexError:
            pass
    elif source_lower == "fuzu":
        try:
            return parsed_url.get("path").split("/")[-1]
        except IndexError:
            pass
    elif source_lower == "corporatestaffing":
        try:
            path = parsed_url.get("path", "")
            m = re.search(r'/job/([^/]+)', path)
            return m.group(1) if m else path.split("/")[-1]
        except IndexError:
            pass
    elif source_lower == "jobwebkenya":
        try:
            path = parsed_url.get("path", "")
            m = re.search(r'/(\d+)/', path)
            return m.group(1) if m else path.split("/")[-1]
        except IndexError:
            pass
    return None


def parse_date(date_str, source=""):
    if not date_str:
        return ""
    date_str = date_str.strip()
    try:
        if source == "myjobmag":
            date_str = re.sub(r'\s+\d{4}$', '', date_str)
            parsed = datetime.strptime(date_str, "%d %B %Y")
            return parsed.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        pass
    try:
        from dateutil import parser as dateparser
        parsed = dateparser.parse(date_str, fuzzy=True)
        return parsed.strftime("%Y-%m-%d")
    except (ValueError, ImportError):
        pass
    return date_str


def parse_pickle_name(pickle_date=None):
    if pickle_date:
        pickle_name = datetime.strptime(pickle_date, "%m-%d-%Y").date().strftime("%m-%d-%Y")
    else:
        today = datetime.now().date()
        pickle_name = today.strftime("%m-%d-%Y")
    return f"{pickle_name}.pkl"
