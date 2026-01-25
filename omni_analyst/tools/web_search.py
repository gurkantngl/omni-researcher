from typing import List, Dict, Any
from urllib.parse import urlparse
from tavily import TavilyClient

from omni_analyst.configs.settings import settings


def _is_allowed(url: str, allowlist: List[str]) -> bool:
    if not allowlist:
        return True
    domain = urlparse(url).netloc.lower()
    return any(domain.endswith(allowed) for allowed in allowlist)


def _sort_pdf_first(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def _score(item: Dict[str, Any]) -> int:
        url = (item.get("url") or "").lower()
        title = (item.get("title") or "").lower()
        return 0 if ".pdf" in url or "pdf" in title else 1

    return sorted(results, key=_score)


def web_search(
    query: str,
    max_results: int = 5,
    allowlist: List[str] | None = None,
) -> List[Dict[str, Any]]:
    if not settings.tavily_api_key:
        return [
            {
                "title": "Placeholder Source",
                "url": "https://example.com",
                "content": "Tavily anahtari bulunamadi. Placeholder icerik.",
            }
        ]
    client = TavilyClient(api_key=settings.tavily_api_key)
    results = client.search(query=query, max_results=max_results)
    items = results.get("results", [])
    allowlist = allowlist or settings.allowlist
    items = [item for item in items if _is_allowed(item.get("url", ""), allowlist)]
    return _sort_pdf_first(items)
