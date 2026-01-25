from omni_analyst.tools.web_search import web_search
from omni_analyst.tools.content_extractor import fetch_html, extract_assets
from omni_analyst.tools.pdf_utils import (
    download_pdf,
    extract_tables_from_pdf_bytes,
    extract_images_from_pdf_bytes,
    pdf_image_support_status,
)
from omni_analyst.configs.settings import settings
from omni_analyst.types import ResearchState


def _company_from_url(url: str) -> str:
    lowered = url.lower()
    if "nvidia" in lowered:
        return "NVIDIA"
    if "amd.com" in lowered or "ir.amd.com" in lowered or "/amd/" in lowered or "advancedmicrodevices" in lowered:
        return "AMD"
    if "intel" in lowered or "intc.com" in lowered:
        return "INTEL"
    return "UNKNOWN"


def run_research(state: ResearchState) -> ResearchState:
    query = state["question"]
    allowlist_override = None
    extra_queries = []
    if "NVIDIA" in query.upper():
        query += " investor relations quarterly report pdf"
        base_allowlist = settings.allowlist or []
        allowlist_override = list(
            dict.fromkeys(
                base_allowlist
                + ["nvidia.com", "sec.gov", "amd.com", "intel.com", "intc.com"]
            )
        )
        extra_queries = [
            "AMD investor relations quarterly results pdf",
            "Intel investor relations quarterly results pdf",
            "INTC 10-Q pdf",
            "Intel Reports Fourth-Quarter and Full-Year 2025 Financial Results pdf",
            "Intel 10-K 2025 pdf",
        ]
    results = web_search(query, max_results=5, allowlist=allowlist_override)
    nvidia_results = []
    if "NVIDIA" in query.upper():
        nvidia_results = web_search(
            "NVIDIA Announces Financial Results PDF",
            max_results=3,
            allowlist=["nvidia.com"],
        )
    extra_results = []
    for extra_query in extra_queries:
        extra_results.extend(
            web_search(extra_query, max_results=3, allowlist=allowlist_override)
        )
    combined_results = results + nvidia_results + extra_results
    state["sources"] = combined_results
    documents = []
    for item in combined_results:
        content = item.get("content", "")
        url = item.get("url", "")
        if not content:
            continue
        company = _company_from_url(url)
        documents.append(f"[COMPANY:{company}] {content}")
    state["documents"] = documents
    image_urls = []
    pdf_urls = []
    for item in combined_results:
        url = item.get("url")
        if not url:
            continue
        title = (item.get("title") or "").lower()
        url_lower = url.lower()
        if ".pdf" in url_lower or "pdf" in url_lower or "pdf" in title:
            pdf_urls.append(url)
            continue
        try:
            html = fetch_html(url)
        except Exception:
            continue
        imgs, pdfs = extract_assets(html, url)
        image_urls.extend(imgs)
        pdf_urls.extend(pdfs)
    def _company_priority(url: str) -> int:
        lowered = url.lower()
        if "nvidia" in lowered:
            return 0
        if "amd" in lowered:
            return 1
        if "intel" in lowered or "intc" in lowered:
            return 2
        return 3

    def _keyword_priority(url: str) -> int:
        lowered = url.lower()
        if any(k in lowered for k in ("earnings", "financial", "results", "earnings_release")):
            return 0
        if "presentation" in lowered or "deck" in lowered:
            return 1
        return 2

    def _priority(url: str) -> tuple[int, int]:
        return (_company_priority(url), _keyword_priority(url))

    state["image_urls"] = sorted(list(dict.fromkeys(image_urls)), key=_priority)[:10]
    unique_pdfs = sorted(list(dict.fromkeys(pdf_urls)), key=_priority)

    selected_pdfs = []
    per_company_counts = {"NVIDIA": 0, "AMD": 0, "INTEL": 0, "UNKNOWN": 0}
    for url in unique_pdfs:
        company = _company_from_url(url)
        if company in per_company_counts and per_company_counts[company] < 2:
            selected_pdfs.append(url)
            per_company_counts[company] += 1
    for url in unique_pdfs:
        if url in selected_pdfs:
            continue
        if len(selected_pdfs) >= 6:
            break
        selected_pdfs.append(url)

    state["pdf_urls"] = selected_pdfs
    pdf_images_enabled = settings.enable_pdf_images
    if pdf_images_enabled:
        supported, reason = pdf_image_support_status()
        if not supported:
            pdf_images_enabled = False
            state["warnings"].append(reason)
    for pdf_url in state["pdf_urls"]:
        pdf_bytes = download_pdf(pdf_url)
        if not pdf_bytes:
            continue
        company = _company_from_url(pdf_url)
        max_pages = settings.pdf_max_pages
        if company == "AMD":
            max_pages = max(max_pages, 6)
        if company == "INTEL":
            max_pages = max(max_pages, 8)
        extracts = extract_tables_from_pdf_bytes(pdf_bytes, max_pages=max_pages)
        state["extracted_tables"].extend(extracts)
        if extracts:
            tagged = "\n".join(f"[COMPANY:{company}] {line}" for line in extracts)
            state["documents"].append(f"[COMPANY:{company}] PDF Extract ({pdf_url})\n{tagged}")
        if pdf_images_enabled and company != "INTEL":
            images = extract_images_from_pdf_bytes(
                pdf_bytes, max_pages=settings.pdf_max_pages
            )
            if images:
                state["image_bytes"].extend(images[: settings.pdf_max_images])
        if not extracts and pdf_images_enabled and not state["image_bytes"]:
            state["warnings"].append(
                f"PDF icerigi cozulmedi: {pdf_url}"
            )
    return state
