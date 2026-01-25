from omni_analyst.tools.vision import analyze_images, analyze_image_bytes
from omni_analyst.types import ResearchState


def run_vision(state: ResearchState) -> ResearchState:
    image_urls = state.get("image_urls", [])
    if image_urls:
        outputs, warnings = analyze_images(image_urls)
        state["extracted_tables"].extend(outputs)
        state["warnings"].extend(warnings)
    image_bytes = state.get("image_bytes", [])
    if image_bytes:
        outputs, warnings = analyze_image_bytes(image_bytes)
        state["extracted_tables"].extend(outputs)
        state["warnings"].extend(warnings)
    return state
