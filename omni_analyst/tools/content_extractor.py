from typing import List, Tuple
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from omni_analyst.configs.settings import settings


def _fetch_with_requests(url: str, timeout: int = 20) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _fetch_with_selenium(url: str) -> str:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
    except Exception as exc:  # pragma: no cover - optional
        raise RuntimeError("Selenium yuklu degil.") from exc

    options = Options()
    if settings.selenium_headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(url)
        return driver.page_source
    finally:
        driver.quit()


def fetch_html(url: str) -> str:
    if settings.use_selenium:
        return _fetch_with_selenium(url)
    return _fetch_with_requests(url)


def extract_assets(html: str, base_url: str) -> Tuple[List[str], List[str]]:
    soup = BeautifulSoup(html, "lxml")
    image_urls = []
    pdf_urls = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            lower_src = src.lower()
            if any(
                token in lower_src
                for token in (
                    "icon",
                    "logo",
                    "badge",
                    "sprite",
                    "favicon",
                    ".svg",
                )
            ):
                continue
            image_urls.append(urljoin(base_url, src))
    for link in soup.find_all("a"):
        href = link.get("href")
        if not href:
            continue
        full_url = urljoin(base_url, href)
        if ".pdf" in full_url.lower():
            pdf_urls.append(full_url)
    return image_urls, pdf_urls
