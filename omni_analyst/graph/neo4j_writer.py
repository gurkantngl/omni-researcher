from typing import Iterable, Tuple
from neo4j import GraphDatabase

from omni_analyst.configs.settings import settings


def write_relationships(
    relationships: Iterable[Tuple[str, str, str]],
) -> None:
    if not settings.neo4j_password:
        return
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    query = """
    MERGE (a:Entity {name: $src})
    MERGE (b:Entity {name: $dst})
    MERGE (a)-[r:REL {type: $rel}]->(b)
    """
    with driver.session() as session:
        for src, rel, dst in relationships:
            session.run(query, src=src, rel=rel, dst=dst)
    driver.close()
