from typing import List, Optional, Tuple
import requests
import google.generativeai as genai

from omni_analyst.configs.settings import settings


def _download_image(url: str, timeout: int = 20) -> Optional[Tuple[bytes, str]]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) < 10_000:
            return None
        content_type = response.headers.get("Content-Type", "image/jpeg")
        return response.content, content_type
    except requests.RequestException:
        return None


def analyze_images(image_urls: List[str]) -> Tuple[List[str], List[str]]:
    if not settings.gemini_api_key or not image_urls:
        return [], []
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.model_vision)
    outputs = []
    warnings = []
    for url in image_urls:
        download = _download_image(url)
        if not download:
            continue
        image_bytes, content_type = download
        try:
            response = model.generate_content(
                [
                    "Bu grafikte ne anlatiliyor?",
                    {"mime_type": content_type, "data": image_bytes},
                ]
            )
            outputs.append(response.text)
        except Exception:
            warnings.append(f"VLM gorsel analizi basarisiz: {url}")
            continue
    return outputs, warnings


def analyze_image_bytes(
    images: List[bytes], content_type: str = "image/png"
) -> Tuple[List[str], List[str]]:
    if not settings.gemini_api_key or not images:
        return [], []
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.model_vision)
    outputs = []
    warnings = []
    for image_bytes in images:
        if len(image_bytes) < settings.pdf_min_image_bytes:
            continue
        try:
            response = model.generate_content(
                [
                    "Bu grafikte ne anlatiliyor?",
                    {"mime_type": content_type, "data": image_bytes},
                ]
            )
            outputs.append(response.text)
        except Exception:
            warnings.append("VLM PDF gorsel analizi basarisiz.")
            continue
    return outputs, warnings
