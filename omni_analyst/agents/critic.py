from omni_analyst.types import ResearchState


def critique_report(state: ResearchState) -> ResearchState:
    critique = []
    if not state["sources"]:
        critique.append("Kaynaklar eksik.")
    if "AMD" in state["question"].upper():
        has_amd = any("AMD" in (doc or "") for doc in state["documents"])
        if not has_amd:
            critique.append("AMD verileri bulunamadi.")
    state["critique"] = " ".join(critique) if critique else "Eksik veri yok."
    state["needs_more_data"] = bool(critique)
    state["iteration"] += 1
    return state
