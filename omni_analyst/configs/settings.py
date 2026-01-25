import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    model_text: str = os.getenv("MODEL_TEXT", "gemini-2.0-flash")
    model_vision: str = os.getenv("MODEL_VISION", "gemini-2.0-flash")
    use_selenium: bool = os.getenv("USE_SELENIUM", "0") == "1"
    selenium_headless: bool = os.getenv("SELENIUM_HEADLESS", "1") == "1"
    allow_domains: str = os.getenv("ALLOW_DOMAINS", "")
    enable_pdf_images: bool = os.getenv("ENABLE_PDF_IMAGES", "1") == "1"
    pdf_max_pages: int = int(os.getenv("PDF_MAX_PAGES", "2"))
    pdf_max_images: int = int(os.getenv("PDF_MAX_IMAGES", "4"))
    pdf_min_image_bytes: int = int(os.getenv("PDF_MIN_IMAGE_BYTES", "20000"))
    poppler_path: str = os.getenv("POPPLER_PATH", "")

    @property
    def allowlist(self) -> list[str]:
        return [d.strip().lower() for d in self.allow_domains.split(",") if d.strip()]


settings = Settings()
