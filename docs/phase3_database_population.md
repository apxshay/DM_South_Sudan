# Phase 3 — Database Population

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Date:** 2026-06-25  
**Status:** Complete — loaders implemented and validated (development on macOS; **recommended benchmark host: Windows 10 + AMD Ryzen 5**)

---

## Platform guidance (read before benchmarking)

| Platform | CPU arch | Neo4j Docker | PostGIS Docker | Fair RDBMS vs graph timing? |
|----------|----------|--------------|----------------|-------------------------------|
| **Windows 10 + Ryzen 5** | `amd64` native | `linux/amd64` native | `linux/amd64` native | **Yes — recommended** |
| macOS Apple Silicon (M1/M2) | `arm64` | `linux/arm64` native | `linux/amd64` **emulated** | **No** — PostgreSQL penalized |
| macOS Intel | `amd64` | native | native | Yes |

Official images used by this project:

- **Neo4j** `neo4j:5.26-community` — publishes `linux/amd64` and `linux/arm64/v8` ([Docker Hub](https://hub.docker.com/_/neo4j)).
- **PostGIS** `postgis/postgis:16-3.4` — publishes **`linux/amd64` only** ([docker-postgis README](https://github.com/postgis/docker-postgis)).

On **Windows 10 with an AMD Ryzen 5** (x86-64), Docker Desktop runs both containers **natively** with no CPU emulation. This is the intended environment for Phase 5 performance benchmarks.

**Windows 10 prerequisites:**

- 64-bit Windows 10 Pro/Enterprise/Education 22H2+ (or Windows 11)
- Virtualization enabled in BIOS (AMD-V / SVM)
- [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) with **WSL 2** backend
- [Miniforge](https://github.com/conda-forge/miniforge/releases) (Windows x86_64 installer)
- ~8 GB RAM minimum (Neo4j + PostGIS + data pipeline); 16 GB recommended
- ~2 GB free disk for Docker images; ~1 GB for raw/processed data

---

## 2026-06-25 — Initial population

### What was done

1. Added Docker Compose stack (`docker-compose.yml`) for PostGIS + Neo4j (APOC + GDS plugins).
2. Added connection config (`.env.example`, `src/db/db_config.py`).
3. Implemented reproducible loaders:
   - `scripts/load_postgresql.py` — applies `schema.sql`, loads all tables in FK order, validates counts
   - `scripts/load_neo4j.py` — MERGE-based import, applies `constraints.cypher`, validates counts
   - `scripts/populate_databases.py` — runs both loaders
4. Added reference SQL/Cypher: `src/db/postgresql/load_data.sql`, `src/db/neo4j/import.cypher`.
5. Validated row/relationship counts and Q1 smoke prerequisites on development hardware.
6. Documented platform differences (native amd64 on Ryzen vs mixed native/emulated on Apple Silicon).

### Deliverables added in Phase 3

```
docker-compose.yml
.env.example
src/db/db_config.py
src/db/postgresql/load_data.sql
src/db/neo4j/import.cypher
scripts/load_postgresql.py
scripts/load_neo4j.py
scripts/populate_databases.py
docs/phase3_database_population.md
```

### Database versions (pinned in `docker-compose.yml`)

| Component | Version | Connection |
|-----------|---------|------------|
| PostgreSQL | 16.4 | Docker `postgis/postgis:16-3.4` |
| PostGIS | 3.4 | Extension enabled via `schema.sql` |
| Neo4j | 5.26 Community | Docker `neo4j:5.26-community` |
| APOC | bundled | `NEO4J_PLUGINS` in compose |
| GDS | 2.13.x | `RETURN gds.version()` in Neo4j Browser |

Credentials: gitignored `.env` (copy from `.env.example`). Default dev password: `dm_ssd_dev`.

**Port note:** `.env.example` uses `POSTGRES_PORT=5432` (standard on Windows/Ryzen). On macOS, if a local PostgreSQL already uses port 5432, set `POSTGRES_PORT=5433` in `.env` (see Issues below).

### Row / relationship counts (parity)

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

### Q1 smoke test prerequisites

| Check | PostgreSQL | Neo4j |
|-------|------------|-------|
| Camp `SSD-DS-SS0101_0005` has connector to road | 1 | 1 |
| Hospital `SSD-HF-000055` has connector | 1 | 1 |
| Hospital in `logistical_hubs` / `LogisticalHub` | 1 | 1 |
| Routable Hospital/PHCC facilities | 419 | 419 |

PostGIS geometry spot-checks (`ST_IsValid`, 100 rows each on points/lines): all passed.

### Issues encountered and fixes

1. **macOS PostgreSQL port conflict** — local Postgres on `5432`; Docker PostGIS mapped to host `5433`. On a clean Windows 10 machine, use `5432`.
2. **`routing_edges.capacity` import** — float literals (`999999999.0`) failed `bigint` column; fixed with `execute_values` and explicit `int()` casting in `load_postgresql.py`.
3. **`execute_values` batch size** — `page_size=5000` intermittently failed; reduced to `1000`.
4. **Apple Silicon asymmetry** — Neo4j runs native `arm64`; PostGIS runs emulated `amd64`. Do **not** use macOS timings for thesis benchmarks; use Ryzen/Windows.

---

## Windows 10 + Ryzen 5 — full setup (Phase 1 → Phase 3)

Use this checklist after cloning the repository on your Ryzen PC. **No commit includes `data/` or `.env`** — you must generate data and config locally.

### Step 0 — Prerequisites

1. Install **Miniforge** (Windows x86_64): https://github.com/conda-forge/miniforge/releases  
2. Install **Docker Desktop**: https://www.docker.com/products/docker-desktop/  
   - Enable WSL 2 integration during setup  
   - Ensure Docker is running (`docker version` in PowerShell)  
3. Clone the repo:
   ```powershell
   git clone https://github.com/apxshay/DM_South_Sudan.git
   cd DM_South_Sudan
   ```

### Step 1 — Python environment + Phase 1 & 2 data pipeline

Open **Miniforge Prompt** or PowerShell with `conda` on PATH:

```powershell
.\scripts\setup.ps1
conda activate dm-south-sudan
.\scripts\bootstrap.ps1
```

This downloads ~600 MB of HDX data, builds the OSMnx road graph, runs Phase 2 merge/network integration, and writes all files under `data/processed/`.

**Resume options** (if raw data already downloaded):

```powershell
.\scripts\bootstrap.ps1 -SkipDownload
.\scripts\bootstrap.ps1 -From network
```

**Verify processed data exists** before Phase 3:

```powershell
dir data\processed\roads_hotosm\road_nodes.gpkg
dir data\processed\network\routing_edges.csv
```

Expected: `routing_edges.csv` has 66,533 data rows (+ header).

### Step 2 — Database configuration

```powershell
copy .env.example .env
```

Default `.env` targets `127.0.0.1:5432` (PostGIS) and `bolt://127.0.0.1:7687` (Neo4j). Edit only if ports conflict.

### Step 3 — Start Docker databases

```powershell
docker compose up -d
docker compose ps
```

Wait until both containers show **healthy** (Neo4j may take 1–2 minutes on first start while plugins download).

**Neo4j Browser:** http://localhost:7474 (user `neo4j`, password from `.env`)

### Step 4 — Populate databases

```powershell
conda activate dm-south-sudan
python scripts\populate_databases.py --reset
```

Expected runtime on Ryzen 5 / native amd64: **~5–15 minutes** (Neo4j MERGE import is the slowest step).

Load individually if needed:

```powershell
python scripts\load_postgresql.py --reset
python scripts\load_neo4j.py --reset
```

### Step 5 — Validate

**PostgreSQL** (all counts should match Expected column above):

```powershell
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM health_facilities;"
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM road_edges;"
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM routing_edges;"
```

**Neo4j:**

```powershell
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "MATCH (n:RoadNode) RETURN count(n);"
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "MATCH ()-[r:CONNECTOR_REVERSE]->() RETURN count(r);"
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "RETURN gds.version();"
```

**Confirm native amd64** (optional, on Ryzen):

```powershell
docker exec dm-south-sudan-neo4j uname -m
docker exec dm-south-sudan-postgis uname -m
```

Both should print `x86_64`.

### Step 6 — Troubleshooting (Windows)

| Problem | Solution |
|---------|----------|
| `conda not found` | Open Miniforge Prompt or add conda to PATH; run `.\scripts\setup.ps1` |
| `Docker daemon not running` | Start Docker Desktop; wait for whale icon to stabilize |
| `port is already allocated` | Change `POSTGRES_PORT` or `NEO4J_BOLT_PORT` in `.env`; `docker compose up -d` |
| `role "dm_ssd" does not exist` | Wrong Postgres instance (host port conflict). Check `.env` port matches `docker compose ps` |
| Neo4j connection reset on first load | Wait for container healthy; retry after ~2 min |
| `data/processed/... not found` | Run `.\scripts\bootstrap.ps1` first |
| WSL 2 not installed | `wsl --install` in admin PowerShell; reboot |

---

## macOS / Linux reproduction

```bash
conda activate dm-south-sudan
cp .env.example .env
# macOS only: if port 5432 is taken, set POSTGRES_PORT=5433 in .env
docker compose up -d
python scripts/populate_databases.py --reset
```

**Validation (PostgreSQL):**

```bash
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -f src/db/postgresql/load_data.sql
```

**Validation (Neo4j):**

```bash
docker exec -i dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev < src/db/neo4j/import.cypher
```

---

## Related documents

- [`AGENT_PHASE3.md`](../AGENT_PHASE3.md) — Phase 3 agent instructions
- [`README.md`](../README.md) — project quick start (Windows section)
- [`docs/phase2_relational_schema.md`](phase2_relational_schema.md)
- [`docs/phase2_graph_schema.md`](phase2_graph_schema.md)
- [`docs/phase5_benchmark_queries.md`](phase5_benchmark_queries.md)
