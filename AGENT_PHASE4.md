# Phase 4 Agent — Query Design & Implementation

**Status:** IN PROGRESS (2026-06-26) — Q1–Q3 routing complete; Q4–Q5 pending.  
**Phase 4 report:** [`docs/phase4_pgrouting_adoption_and_routing_queries.md`](docs/phase4_pgrouting_adoption_and_routing_queries.md)  
**Technical log:** [`docs/phase4_query_implementation.md`](docs/phase4_query_implementation.md)  
**Query specification:** [`docs/phase5_benchmark_queries.md`](docs/phase5_benchmark_queries.md)

You are the **Phase 4 Query Implementation Agent** for the DM South Sudan project.

Your job is to **implement all five benchmark queries in both PostgreSQL and Neo4j**, verify they return correct results against the loaded databases, and document implementation decisions. Informal routing benchmarks may be run via `scripts/benchmark_routing_queries.py`; formal Phase 5 timing study follows Phase 4 completion.

The **Orchestrator Agent** (`AGENT.md`) maintains the global project view.

---

## Prerequisites (complete — do not redo unless broken)

| Phase | Status | Key artifacts |
|-------|--------|---------------|
| Phase 1 | Complete | `docs/phase1_data_understanding.md` |
| Phase 2 | Complete | Schemas, processed data, `docs/phase5_benchmark_queries.md` |
| Phase 3 | Complete | Live PostGIS + Neo4j, `docs/phase3_database_population.md` |
| **pgRouting stack** | Required | Docker image `pgrouting/pgrouting:16-3.5-4.0`; extension in `schema.sql` |

**Environment:** Docker containers healthy; `conda activate dm-south-sudan`; `.env` configured. Pipeline: [`README.md`](README.md) Steps 0–7.

**Do not:** redesign schemas, re-run Phase 2 ETL, or re-populate databases unless imports are broken.

---

## Dual-track PostgreSQL (Q1–Q3)

| Track | Role | Files |
|-------|------|-------|
| **PG-pgRouting** | Primary PostgreSQL — fair vs Neo4j GDS | `*_pgrouting.sql` |
| **PG-CTE** | Secondary — pure SQL without extensions | `q1/q2/q3_*.sql` (no `_pgrouting` suffix) |
| **Neo4j-GDS** | Primary graph — Dijkstra on `length_m` | `*.cypher` in `src/queries/neo4j/` |

pgRouting is enabled at **Step 5 populate** (`CREATE EXTENSION pgrouting` in `schema.sql`), not installed manually after Phase 3.

---

## Work one task at a time (required)

Recommended order: **Q1 → Q4 → Q2 → Q3 → Q5** (Q2–Q3 may already be done).

Each session: implement one query (or one sub-step), validate, append to `docs/phase4_query_implementation.md`, stop.

---

## Query modules (`src/queries/`)

```
src/queries/
  _benchmark_params.yaml
  postgresql/
    q1_nearest_hospital.sql              # PG-CTE (secondary)
    q1_nearest_hospital_pgrouting.sql    # PG-pgRouting (primary) ✅
    q2_state_camps_to_hospital.sql       # PG-CTE ✅
    q2_state_camps_to_hospital_pgrouting.sql  ✅
    q3_hub_reachability.sql              # PG-CTE ✅
    q3_hub_reachability_pgrouting.sql    ✅
    q4_state_stats.sql                   # pending
    q5_max_flow.py                       # pending (NetworkX)
  neo4j/
    q1_nearest_hospital.cypher           ✅ GDS Dijkstra
    q2_state_camps_to_hospital.cypher    ✅
    q3_hub_reachability.cypher           ✅
    q4_state_stats.cypher                # pending
    q5_max_flow.cypher                   # pending (GDS maxFlow)
```

Optional: `scripts/run_query.py`, `scripts/benchmark_routing_queries.py` (exists).

---

## Query summary

| Query | PostgreSQL primary | PostgreSQL secondary | Neo4j |
|-------|-------------------|---------------------|-------|
| **Q1** | `pgr_dijkstraCost` → 419 targets | Hop-bounded recursive CTE | GDS `allShortestPaths.dijkstra` |
| **Q2** | `pgr_dijkstraCost` per camp | 15× recursive CTE (impractical) | GDS `shortestPath.dijkstra` per camp |
| **Q3** | `pgr_dijkstraCost` hub → camps | Recursive CTE + hop cap (impractical) | GDS `allShortestPaths.dijkstra` |
| **Q4** | `v_state_humanitarian_stats` + road km | — | Multiple aggregations |
| **Q5** | NetworkX on `routing_edges` | — | GDS `maxFlow` |

---

## Success criteria

- [x] pgRouting in Docker + schema
- [x] Q1–Q3 dual-track + Neo4j GDS validated
- [x] Pilot routing benchmark documented
- [ ] Q4 PostgreSQL + Neo4j
- [ ] Q5 PostgreSQL + Neo4j
- [ ] Q5 flow = 200 on smoke scenario
- [ ] `AGENT.md` updated — Phase 4 complete, Phase 5 next

---

## Quick reference

```
docs/phase4_pgrouting_adoption_and_routing_queries.md  # Phase 4 narrative report
docs/phase4_query_implementation.md                    # Discovery / validation log
docs/phase5_benchmark_queries.md                       # Spec + dual-track matrix
docs/database_usage_guide.md                           # Run queries (§11)
scripts/benchmark_routing_queries.py                   # Pilot benchmarks
src/queries/_benchmark_params.yaml                     # Scenario IDs
AGENT.md                                               # Orchestrator
```

**Run databases:** `docker compose up -d` (see [`README.md`](README.md)).
