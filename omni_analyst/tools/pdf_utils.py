from typing import List, Optional
import io
import requests
import pdfplumber
import os
import shutil

from omni_analyst.configs.settings import settings

def download_pdf(url: str, timeout: int = 30) -> Optional[bytes]:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        return None


def extract_tables_from_pdf_bytes(pdf_bytes: bytes, max_pages: int = 2) -> List[str]:
    outputs = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages[:max_pages]:
            tables = page.extract_tables() or []
            for table in tables:
                rows = ["\t".join(cell or "" for cell in row) for row in table]
                outputs.append("\n".join(rows))
            text = page.extract_text() or ""
            if text:
                outputs.append(text[:1500])
    return outputs


def _has_poppler() -> bool:
    if settings.poppler_path:
        pdftoppm = os.path.join(settings.poppler_path, "pdftoppm.exe")
        return os.path.exists(pdftoppm)
    return shutil.which("pdftoppm") is not None


def pdf_image_support_status() -> tuple[bool, str]:
    try:
        from pdf2image import convert_from_bytes  # noqa: F401
    except Exception:
        return False, "pdf2image bulunamadi."
    if not _has_poppler():
        return False, "Poppler bulunamadi. POPPLER_PATH ayarlayin."
    return True, ""


def extract_images_from_pdf_bytes(
    pdf_bytes: bytes, max_pages: int = 2
) -> List[bytes]:
    try:
        from pdf2image import convert_from_bytes
    except Exception:
        return []
    try:
        kwargs = {"first_page": 1, "last_page": max_pages}
        if settings.poppler_path:
            kwargs["poppler_path"] = settings.poppler_path
        images = convert_from_bytes(pdf_bytes, **kwargs)
    except Exception:
        return []
    outputs = []
    for image in images:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        outputs.append(buffer.getvalue())
    return outputs
