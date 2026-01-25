from typing import List
import re
from langchain_google_genai import ChatGoogleGenerativeAI

from omni_analyst.configs.settings import settings
from omni_analyst.types import ResearchState


def _fallback_plan(question: str) -> List[str]:
    return [
        "Soru kapsamindaki ana varliklari belirle.",
        "Guncel kaynaklari topla ve ozetle.",
        "Kritik metrikleri ve riskleri ayristir.",
        "Grafik/tablo gerektiren bolumleri tespit et.",
        "Raporu kaynakli sekilde derle.",
    ]


def plan_tasks(state: ResearchState) -> ResearchState:
    if not settings.gemini_api_key:
        state["plan"] = _fallback_plan(state["question"])
        return state

    llm = ChatGoogleGenerativeAI(
        google_api_key=settings.gemini_api_key,
        model=settings.model_text,
    )
    prompt = (
        "Asagidaki soruyu arastirmak icin 4-6 maddelik bir gorev listesi uret:\n"
        f"Soru: {state['question']}"
    )
    try:
        response = llm.invoke(prompt)
    except Exception:
        state["plan"] = _fallback_plan(state["question"])
        return state
    raw_lines = [line.strip() for line in response.content.splitlines()]
    lines = []
    for line in raw_lines:
        if not line:
            continue
        normalized = line.casefold()
        if any(token in normalized for token in ("elbet", "işte", "gorev listesi", "görev listesi")):
            continue
        cleaned = re.sub(r"^[\-\*\s]*\d+[\.\)]\s*", "", line)
        cleaned = cleaned.replace("**", "").replace("*", "").strip()
        cleaned = cleaned.rstrip(":").strip()
        if re.match(r"^[\-\*\s]*\d+[\.\)]\s*", line):
            if cleaned:
                lines.append(cleaned)
    if not lines:
        for line in raw_lines:
            cleaned = line.strip("-* ").replace("**", "").replace("*", "").strip()
            cleaned = cleaned.rstrip(":").strip()
            if cleaned and len(cleaned) <= 120:
                lines.append(cleaned)
    state["plan"] = lines[:6] if lines else _fallback_plan(state["question"])
    return state
