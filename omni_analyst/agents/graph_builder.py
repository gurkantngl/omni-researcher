from omni_analyst.graph.neo4j_writer import write_relationships
from omni_analyst.types import ResearchState


def build_graph(state: ResearchState) -> ResearchState:
    relationships = []
    if "NVIDIA" in state["question"].upper():
        relationships.append(("NVIDIA", "COMPETES_WITH", "AMD"))
        relationships.append(("NVIDIA", "COMPETES_WITH", "INTEL"))
    if relationships:
        write_relationships(relationships)
        state["graph_updates"] = [
            f"{src}-[{rel}]->{dst}" for src, rel, dst in relationships
        ]
    return state
