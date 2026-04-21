import requests
from typing import Optional


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str, timeout: int = 15) -> Optional[str]:
    """
    Fetch HTML content from a URL.

    Args:
        url: The webpage URL.
        timeout: Request timeout in seconds.

    Returns:
        HTML text if successful, otherwise None.
    """
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            print(f"[WARNING] Skipping non-HTML content: {url}")
            return None

        return response.text

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return None
