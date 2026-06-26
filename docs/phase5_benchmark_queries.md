# Phase 5 — Benchmark Query Specification

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Date:** 2026-06-24  
**Status:** Canonical query templates for Phase 5 benchmarking

Schemas: [`phase2_relational_schema.md`](phase2_relational_schema.md), [`phase2_graph_schema.md`](phase2_graph_schema.md)  
**Prerequisite:** Phase 3 complete — databases loaded per [`README.md`](../README.md) and validated in [`phase3_database_population.md`](phase3_database_population.md)

---

## Benchmark platform

| Platform | Fair RDBMS vs graph timings? | Notes |
|----------|------------------------------|-------|
| **Windows 10/11 + Ryzen (amd64)** | **Yes — use this** | Both Docker images native `linux/amd64` |
| macOS Apple Silicon | **No** | PostGIS emulated amd64; Neo4j native arm64 |
| macOS Intel / Linux amd64 | Yes | Both native amd64 |

Run Phase 5 on a host where `docker exec dm-south-sudan-postgis uname -m` and `docker exec dm-south-sudan-neo4j uname -m` both return `x86_64`.

Document in the thesis: CPU model, OS, Docker version, image tags, and container architectures.

Do **not** publish comparative timings from macOS Apple Silicon unless both databases run on equal footing.

---

## Overview

Five queries designed to compare PostgreSQL and Neo4j across graph-native workloads (Q1–Q3, Q5) and relational strengths (Q4). All queries use **directed** edges; do not treat the road network as undirected.

### Fixed benchmark parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Example camp | `SSD-DS-SS0101_0005` | Don Bosco, Central Equatoria |
| Q2 state | `SS01` | Central Equatoria (15 camps) |
| Q2 target hospital | `SSD-HF-000055` | Juba Teaching Hospital |
| Q3 hub | `HUB-001` / `SSD-HF-000055` | Juba Teaching Hospital |
| Q3 max distance | `50000` m | 50 km |
| Q5 camp | `SSD-DS-SS0101_0005` | Scenario camp |
| Q5 hospital | `SSD-HF-000055` | Scenario hospital |
| Q5 evacuees | `200` | Scenario override |
| Q5 hospital slots | `250` | Scenario override |

### Data quality caveats (document in thesis)

1. 666 POIs have snap distance > 5 km (`data/processed/network/poi_snap_review.csv`).
2. Q1/Q2 exclude `facility_type = 'unknown'` (651 facilities in graph).
3. Q4 road km is **national** only (no state polygons on road edges).
4. Q5 capacities are synthetic; roads are unlimited.

---

## Dual-track PostgreSQL routing (Q1–Q3)

Phase 4 implements **two** PostgreSQL routing stacks plus Neo4j GDS:

| Track | Files | Role in thesis |
|-------|-------|----------------|
| **PG-CTE** | `q1_nearest_hospital.sql`, `q2_state_camps_to_hospital.sql`, `q3_hub_reachability.sql` | Secondary — pure SQL without extensions |
| **PG-pgRouting** | `q1_nearest_hospital_pgrouting.sql`, `q2_*_pgrouting.sql`, `q3_*_pgrouting.sql` | **Primary PostgreSQL** — fair vs Neo4j GDS |
| **Neo4j-GDS** | `q1_nearest_hospital.cypher`, `q2_*.cypher`, `q3_*.cypher` | **Primary graph** — distance-weighted Dijkstra |

**Phase 5 headline comparison:** median latency **PG-pgRouting vs Neo4j-GDS**.  
**Supporting analysis:** PG-CTE vs PG-pgRouting (cost of omitting pgRouting).

Docker image: `pgrouting/pgrouting:16-3.5-4.0` with `CREATE EXTENSION pgrouting` in [`schema.sql`](../src/db/postgresql/schema.sql).

Benchmark harness: `python scripts/benchmark_routing_queries.py --runs 5 --warmup 1`  
Output: `output/routing_benchmark_results.json`

---

## Query 1 — Nearest Hospital/PHCC from one camp

**Use case:** Cholera outbreak at a refugee camp — find shortest road path (meters) to the nearest Hospital or PHCC.

**Difficulty:** Medium–High (SQL recursive CTE) vs Low (Neo4j native).

### Logic

1. Start at camp `CONNECTOR` → road node.
2. Traverse directed `ROAD_SEGMENT` / `road_edges`.
3. End at a road node that is an access point for a `Hospital` or `PHCC`.
4. `total_m = camp_connector + road_path + hospital_connector`.

### Neo4j (Cypher)

```cypher
// Parameters: $camp_id e.g. 'SSD-DS-SS0101_0005'
MATCH (c:DisplacementSite {poi_node_id: $camp_id})-[cOut:CONNECTOR]->(start:RoadNode)
MATCH (hf:HealthFacility)
WHERE hf.facility_type IN ['Hospital', 'PHCC']
MATCH (hf)-[hOut:CONNECTOR]->(end:RoadNode)
MATCH p = shortestPath((start)-[:ROAD_SEGMENT*]->(end))
WITH c, hf, cOut, hOut, p,
     cOut.length_m + reduce(d = 0, r IN relationships(p) | d + r.length_m) + hOut.length_m AS total_m
RETURN c.poi_node_id AS camp_id,
       c.name AS camp_name,
       hf.facility_id AS facility_id,
       hf.name AS facility_name,
       hf.facility_type AS facility_type,
       total_m,
       length(p) AS road_hops
ORDER BY total_m
LIMIT 1;
```

### PostgreSQL (recursive CTE sketch)

```sql
-- Parameters: :camp_id
WITH RECURSIVE
camp AS (
    SELECT ds.site_id, ds.site_name, pc.road_node_id AS start_road_node_id, pc.length_m AS camp_connector_m
    FROM displacement_sites ds
    JOIN poi_connectors pc ON pc.poi_node_id = ds.site_id
    WHERE ds.site_id = :camp_id
),
targets AS (
    SELECT fra.road_node_id, fra.facility_id, fra.connector_length_m AS hospital_connector_m
    FROM facility_road_access fra
    JOIN health_facilities hf ON hf.facility_id = fra.facility_id
    WHERE hf.facility_type IN ('Hospital', 'PHCC')
),
search AS (
    SELECT c.start_road_node_id AS node_id,
           c.camp_connector_m AS cost_m,
           ARRAY[c.start_road_node_id] AS visited,
           0 AS hops
    FROM camp c
    UNION ALL
    SELECT re.end_node_id::bigint,
           s.cost_m + re.length_m,
           s.visited || re.end_node_id::bigint,
           s.hops + 1
    FROM search s
    JOIN road_edges re ON re.start_node_id = s.node_id
    WHERE s.hops < 50
      AND NOT re.end_node_id = ANY(s.visited)
),
best AS (
    SELECT t.facility_id, s.cost_m + t.hospital_connector_m AS total_m, s.hops
    FROM search s
    JOIN targets t ON t.road_node_id = s.node_id
    ORDER BY total_m
    LIMIT 1
)
SELECT * FROM best;
```

**Note:** Production PostgreSQL uses **pgRouting** (`pgr_dijkstraCost`) in Phase 4 artifacts (`*_pgrouting.sql`). The recursive CTE below remains as the **PG-CTE secondary baseline** to demonstrate SQL graph limitations without extensions.

---

## Query 2 — All Central Equatoria camps → Juba referral hospital

**Use case:** Referral hospital in Juba has capacity — find shortest path from every camp in Central Equatoria.

**Difficulty:** Extreme (SQL) vs Low (Neo4j `UNWIND`).

### Neo4j (Cypher)

```cypher
// Parameters: $state_code 'SS01', $target_facility_id 'SSD-HF-000055'
MATCH (target:HealthFacility {facility_id: $target_facility_id})-[tOut:CONNECTOR]->(end:RoadNode)
MATCH (c:DisplacementSite {state_code: $state_code})-[cOut:CONNECTOR]->(start:RoadNode)
MATCH p = shortestPath((start)-[:ROAD_SEGMENT*]->(end))
WITH c, target, cOut, tOut, p,
     cOut.length_m + reduce(d = 0, r IN relationships(p) | d + r.length_m) + tOut.length_m AS total_m
RETURN c.poi_node_id AS camp_id,
       c.name AS camp_name,
       target.facility_id AS hospital_id,
       total_m,
       length(p) AS road_hops
ORDER BY total_m;
```

### PostgreSQL

Run Query 1 once per camp in `SELECT site_id FROM displacement_sites WHERE state_code = 'SS01'` (15 iterations), or extend the recursive CTE with a multi-source seed — expected to perform poorly; document runtime comparison.

---

## Query 3 — Camps reachable within 50 km of a hub

**Use case:** Flooding near Juba — which camps can a logistical hub reach within 50 km of road distance?

**Hub:** Curated hospital from `logistical_hubs` (no airport data in project).

### Neo4j (Cypher) — reachable camps

```cypher
// Parameters: $hub_id 'HUB-001', $max_distance_m 50000
MATCH (hub:LogisticalHub {hub_id: $hub_id})
MATCH (hf:HealthFacility {facility_id: hub.facility_id})-[hOut:CONNECTOR]->(hubStart:RoadNode)
MATCH (c:DisplacementSite)-[cOut:CONNECTOR]->(campStart:RoadNode)
MATCH p = shortestPath((hubStart)-[:ROAD_SEGMENT*]->(campStart))
WITH c, hf, hOut, cOut, p,
     hOut.length_m + reduce(d = 0, r IN relationships(p) | d + r.length_m) + cOut.length_m AS total_m
WHERE total_m <= $max_distance_m
RETURN c.poi_node_id AS camp_id, c.name AS camp_name, c.state_code, total_m
ORDER BY total_m;
```

### Neo4j — isolated camps (complement)

```cypher
// Camps NOT reachable within threshold
MATCH (c:DisplacementSite)
WHERE NOT EXISTS {
    MATCH (hub:LogisticalHub {hub_id: $hub_id})
    MATCH (hf:HealthFacility {facility_id: hub.facility_id})-[hOut:CONNECTOR]->(hubStart:RoadNode)
    MATCH (c)-[cOut:CONNECTOR]->(campStart:RoadNode)
    MATCH p = shortestPath((hubStart)-[:ROAD_SEGMENT*]->(campStart))
    WITH hOut, cOut, p,
         hOut.length_m + reduce(d = 0, r IN relationships(p) | d + r.length_m) + cOut.length_m AS total_m
    WHERE total_m <= $max_distance_m
}
RETURN c.poi_node_id, c.name, c.state_code;
```

### PostgreSQL

Recursive CTE from hub road node with `cost_m <= 50000` stop condition; join to all camps; anti-join for isolated list.

---

## Query 4 — State humanitarian stats + national road length

**Use case:** Per-state camp counts, IDP totals, hospital/PHCC counts; national primary+secondary road km.

**Difficulty:** Low (SQL) vs Medium (Cypher aggregations).

### PostgreSQL

```sql
-- Per-state humanitarian stats
SELECT * FROM v_state_humanitarian_stats
ORDER BY state_code;

-- National primary + secondary road length (km)
SELECT ROUND(SUM(length_m) / 1000.0, 2) AS primary_secondary_km
FROM road_edges
WHERE split_part(highway, '|', 1) IN ('primary', 'secondary');
```

### Neo4j (Cypher)

```cypher
// Per-state displacement stats
MATCH (c:DisplacementSite)
RETURN c.state_code AS state_code,
       count(c) AS displacement_site_count,
       sum(c.idp_individuals) AS idp_individuals_total
ORDER BY state_code;

// Per-state hospital/PHCC count (georeferenced)
MATCH (h:HealthFacility)
WHERE h.facility_type IN ['Hospital', 'PHCC']
  AND h.nearest_road_node_id IS NOT NULL
RETURN h.state_code AS state_code,
       count(h) AS hospital_phcc_count
ORDER BY state_code;

// National road length
MATCH ()-[r:ROAD_SEGMENT]->()
WHERE r.highway IN ['primary', 'secondary']
RETURN sum(r.length_m) / 1000.0 AS primary_secondary_km;
```

**Thesis point:** Q4 demonstrates RDBMS strength for dimensional reporting; graph DB can answer it but SQL is more natural.

---

## Query 5 — Evacuation max flow (camp → hospital)

**Use case:** Camp must evacuate 200 people to a hospital with 250 free beds — what is the maximum flow through the network?

### Capacity model

| Edge | Capacity |
|------|----------|
| `ROAD_SEGMENT` | Unlimited (`999999999`) |
| Camp `CONNECTOR` (camp → road) | `min($evacuees, camp.idp_individuals)` |
| `CONNECTOR_REVERSE` (road → hospital) | `min($hospital_slots, hospital.admission_capacity)` |

Expected result when path exists: `min(200, 250, connectivity) = 200`.

### Neo4j (Graph Data Science)

```cypher
// Build projected graph with capacity property, then:
// CALL gds.maxFlow.stream('evacGraph', {sourceNode: campRoadNodeId, targetNode: hospitalRoadNodeId})
// Requires GDS plugin and graph projection from routing_edges with scenario capacities applied.
```

Phase 5 implementation steps:
1. Resolve camp and hospital road node IDs from `CONNECTOR` edges.
2. Project directed graph with scenario-overridden capacities on connector edges.
3. `gds.maxFlow` from camp road node to hospital road node.

### PostgreSQL

Max-flow is **not** native SQL. Implement via application layer (e.g. NetworkX `maximum_flow`) on `routing_edges` exported graph with the same capacity overrides. Document honestly in the thesis: algorithm portability vs graph-native operations.

```python
# Pseudocode — Phase 5 benchmark harness
# G = build_digraph from routing_edges
# G[camp_road][camp_poi]['capacity'] = min(200, idp_count)
# G[hospital_road][hospital_poi]['capacity'] = min(250, admission_capacity)
# flow = nx.maximum_flow(G, camp_road, hospital_road)
```

---

## Benchmark execution checklist (Phase 5)

| Step | Action |
|------|--------|
| 0 | Complete Phase 3 — [`README.md`](../README.md) Steps 3–5 on **Windows amd64** for fair timings |
| 1 | Confirm both containers native `x86_64`: `docker exec ... uname -m` |
| 2 | Load PostgreSQL schema + data (`scripts/load_postgresql.py` or already loaded) |
| 3 | Load Neo4j nodes/relationships + `constraints.cypher` |
| 4 | Warm up both databases |
| 5 | Run each query N times; record median latency |
| 6 | Record implementation complexity (lines of code, readability) |
| 7 | Include data quality caveats and platform metadata in results section |

---

## Related documents

- [`phase2_relational_schema.md`](phase2_relational_schema.md)
- [`phase2_graph_schema.md`](phase2_graph_schema.md)
- [`phase2_data_modeling.md`](phase2_data_modeling.md)
- [`phase4_pgrouting_adoption_and_routing_queries.md`](phase4_pgrouting_adoption_and_routing_queries.md)
- [`phase4_query_implementation.md`](phase4_query_implementation.md)
- [`README.md`](../README.md)
- [`phase3_database_population.md`](phase3_database_population.md)
- [`road_network_topology.md`](road_network_topology.md)
- [`AGENT_PHASE3.md`](../AGENT_PHASE3.md)
