import sys

from langgraph.graph import StateGraph, END

from omni_analyst.types import ResearchState, initial_state
from omni_analyst.agents.planner import plan_tasks
from omni_analyst.agents.researcher import run_research
from omni_analyst.agents.vision_analyst import run_vision
from omni_analyst.agents.graph_builder import build_graph
from omni_analyst.agents.reporter import draft_report, finalize_report
from omni_analyst.agents.critic import critique_report


def route_after_critique(state: ResearchState) -> str:
    if state["needs_more_data"] and state["iteration"] < state["max_iterations"]:
        return "research"
    return "final"


def build_state_machine():
    graph = StateGraph(ResearchState)
    graph.add_node("plan", plan_tasks)
    graph.add_node("research", run_research)
    graph.add_node("vision", run_vision)
    graph.add_node("graph", build_graph)
    graph.add_node("draft", draft_report)
    graph.add_node("critique", critique_report)
    graph.add_node("final", finalize_report)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "research")
    graph.add_edge("research", "vision")
    graph.add_edge("vision", "graph")
    graph.add_edge("graph", "draft")
    graph.add_edge("draft", "critique")
    graph.add_conditional_edges(
        "critique",
        route_after_critique,
        {"research": "research", "final": "final"},
    )
    graph.add_edge("final", END)
    return graph.compile()


def run(question: str) -> ResearchState:
    workflow = build_state_machine()
    return workflow.invoke(initial_state(question))


def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding) + "\n")


if __name__ == "__main__":
    sample_question = (
        "NVIDIA'nin son ceyrek raporunu analiz et, rakipleriyle karsilastir "
        "ve riskleri ozetle."
    )
    result = run(sample_question)
    safe_print(result["final_report"])
