# Phase 3 — Database Population

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Date:** 2026-06-25  
**Status:** Complete — loaders validated on macOS (development) and Windows 10 amd64 (benchmark host)

**Setup guide:** follow [`README.md`](../README.md) for the full Windows and macOS pipeline (Steps 1–6). **Day-to-day usage** (connect, query, GUI): [`database_usage_guide.md`](database_usage_guide.md). This document records **what was built**, **expected counts**, **platform differences**, and **known issues**.

---

## Platform guidance

| Platform | CPU | Neo4j Docker | PostGIS Docker | Use for Phase 5 timings? |
|----------|-----|--------------|----------------|--------------------------|
| **Windows 10/11 + Ryzen** | `amd64` | `linux/amd64` native | `linux/amd64` native | **Yes — recommended** |
| macOS Apple Silicon | `arm64` | `linux/arm64` native | `linux/amd64` **emulated** | **No** — PostgreSQL penalized |
| macOS Intel / Linux amd64 | `amd64` | native | native | Yes |

Official images (pinned in `docker-compose.yml`):

- **PostGIS** `pgrouting/pgrouting:16-3.5-4.0` — **`linux/amd64` only** (PostGIS + pgRouting 4.0.1)
- **Neo4j** `neo4j:5.26-community` — `linux/amd64` and `linux/arm64/v8` ([Docker Hub](https://hub.docker.com/_/neo4j))

### Platform-specific configuration

| Setting | Windows (typical) | macOS (typical) |
|---------|-------------------|-----------------|
| Postgres host port | `5432` in `.env` | `5432` or **`5433`** if local Postgres occupies 5432 |
| Docker backend | Docker Desktop + WSL 2 | Docker Desktop |
| `conda` / `docker` on PATH | Often missing in default PowerShell — use Miniforge Prompt | Usually available after `conda init` |
| Confirm amd64 for benchmarks | `docker exec … uname -m` → `x86_64` | Apple Silicon shows `aarch64` for Neo4j, PostGIS still amd64 under emulation |

---

## What was implemented (2026-06-25)

1. Docker Compose stack (`docker-compose.yml`) — PostGIS + Neo4j with APOC and GDS plugins.
2. Connection config — `.env.example`, `src/db/db_config.py` (gitignored `.env` locally).
3. Loaders:
   - `scripts/load_postgresql.py` — applies `schema.sql`, loads CSV/GPKG in FK order, validates counts
   - `scripts/load_neo4j.py` — MERGE-based import, applies `constraints.cypher`, validates counts
   - `scripts/populate_databases.py` — runs both loaders
4. Reference SQL/Cypher — `src/db/postgresql/load_data.sql`, `src/db/neo4j/import.cypher`.

### Database versions

| Component | Version | Notes |
|-----------|---------|-------|
| PostgreSQL | 16.x | Image `pgrouting/pgrouting:16-3.5-4.0` |
| PostGIS | 3.4+ | Enabled in `schema.sql` |
| pgRouting | 4.0.1 | `CREATE EXTENSION pgrouting` in `schema.sql` |
| Neo4j | 5.26.x Community | Image `neo4j:5.26-community` |
| APOC | bundled | `NEO4J_PLUGINS` in compose |
| GDS | 2.13.x | `RETURN gds.version()` in Neo4j |

Default dev password: `dm_ssd_dev` (from `.env.example`).

### Validated hosts

| Host | OS | Docker | Populate time | Container arch |
|------|-----|--------|---------------|----------------|
| Development (macOS) | Apple Silicon | Desktop | ~10–15 min | Neo4j arm64, PostGIS emulated amd64 |
| Benchmark (Windows) | Win 10 19045, Ryzen 5 | Desktop 4.78+ / WSL 2 | ~9 min | Both `x86_64` |

---

## Row / relationship counts (parity)

| Entity | Expected | PostgreSQL | Neo4j | Notes |
|--------|----------|------------|-------|-------|
| Road nodes | 24,779 | 24,779 | 24,779 | |
| Road edges / `ROAD_SEGMENT` | 62,345 | 62,345 | 62,345 | Directed arcs preserved |
| Health facilities (spatial) | 2,017 | 2,017 (`facility_road_access`) | 2,017 (`HealthFacility`) | |
| Health facilities (all) | 2,251 | 2,251 (`health_facilities`) | — | 234 without coordinates omitted from graph |
| Displacement sites | 77 | 77 | 77 | |
| Connectors | 2,094 | 2,094 (`poi_connectors`) | 2,094 (`CONNECTOR`) | |
| `CONNECTOR_REVERSE` | 2,094 | 2,094 (`routing_edges`) | 2,094 | Required for Q5 max-flow |
| Logistical hubs | 5 | 5 | 5 | Secondary `LogisticalHub` label in Neo4j |
| Routing edges (unified) | 66,533 | 66,533 | — | PostgreSQL-only denormalized layer |

---

## Q1 smoke test prerequisites

| Check | PostgreSQL | Neo4j |
|-------|------------|-------|
| Camp `SSD-DS-SS0101_0005` has connector to road | 1 | 1 |
| Hospital `SSD-HF-000055` has connector | 1 | 1 |
| Hospital in `logistical_hubs` / `LogisticalHub` | 1 | 1 |
| Routable Hospital/PHCC facilities | 419 | 419 |

PostGIS geometry spot-checks (`ST_IsValid`, 100 rows each on points/lines): all passed.

---

## Validation commands

Run after `populate_databases.py --reset`. See [`README.md`](../README.md) Step 6 for the quick checklist.

**PostgreSQL — ad hoc counts**

```powershell
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM health_facilities;"
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM road_edges;"
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM routing_edges;"
```

**PostgreSQL — full reference script**

```bash
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -f src/db/postgresql/load_data.sql
```

**Neo4j**

```powershell
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "MATCH (n:RoadNode) RETURN count(n);"
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "MATCH ()-[r:CONNECTOR_REVERSE]->() RETURN count(r);"
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "RETURN gds.version();"
```

```bash
docker exec -i dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev < src/db/neo4j/import.cypher
```

**Architecture (benchmark hosts only)**

```powershell
docker exec dm-south-sudan-neo4j uname -m
docker exec dm-south-sudan-postgis uname -m
```

Expect `x86_64` on Windows/Ryzen.

---

## pgRouting image upgrade (Phase 4, 2026-06-26)

Phase 4 routing requires **pgRouting**. The Docker service now uses **`pgrouting/pgrouting:16-3.5-4.0`** instead of `postgis/postgis:16-3.4`.

### Fresh clone

Follow [`README.md`](../README.md) Steps 4–5 — extension is created automatically by `schema.sql`.

### Existing populated database

1. `docker compose pull postgis && docker compose up -d`
2. `CREATE EXTENSION IF NOT EXISTS pgrouting;` (data volume preserved)
3. Verify: `SELECT extname, extversion FROM pg_extension WHERE extname = 'pgrouting';`

Full narrative: [`phase4_pgrouting_adoption_and_routing_queries.md`](phase4_pgrouting_adoption_and_routing_queries.md) §3.

---

## Issues encountered and fixes

| # | Issue | Platform | Fix / workaround |
|---|-------|----------|------------------|
| 1 | Local Postgres on port 5432 | macOS | Set `POSTGRES_PORT=5433` in `.env` |
| 2 | `routing_edges.capacity` float → bigint import error | All | Fixed in `load_postgresql.py` with explicit `int()` casting |
| 3 | `execute_values` batch failures | All | Reduced `page_size` from 5000 to 1000 |
| 4 | Unfair benchmark timings | macOS Apple Silicon | PostGIS emulated; use Windows amd64 for Phase 5 |
| 5 | `conda` / `docker` not on PATH | Windows | Miniforge Prompt or add Scripts + Docker `resources\bin` to PATH |
| 6 | Docker Desktop not installed | Windows | Install Docker Desktop; start before `docker compose up` |
| 7 | `bootstrap.ps1` fails at Phase 2 (`scripts\health` not found) | Windows | Unicode em dash in step labels broke `conda run`; fixed in `bootstrap.ps1` (ASCII hyphens). Resume: `.\scripts\bootstrap.ps1 -SkipDownload -From network` |
| 8 | pgRouting missing after Phase 4 image upgrade | All | `CREATE EXTENSION IF NOT EXISTS pgrouting;` or `populate_databases.py --reset` |

---

## Related documents

- [`README.md`](../README.md) — **main setup guide** (Windows + macOS)
- [`database_usage_guide.md`](database_usage_guide.md) — **day-to-day use** (connect, SQL, Cypher)
- [`AGENT_PHASE3.md`](../AGENT_PHASE3.md) — Phase 3 agent instructions
- [`docs/phase2_relational_schema.md`](phase2_relational_schema.md)
- [`docs/phase2_graph_schema.md`](phase2_graph_schema.md)
- [`phase4_pgrouting_adoption_and_routing_queries.md`](phase4_pgrouting_adoption_and_routing_queries.md)
- [`phase5_benchmark_queries.md`](phase5_benchmark_queries.md)
