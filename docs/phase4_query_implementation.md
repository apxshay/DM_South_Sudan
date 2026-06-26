# Phase 4 — Query Implementation Progress

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Started:** 2026-06-26

**Main Phase 4 report (read this first):** [`phase4_pgrouting_adoption_and_routing_queries.md`](phase4_pgrouting_adoption_and_routing_queries.md) — pgRouting adoption, dual-track queries, pilot benchmark analysis.

This file is the **technical discovery log** (probe queries, rejected approaches, per-query validation).

---

## Design principles

- Implement from **Phase 2 schemas** and **loaded data**; do not copy SQL/Cypher from `docs/phase5_benchmark_queries.md`.
- **Directed edges only** — preserve OSMnx direction and one-way links.
- **Path cost (Q1–Q3):** `total_m = camp_connector + Σ(road_segment.length_m) + facility_connector`.
- **Q1/Q2:** exclude `facility_type = 'unknown'` from routing targets.
- **Benchmark parameters:** `src/queries/_benchmark_params.yaml` (derived from Phase 3 smoke + reference CSVs).
- **One query per session**; append a dated section after each query passes validation.

---

## 2026-06-26 — Q1: Nearest Hospital/PHCC from one camp

### Discovery

**Smoke scenario:** camp `SSD-DS-SS0101_0005` (Don Bosco, Central Equatoria) → nearest routable Hospital or PHCC.

#### Environment probes

| Check | PostgreSQL | Neo4j |
|-------|------------|-------|
| Containers healthy | yes | yes |
| Road nodes | 24,779 | 24,779 |
| Road edges / ROAD_SEGMENT | 62,345 | 62,345 |
| Camp connector (Don Bosco → road) | road node `2985123616`, 714.8 m | same |
| Eligible Hospital/PHCC targets (excl. unknown) | 419 | 419 |
| GDS available | — | 2.13.10 |

#### PostgreSQL approach evaluation

| Option | Result | Decision |
|--------|--------|----------|
| pgRouting `pgr_dijkstra` | Extension not installed | Rejected |
| Unbounded recursive CTE on `road_edges` | No result in >3 min (path explosion) | Rejected |
| plpgsql Dijkstra with temp frontier table | `CREATE FUNCTION` OK; execution still running after ~70 s | Rejected (interpreted loop too slow at national scale) |
| Hop-bounded recursive CTE (`max_hops=30`) | **~36 s**; matches Neo4j on smoke camp | **Selected** |

**Caveat (documented):** the recursive CTE explores all **simple paths** up to `max_hops` and picks minimum `total_m`. It is not a full Dijkstra over the national graph; a shorter-distance path requiring more than `max_hops` would be missed. Hop limit 30 was chosen after timing probes (25 hops ≈ 12 s, 30 hops ≈ 36 s, both agree with GDS on smoke camp).

#### Neo4j approach evaluation

| Option | Result | Decision |
|--------|--------|----------|
| `shortestPath()` (hop-based) | Finds minimum-hop path; ranks by `length_m` afterward — **not guaranteed to minimize meters** | Rejected for production Q1 |
| **GDS `gds.allShortestPaths.dijkstra.stream`** with `relationshipWeightProperty: 'length_m'` | **5191.26 m** to Gumbo PHCC in ~52 s incl. projection; true distance minimization | **Selected** |

Discovery confirmed `shortestPath()` returns the same winner for Don Bosco (3 hops, 5191.26 m), but GDS Dijkstra is used per Phase 4 requirement to guarantee meter-based optimality across all 419 targets.

**GDS projection:** in-memory graph `q1_road_network` — native projection of `RoadNode` + directed `ROAD_SEGMENT` with `length_m` property (62,345 rels). Dropped and recreated idempotently on each run.

### Implementation

| Platform | File | Approach |
|----------|------|----------|
| PostgreSQL | `src/queries/postgresql/q1_nearest_hospital.sql` | Recursive CTE on `road_edges` + `poi_connectors` / `facility_road_access`; psql vars `camp_id`, `max_hops` |
| Neo4j | `src/queries/neo4j/q1_nearest_hospital.cypher` | GDS graph project + `allShortestPaths.dijkstra` from camp road node; parameter `$camp_id` |

### Validation (smoke camp `SSD-DS-SS0101_0005`)

| Field | PostgreSQL | Neo4j | Match |
|-------|------------|-------|-------|
| `facility_id` | SSD-HF-000126 | SSD-HF-000126 | yes |
| `facility_name` | Gumbo PHCC | Gumbo PHCC | yes |
| `facility_type` | PHCC | PHCC | yes |
| `camp_connector_m` | 714.8 | 714.8 | yes |
| `road_cost_m` | 3842.053269737041 | 3842.053269737041 | yes |
| `hospital_connector_m` | 634.41 | 634.41 | yes |
| `total_m` | 5191.263269737041 | 5191.263269737041 | yes |
| `road_hops` | 3 | 3 | yes |

**Semantic equivalence:** pass (exact match on all fields).

### Run commands

```powershell
# PostgreSQL
Get-Content src/queries/postgresql/q1_nearest_hospital.sql |
  docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan `
    -v camp_id=SSD-DS-SS0101_0005 -v max_hops=30

# Neo4j
Get-Content src/queries/neo4j/q1_nearest_hospital.cypher |
  docker exec -i dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev `
    --param "camp_id => 'SSD-DS-SS0101_0005'"
```

### Issues and fixes

- Project files are on the host; Docker containers do not mount the repo — queries are **piped via stdin** (`Get-Content … | docker exec -i`).
- Initial plpgsql Dijkstra draft abandoned after slowness (~3.9 min); replaced with hop-bounded recursive CTE that validates correctly on smoke data.

---

### Discovery query log (Q1)

All queries below were run during Phase 4 Session 1 against live Docker databases.  
**Smoke camp:** `SSD-DS-SS0101_0005` (Don Bosco) unless noted.

Queries that **failed or produced no result** are included for completeness.

#### Q1-D01 — Environment row counts

**Purpose:** Confirm Phase 3 data is loaded.

**PostgreSQL:**
```sql
SELECT COUNT(*) AS health_facilities FROM health_facilities;
SELECT COUNT(*) AS road_nodes FROM road_nodes;
SELECT COUNT(*) AS routing_edges FROM routing_edges;
```

**Result:** 2251 facilities, 24,779 road nodes, 66,533 routing edges.

**Neo4j:**
```cypher
MATCH (n:RoadNode) RETURN count(n) AS road_nodes;
MATCH ()-[r:ROAD_SEGMENT]->() RETURN count(r) AS road_segments;
RETURN gds.version() AS gds_version;
```

**Result:** 24,779 road nodes, 62,345 ROAD_SEGMENT rels, GDS 2.13.10.

**Verdict:** Good — prerequisites OK.

---

#### Q1-D02 — Camp connector and eligible targets

**Purpose:** Verify smoke camp is routable; count Hospital/PHCC targets.

**PostgreSQL:**
```sql
SELECT ds.site_id, ds.site_name, pc.road_node_id, pc.length_m AS camp_connector_m
FROM displacement_sites ds
JOIN poi_connectors pc ON pc.poi_node_id = ds.site_id
WHERE ds.site_id = 'SSD-DS-SS0101_0005';

SELECT COUNT(*) AS eligible_targets
FROM facility_road_access fra
JOIN health_facilities hf ON hf.facility_id = fra.facility_id
WHERE hf.facility_type IN ('Hospital', 'PHCC');
```

**Result:** Don Bosco → road node `2985123616`, connector **714.8 m**; **419** eligible targets.

**Neo4j:** same counts via `DisplacementSite` + `CONNECTOR` and `HealthFacility` filter.

**Verdict:** Good — smoke scenario is valid.

---

#### Q1-D03 — pgRouting availability check

**Purpose:** See if `pgr_dijkstra` is available (preferred production approach for PG).

**PostgreSQL:**
```sql
SELECT extname, extversion FROM pg_extension WHERE extname LIKE 'pgr%' OR extname = 'postgis';
```

**Result:** only `postgis 3.4.3` — **no pgRouting extension**.

**Verdict (historical — Q1-D03, before image swap):** Not available in the then-current stack (`postgis/postgis:16-3.4` image). **Resolved 2026-06-26** — see [pgRouting adoption](#2026-06-26--pgrouting-adoption--dual-track-q1q3) below.

---

#### Q1-D04 — Unbounded recursive CTE (path explosion)

**Purpose:** Naive SQL graph traversal without hop limit.

**PostgreSQL:**
```sql
WITH RECURSIVE
camp AS (
  SELECT pc.road_node_id AS start_road_node_id, pc.length_m AS camp_connector_m
  FROM poi_connectors pc WHERE pc.poi_node_id = 'SSD-DS-SS0101_0005'
),
targets AS (
  SELECT fra.road_node_id, fra.facility_id, fra.connector_length_m,
         hf.facility_name, hf.facility_type
  FROM facility_road_access fra
  JOIN health_facilities hf ON hf.facility_id = fra.facility_id
  WHERE hf.facility_type IN ('Hospital', 'PHCC')
),
search AS (
  SELECT c.start_road_node_id AS node_id, c.camp_connector_m AS cost_m,
         ARRAY[c.start_road_node_id] AS visited, 0 AS hops
  FROM camp c
  UNION ALL
  SELECT re.end_node_id, s.cost_m + re.length_m,
         s.visited || re.end_node_id, s.hops + 1
  FROM search s
  JOIN road_edges re ON re.start_node_id = s.node_id
  WHERE s.hops < 80
    AND NOT re.end_node_id = ANY(s.visited)
)
SELECT t.facility_id, t.facility_name, MIN(s.cost_m + t.connector_length_m) AS total_m
FROM search s JOIN targets t ON t.road_node_id = s.node_id
GROUP BY t.facility_id, t.facility_name, t.facility_type
ORDER BY total_m LIMIT 5;
```

**Result:** **No completion in >3 minutes** (query still running; cancelled manually).

**Verdict:** Bad — enumerates too many simple paths at national scale. Not usable.

---

#### Q1-D05 — Pruned Dijkstra-style recursive CTE (SQL syntax limit)

**Purpose:** Attempt cost-based pruning inside recursion.

**PostgreSQL:**
```sql
-- Recursive arm included:
--   AND d.cost_m + re.length_m < COALESCE(
--         (SELECT MIN(d2.cost_m) FROM dijkstra d2 WHERE d2.node_id = re.end_node_id),
--         'Infinity'::double precision)
```

**Result:** `ERROR: recursive reference to query "dijkstra" must not appear within a subquery`

**Verdict:** Bad — PostgreSQL disallows this pattern; not runnable.

---

#### Q1-D06 — Hop-bounded recursive CTE (`max_hops = 25`)

**Purpose:** Bounded path exploration; time vs correctness tradeoff.

**PostgreSQL:** same structure as Q1-D04 with `s.hops < 25`.

**Result (~12 s):**

| facility_id | facility_name | total_m |
|-------------|---------------|---------|
| SSD-HF-000126 | Gumbo PHCC | 5191.26 |
| SSD-HF-000069 | Sacred Heart PHCC | 6970.58 |
| SSD-HF-000066 | Kator PHCC | 7982.74 |
| SSD-HF-000067 | Lologo PHCC | 8080.61 |
| SSD-HF-000068 | Malakia PHCC | 8194.94 |

**Verdict:** **Produces a solution** and matches GDS winner on smoke camp. **Approximation** — not guaranteed globally optimal; misses paths needing >25 hops.

---

#### Q1-D07 — Hop-bounded recursive CTE (`max_hops = 30`)

**Purpose:** Slightly higher hop cap; selected for final artifact.

**Result (~36 s):** same winner — **Gumbo PHCC, 5191.26 m**, 3 road hops.

**Verdict:** **Selected PostgreSQL implementation** (see `src/queries/postgresql/q1_nearest_hospital.sql`). Still an approximation, but validated against GDS on smoke camp.

---

#### Q1-D08 — plpgsql Dijkstra with temp frontier tables

**Purpose:** True distance-minimizing Dijkstra in PostgreSQL without pgRouting.

**Approach:** `pg_temp.q1_nearest_hospital()` — temp tables `_q1_dist` / `_q1_frontier`, iteratively pop minimum-cost node, relax `road_edges`.

**Result (~233 s / ~3.9 min):**

| camp_id | facility_id | facility_name | total_m | road_hops |
|---------|-------------|---------------|---------|-----------|
| SSD-DS-SS0101_0005 | SSD-HF-000126 | Gumbo PHCC | 5191.26 | 3 |

**Verdict:** **Correct solution**, same as GDS. **Bad for benchmarking** — interpreted plpgsql loop over ~62k edges is too slow. Not kept as final artifact; documented here as proof that exact Dijkstra is possible in PG without pgRouting, but impractical.

---

#### Q1-D09 — Neo4j hop-based `shortestPath()` (comparison)

**Purpose:** Compare hop-min vs distance-min semantics.

**Cypher:**
```cypher
MATCH (c:DisplacementSite {poi_node_id: 'SSD-DS-SS0101_0005'})-[cOut:CONNECTOR]->(start:RoadNode)
MATCH (hf:HealthFacility {facility_id: 'SSD-HF-000126'})-[hOut:CONNECTOR]->(end:RoadNode)
MATCH p = shortestPath((start)-[:ROAD_SEGMENT*]->(end))
RETURN hf.name,
       cOut.length_m + reduce(d=0.0, r IN relationships(p) | d + r.length_m) + hOut.length_m AS hop_path_total_m,
       length(p) AS hops;
```

**Result:** Gumbo PHCC, **5191.26 m**, **3 hops** — same as GDS for this facility.

**Verdict:** **Produces a solution** on smoke camp, but `shortestPath()` minimizes **hops**, not meters. Ranking all 419 facilities by hop-first paths could pick a different winner elsewhere. **Rejected** for final Q1; kept for comparison.

---

#### Q1-D10 — Neo4j GDS graph projection (discovery)

**Purpose:** Prepare distance-weighted road layer for Dijkstra.

**Cypher:**
```cypher
CALL gds.graph.project(
  'q1_road_discovery',
  'RoadNode',
  { ROAD_SEGMENT: { orientation: 'NATURAL', properties: 'length_m' } }
)
YIELD graphName, nodeCount, relationshipCount;
```

**Result:** 24,779 nodes, 62,345 relationships.

**Verdict:** Good — projection works; renamed to `q1_road_network` in final artifact.

---

#### Q1-D11 — Neo4j GDS `allShortestPaths.dijkstra` (discovery ranking)

**Purpose:** Distance-weighted shortest paths from camp road node to all Hospital/PHCC access nodes.

**Cypher:**
```cypher
MATCH (c:DisplacementSite {poi_node_id: 'SSD-DS-SS0101_0005'})-[cOut:CONNECTOR]->(start:RoadNode)
WITH c, cOut, id(start) AS sourceNode
CALL gds.allShortestPaths.dijkstra.stream('q1_road_discovery', {
  sourceNode: sourceNode,
  relationshipWeightProperty: 'length_m'
})
YIELD targetNode, totalCost AS road_cost_m
MATCH (end:RoadNode) WHERE id(end) = targetNode
MATCH (hf:HealthFacility)-[hOut:CONNECTOR]->(end)
WHERE hf.facility_type IN ['Hospital', 'PHCC']
WITH c, hf, cOut, hOut, road_cost_m,
     cOut.length_m + road_cost_m + hOut.length_m AS total_m
ORDER BY total_m ASC
LIMIT 5
RETURN c.poi_node_id, hf.facility_id, hf.name, total_m, road_cost_m;
```

**Result (~6 s excl. projection):**

| facility_id | name | total_m | road_cost_m |
|-------------|------|---------|-------------|
| SSD-HF-000126 | Gumbo PHCC | 5191.26 | 3842.05 |
| SSD-HF-000069 | Sacred Heart PHCC | 6970.58 | 6183.55 |
| SSD-HF-000066 | Kator PHCC | 7982.74 | 7066.33 |
| … | … | … | … |

**Verdict:** **Selected Neo4j approach** — true Dijkstra on `length_m`. Final artifact: `src/queries/neo4j/q1_nearest_hospital.cypher` (~52 s incl. drop/project on cold run).

---

#### Q1-D12 — Final validated artifacts (selected)

| ID | File | Runtime (smoke) | Winner | total_m |
|----|------|-----------------|--------|---------|
| **Final PG** | `src/queries/postgresql/q1_nearest_hospital.sql` | ~36 s | Gumbo PHCC | 5191.26 |
| **Final Neo4j** | `src/queries/neo4j/q1_nearest_hospital.cypher` | ~52 s | Gumbo PHCC | 5191.26 |

Cross-database match: **exact** on all output fields.

---

### pgRouting notes (Q1 discovery — historical context)

**Is pgRouting the proper PostgreSQL solution for Dijkstra?**  
Yes. [pgRouting](https://pgrouting.org/) adds `pgr_dijkstra`, `pgr_dijkstraCost`, etc. on a `edge`/`vertex` topology — the standard production approach for road-network shortest path in PostGIS.

**Why pgRouting was missing initially (Q1-D03):**

| Reason | Detail |
|--------|--------|
| **Not in the original Docker image** | Phase 3 used `postgis/postgis:16-3.4`; Q1-D03 showed only `postgis` — pgRouting is a separate extension. |
| **Never part of Phase 3 setup** | Loaders and schema were built around plain PostGIS + `road_edges` / `routing_edges`. |

**Resolution (2026-06-26):** adopted dual-track PostgreSQL — **PG-pgRouting** (primary, fair vs Neo4j GDS) and **PG-CTE** (secondary baseline showing SQL without extensions). See [`phase4_pgrouting_adoption_and_routing_queries.md`](phase4_pgrouting_adoption_and_routing_queries.md).

**Compatibility with your two machines (Ryzen Windows + Apple Silicon macOS):**

pgRouting runs **inside PostgreSQL**, not on the host CPU directly. What matters is the **Postgres container architecture**:

| Host | PostGIS container | pgRouting if installed |
|------|-------------------|------------------------|
| **Windows Ryzen (project benchmark host)** | `linux/amd64` **native** | Would run natively in the same container — **fully compatible**, fair timings. |
| **macOS Apple Silicon (dev host)** | `linux/amd64` **emulated** (PostGIS image has no arm64 build) | Would run under the **same amd64 emulation** as PostGIS — **works**, but slower; same unfair-timing caveat as Phase 3 docs. |

pgRouting itself is a normal PostgreSQL C extension built for Linux x86_64 in the container. There is no Apple Silicon–specific blocker — the Apple Silicon issue in this project is that **PostGIS is always emulated amd64**, not that pgRouting lacks arm64 support.

**Adopted in Phase 4 (2026-06-26):** switched to `pgrouting/pgrouting:16-3.5-4.0`; see [`phase4_pgrouting_adoption_and_routing_queries.md`](phase4_pgrouting_adoption_and_routing_queries.md) §3 and pgRouting Q1 artifacts (`q1_nearest_hospital_pgrouting.sql`).

---

## 2026-06-26 — pgRouting adoption + dual-track Q1–Q3

### Infrastructure

| Change | Detail |
|--------|--------|
| Docker image | `postgis/postgis:16-3.4` → `pgrouting/pgrouting:16-3.5-4.0` |
| Schema | `CREATE EXTENSION IF NOT EXISTS pgrouting` in `src/db/postgresql/schema.sql` |
| Loader | `scripts/load_postgresql.py` prints PostGIS + pgRouting versions after load |
| Existing volume | `CREATE EXTENSION pgrouting` on migrated DB — **no full re-populate required** |

Verified on Windows amd64: pgRouting **4.0.1**, PostGIS **3.4.3** (existing volume), container `x86_64`.

### Q1 — pgRouting track

| Platform | File | Approach | Smoke `total_m` |
|----------|------|----------|-----------------|
| PG-CTE (secondary) | `q1_nearest_hospital.sql` | Hop-bounded recursive CTE | 5191.26 |
| **PG-pgRouting (primary)** | `q1_nearest_hospital_pgrouting.sql` | `pgr_dijkstraCost` → 419 targets | **5191.26** |
| Neo4j-GDS (primary) | `q1_nearest_hospital.cypher` | GDS Dijkstra | **5191.26** |

**Semantic equivalence:** pass — pgRouting matches GDS and CTE on Don Bosco smoke camp.

### Q2 — All SS01 camps → Juba Teaching Hospital

| Platform | File | Rows | Match |
|----------|------|------|-------|
| PG-pgRouting | `q2_state_camps_to_hospital_pgrouting.sql` | 15 | — |
| Neo4j-GDS | `q2_state_camps_to_hospital.cypher` | 15 | **exact `total_m` on all camps** |
| PG-CTE | `q2_state_camps_to_hospital.sql` | 15 | same distances (slow — 15× recursive search) |

Example: Mahad → JTH **3301.32 m** (pgRouting = Neo4j).

### Q3 — Hub HUB-001 reachability (50 km)

| Platform | File | Reachable | Isolated |
|----------|------|-----------|----------|
| PG-pgRouting | `q3_hub_reachability_pgrouting.sql` | 6 | 71 |
| Neo4j-GDS | `q3_hub_reachability.cypher` | 6 | 71 |
| PG-CTE | `q3_hub_reachability.sql` | (same logic) | |

Reachable camps match pgRouting ↔ Neo4j on `total_m` (e.g. Mahad **3320.65 m**).

### Phase 5 benchmark harness

`scripts/benchmark_routing_queries.py` — three tracks × Q1–Q3, warmup + median latency, writes `output/routing_benchmark_results.json`.

**2026-06-26 Windows amd64 run** (`--runs 2 --warmup 1`):

| Query | PG-CTE | PG-pgRouting | Neo4j-GDS |
|-------|--------|--------------|-----------|
| Q1 | 74.9 s | **0.15 s** | 25.1 s |
| Q2 | skipped (too slow) | **0.60 s** | 9.3 s |
| Q3 | skipped (too slow) | **0.14 s** | 8.8 s |

Primary comparison: **PG-pgRouting vs Neo4j-GDS**. Q2/Q3 PG-CTE omitted from automated harness (national-scale recursive CTE impractical).

---

### Remaining (Phase 4)

- [ ] Q4 — State humanitarian stats + national road km
- [x] Q2 — All camps in state → one referral hospital (dual-track PG + Neo4j)
- [x] Q3 — Hub reachability within 50 km (dual-track PG + Neo4j)
- [ ] Q5 — Evacuation max flow
