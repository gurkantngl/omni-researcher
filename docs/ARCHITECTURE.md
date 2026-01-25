# Omni-Analyst Mimarisi

## State Machine Akisi
- `plan` -> `research` -> `vision` -> `graph` -> `draft` -> `critique`
- `critique` ciktisi eksik veri bulursa `research` adimina geri doner.
- Iterasyon siniri `max_iterations` ile kontrol edilir.

## Agent Rolleri
- Planner: Soruyu alt gorevlere boler.
- Research: Web kaynaklarini toplar.
- Vision: Grafik/tablo goruntulerini metne cevirir.
- Graph Builder: Neo4j'e entity ve iliski yazar.
- Critic: Eksik veri/hallusinasyon risklerini tespit eder.
- Reporter: Kaynakli raporu olusturur.

## GraphRAG Notu
Neo4j uzerinde:
- Node: `Entity`
- Relationship: `REL` (ozel iliski tipi `type` alaniyla tutulur)
