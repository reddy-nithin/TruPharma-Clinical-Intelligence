"""
Opioid Track Ingestion — Shared utilities for API access.
"""

import time
import requests


def retry_get(url, max_retries=3, initial_delay=1.0, timeout=30,
              delay_between=0.0, headers=None):
    """HTTP GET with exponential backoff retry.

    Args:
        url: The URL to fetch.
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay in seconds before first retry.
        timeout: Request timeout in seconds.
        delay_between: Rate-limit delay before each request.
        headers: Optional request headers.

    Returns:
        requests.Response on success.

    Raises:
        requests.RequestException after all retries exhausted.
    """
    if headers is None:
        headers = {"User-Agent": "TruPharma-Opioid/1.0"}

    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            if delay_between > 0:
                time.sleep(delay_between)
            resp = requests.get(url, timeout=timeout, headers=headers)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            # Don't retry on 404 (definitive "not found")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    raise
            if attempt < max_retries:
                wait = initial_delay * (2 ** attempt)
                print(f"  [retry {attempt + 1}/{max_retries}] {e} — waiting {wait:.1f}s")
                time.sleep(wait)

    raise last_exc
