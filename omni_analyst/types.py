from typing import List, Dict, Any, TypedDict


class ResearchState(TypedDict):
    question: str
    plan: List[str]
    sources: List[Dict[str, Any]]
    documents: List[str]
    extracted_tables: List[str]
    image_urls: List[str]
    pdf_urls: List[str]
    image_bytes: List[bytes]
    warnings: List[str]
    graph_updates: List[str]
    draft_report: str
    critique: str
    final_report: str
    iteration: int
    max_iterations: int
    needs_more_data: bool


def initial_state(question: str, max_iterations: int = 2) -> ResearchState:
    return {
        "question": question,
        "plan": [],
        "sources": [],
        "documents": [],
        "extracted_tables": [],
        "image_urls": [],
        "pdf_urls": [],
        "image_bytes": [],
        "warnings": [],
        "graph_updates": [],
        "draft_report": "",
        "critique": "",
        "final_report": "",
        "iteration": 0,
        "max_iterations": max_iterations,
        "needs_more_data": False,
    }
