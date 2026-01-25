from typing import Optional
import requests


def fetch_url(url: str, timeout: int = 20) -> Optional[str]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None
