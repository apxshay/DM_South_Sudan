# Phase 4 — pgRouting Adoption, Routing Queries & Pilot Benchmarks

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Date:** 2026-06-26  
**Status:** In progress — Q1–Q3 routing complete (dual-track); Q4 and Q5 pending

**Companion logs:**  
- Technical progress (discovery queries, per-query notes): [`phase4_query_implementation.md`](phase4_query_implementation.md)  
- Query specification: [`phase5_benchmark_queries.md`](phase5_benchmark_queries.md)  
- Setup pipeline: [`README.md`](../README.md)

---

## 1. Executive summary

Phase 4 implements the five benchmark queries (Q1–Q5) in PostgreSQL and Neo4j. Early work on **Q1** exposed a critical gap: the original PostgreSQL stack (`postgis/postgis:16-3.4`) had **no pgRouting**, so routing had to use recursive CTEs — slow, approximate, and unsuitable for a fair thesis comparison against Neo4j **GDS Dijkstra**.

We adopted a **dual-track** PostgreSQL strategy:

| Track | Purpose |
|-------|---------|
| **PG-CTE** | Secondary baseline — “pure SQL without extensions” |
| **PG-pgRouting** | **Primary PostgreSQL** — industry-standard routing (`pgr_dijkstraCost`) |
| **Neo4j-GDS** | **Primary graph** — distance-weighted Dijkstra |

**Infrastructure change:** pgRouting is **not** a retroactive add-on after Phase 3. From a fresh clone, the **`pgrouting/pgrouting:16-3.5-4.0`** Docker image is used at **Step 4** (start databases), and **`CREATE EXTENSION pgrouting`** runs automatically at **Step 5** (populate via `schema.sql`).

**Completed in this phase (routing):** Q1, Q2, Q3 — all three tracks where practical.  
**Remaining:** Q4 (relational aggregations), Q5 (max-flow).

---

## 2. What problem we hit (Q1 discovery)

### 2.1 Initial PostgreSQL Q1

The first working PostgreSQL Q1 used a **hop-bounded recursive CTE** on `road_edges` (`max_hops=30`). It returned the correct answer on the smoke camp (Don Bosco → Gumbo PHCC, **5191.26 m**) and matched Neo4j GDS, but:

- It is **not true Dijkstra** — it enumerates simple paths up to a hop cap.
- **Unbounded** recursive CTE did not finish in >3 minutes.
- **plpgsql Dijkstra** (hand-rolled) was correct but ~3.9 minutes per query.
- **pgRouting** was probed and **not installed** in the original Docker image.

Neo4j Q1 uses **GDS `allShortestPaths.dijkstra`** with `length_m` weights — true distance minimization.

### 2.2 Why pgRouting matters for the thesis

The project goal is comparing **real systems** at their best. Comparing Neo4j GDS Dijkstra to a hop-bounded SQL approximation would let reviewers argue the PostgreSQL side was handicapped. pgRouting restores a fair **primary** comparison: **PG-pgRouting vs Neo4j-GDS**.

The **PG-CTE** track is kept deliberately as a **supporting** narrative: “what happens if you try routing in SQL without extensions.”

---

## 3. Infrastructure changes (pgRouting at the correct pipeline step)

### 3.1 Fresh install pipeline (correct order)

| Step | Action | pgRouting relevance |
|------|--------|---------------------|
| 0–2 | Clone, conda, bootstrap data | None — Phase 1–2 unchanged |
| 3 | Copy `.env.example` → `.env` | None |
| **4** | **`docker compose up -d`** | Uses image **`pgrouting/pgrouting:16-3.5-4.0`** (PostGIS + pgRouting binaries in container) |
| **5** | **`python scripts/populate_databases.py --reset`** | `schema.sql` runs **`CREATE EXTENSION IF NOT EXISTS pgrouting`** before tables |
| 6 | Validate counts + extensions | Confirm `pgrouting` 4.0.1 present |
| 7 | Run Phase 4 queries | Use files under `src/queries/` |

No separate “install pgRouting after everything” step exists on a fresh machine.

### 3.2 Files changed

| File | Change |
|------|--------|
| [`docker-compose.yml`](../docker-compose.yml) | `image: pgrouting/pgrouting:16-3.5-4.0` |
| [`src/db/postgresql/schema.sql`](../src/db/postgresql/schema.sql) | `CREATE EXTENSION IF NOT EXISTS pgrouting` |
| [`scripts/load_postgresql.py`](../scripts/load_postgresql.py) | Prints PostGIS + pgRouting versions after load |

### 3.3 Migrating an existing dev machine (already on old `postgis/postgis` image)

If you populated databases **before** this change:

1. `git pull` (or sync) to get updated `docker-compose.yml` and `schema.sql`.
2. `docker compose pull postgis`
3. `docker compose up -d`
4. Enable extension on the **existing volume** (data preserved):

   ```powershell
   docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "CREATE EXTENSION IF NOT EXISTS pgrouting;"
   ```

5. Verify:

   ```powershell
   docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis', 'pgrouting');"
   ```

**Re-populate is not required** if counts were already correct — only the extension and query files are new.

If PostGIS upgrade errors appear after image swap, reset volume:

```powershell
docker compose down -v
docker compose up -d
python scripts\populate_databases.py --reset
```

### 3.4 Apple Silicon (macOS dev)

pgRouting runs **inside** the same PostGIS container as before. Apple Silicon still runs PostGIS as **emulated amd64** — pgRouting does not add a new platform issue. **Phase 5 fair timings** remain Windows amd64 only.

---

## 4. Query artifacts (Q1–Q3)

Parameters: [`src/queries/_benchmark_params.yaml`](../src/queries/_benchmark_params.yaml)

### 4.1 File map

| Query | PG-CTE (secondary) | PG-pgRouting (primary) | Neo4j-GDS (primary) |
|-------|-------------------|------------------------|---------------------|
| Q1 | `postgresql/q1_nearest_hospital.sql` | `postgresql/q1_nearest_hospital_pgrouting.sql` | `neo4j/q1_nearest_hospital.cypher` |
| Q2 | `postgresql/q2_state_camps_to_hospital.sql` | `postgresql/q2_state_camps_to_hospital_pgrouting.sql` | `neo4j/q2_state_camps_to_hospital.cypher` |
| Q3 | `postgresql/q3_hub_reachability.sql` | `postgresql/q3_hub_reachability_pgrouting.sql` | `neo4j/q3_hub_reachability.cypher` |

### 4.2 Shared cost model

All routing queries use **directed** edges and meter-based cost:

```
total_m = start_connector_m + SUM(road_segment.length_m) + end_connector_m
```

pgRouting edge SQL (reused in Q1–Q3):

```sql
SELECT edge_id AS id,
       start_node_id AS source,
       end_node_id AS target,
       length_m AS cost,
       CASE WHEN oneway IS TRUE THEN -1 ELSE length_m END AS reverse_cost
FROM road_edges
```

### 4.3 Correctness validation

| Query | Check | Result |
|-------|-------|--------|
| Q1 smoke (`SSD-DS-SS0101_0005`) | Nearest Hospital/PHCC | **Gumbo PHCC**, **5191.26 m** — exact match PG-CTE, PG-pgRouting, Neo4j-GDS |
| Q2 (`SS01` → `SSD-HF-000055`) | 15 camps | **Exact `total_m` match** PG-pgRouting ↔ Neo4j-GDS (all 15 rows) |
| Q3 (`HUB-001`, 50 km) | Reachable / isolated | **6 reachable, 71 isolated** — PG-pgRouting ↔ Neo4j-GDS match on reachable camps |

### 4.4 How to run queries (project dir is not mounted in Docker — pipe via stdin)

**Q1 pgRouting (PostgreSQL):**

```powershell
Get-Content src/queries/postgresql/q1_nearest_hospital_pgrouting.sql |
  docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan `
    -v camp_id=SSD-DS-SS0101_0005
```

**Q1 Neo4j GDS:**

```powershell
Get-Content src/queries/neo4j/q1_nearest_hospital.cypher |
  docker exec -i dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev `
    --param "camp_id => 'SSD-DS-SS0101_0005'"
```

See [`database_usage_guide.md`](database_usage_guide.md) Section 11 for all Q1–Q3 commands.

---

## 5. Pilot benchmark (routing Q1–Q3)

Harness: [`scripts/benchmark_routing_queries.py`](../scripts/benchmark_routing_queries.py)  
Results: [`output/routing_benchmark_results.json`](../output/routing_benchmark_results.json)

Run on **Windows amd64** (fair container architecture):

```powershell
conda activate dm-south-sudan
python scripts/benchmark_routing_queries.py --runs 5 --warmup 1
```

Use `--skip-slow-cte` to skip Q2/Q3 PG-CTE (they do not finish in practical time).

### 5.1 Results (2026-06-26, `--runs 2 --warmup 1`, Windows Ryzen)

| Query | PG-CTE median | PG-pgRouting median | Neo4j-GDS median |
|-------|---------------|---------------------|------------------|
| Q1 | **74.9 s** | **0.15 s** | **25.1 s** |
| Q2 | *skipped* | **0.60 s** | **9.3 s** |
| Q3 | *skipped* | **0.14 s** | **8.8 s** |

### 5.2 Analysis — why these numbers look this way

#### PG-pgRouting (0.14–0.60 s) — fast and stable

- `pgr_dijkstraCost` is a **compiled C extension** over a pre-indexed edge table.
- Q1 calls once with an array of 419 target nodes; Q2 loops 15 source→target pairs; Q3 one multi-target call from hub.
- Timings are **trustworthy** for thesis primary comparison.

#### PG-CTE Q1 (~75 s) — slow but completes

- Hop-bounded recursive CTE explores many simple paths on ~62k edges.
- Result is **correct on smoke data** but algorithmically wrong class (approximation).
- Useful thesis point: “without pgRouting, even a bounded CTE is ~500× slower than pgRouting on Q1.”

#### PG-CTE Q2/Q3 — skipped (critical finding)

- **Q2:** 15 nested recursive searches — did not complete in practical time (>10 min observed).
- **Q3:** Even with `max_hops=50`, national-scale path enumeration did not finish in reasonable time.
- **Thesis implication:** multi-source / reachability in pure SQL is not merely slow — it is **operationally unusable** at this graph size without extensions.

#### Neo4j-GDS (3–47 s on Q1; ~9 s on Q2/Q3) — high variance on Q1

Observed Q1 timings: **47.0 s** then **3.2 s** (median **25.1 s**).

**Causes:**

1. **GDS graph projection** — each query file drops and recreates an in-memory graph (`q1_road_network`). First run pays full projection cost (~62k relationships); second run benefits from JVM/GDS warm caches.
2. **Cold vs warm JVM** — Neo4j container may still be warming on first timed run after restart.
3. **Only 2 runs** — median is unstable; Phase 5 should use **N ≥ 5** after explicit warm-up.

**Recommendation for Phase 5:**

- Separate **projection time** from **query time** in reporting, or use a **persistent GDS graph** across runs.
- Run **5+ timed iterations** after **2 warm-up** runs that are discarded.
- Report Neo4j as: *projection + dijkstra* if projection is part of the operational workflow.

#### Surprising result: pgRouting faster than Neo4j on these queries

On this dataset and implementation, **PG-pgRouting medians are lower than Neo4j-GDS medians** for Q1–Q3. This is **plausible**:

- PostgreSQL reads from persistent disk-backed tables with B-tree indexes on edge endpoints.
- Neo4j pays **per-query projection** overhead in our current Cypher files.
- This does **not** mean PostgreSQL is universally faster for graph workloads — it reflects **this** query shape, **this** data size, and **this** Neo4j usage pattern (ephemeral GDS graphs).

**Thesis wording:** compare **fair algorithms** (Dijkstra on meters), note **implementation overhead** (GDS projection), and avoid over-generalizing from three routing queries.

### 5.3 Issues encountered during benchmarking

| Issue | Cause | Fix applied |
|-------|-------|-------------|
| Unicode error piping SQL on Windows | `subprocess` default cp1252 vs UTF-8 comments (`→`, `—`) | `encoding='utf-8'` in benchmark script |
| Long-running PG-CTE blocking Postgres | Q2/Q3 CTE path explosion | `--skip-slow-cte`; document as `skipped_slow` |
| Hung benchmark sessions | Killed mid-query | Restart PostGIS container to clear locks |
| Unstable Neo4j Q1 times | Cold GDS projection | Phase 5: more runs + warm-up + optional persistent graph |

---

## 6. Recommendations

### For the thesis

1. **Primary routing comparison:** PG-pgRouting vs Neo4j-GDS only.
2. **Secondary narrative:** PG-CTE on Q1 (and note Q2/Q3 CTE impracticality).
3. **Document** Docker image tags, extension versions, and `uname -m` inside containers.
4. **Neo4j Phase 5:** report projection vs query time separately; increase run count.

### For the codebase (optional improvements)

| Priority | Item |
|----------|------|
| High | Phase 5 harness: persistent GDS graph or cached projection |
| Medium | `scripts/run_query.py` — run any query by name with params from YAML |
| Low | Q4/Q5 implementation (remaining Phase 4 work) |
| Low | pgRouting topology table (`pgr_createTopology`) — not required; edge SQL works on existing `road_edges` |

---

## 7. Phase 4 completion checklist

| Item | Status |
|------|--------|
| pgRouting in Docker + schema | Done |
| Q1 dual-track + Neo4j GDS | Done |
| Q2 dual-track + Neo4j GDS | Done |
| Q3 dual-track + Neo4j GDS | Done |
| Pilot routing benchmark | Done (`output/routing_benchmark_results.json`) |
| Q4 PostgreSQL + Neo4j | Pending |
| Q5 NetworkX + GDS maxFlow | Pending |
| Formal Phase 5 (N runs, complexity metrics) | Pending |

---

## Related documents

- [`README.md`](../README.md) — full pipeline Steps 0–7  
- [`phase4_query_implementation.md`](phase4_query_implementation.md) — detailed discovery log  
- [`phase3_database_population.md`](phase3_database_population.md) — counts, migration notes  
- [`phase5_benchmark_queries.md`](phase5_benchmark_queries.md) — dual-track benchmark matrix  
- [`database_usage_guide.md`](database_usage_guide.md) — daily use + query commands  
- [`AGENT_PHASE4.md`](../AGENT_PHASE4.md) — agent instructions (updated)
