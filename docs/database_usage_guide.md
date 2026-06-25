# Using the Databases — Step-by-Step Guide

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Audience:** You, running PostgreSQL/PostGIS and Neo4j locally after Phase 3 setup

This guide explains **what to open**, **how to connect**, and **how to run queries** on both databases. For first-time installation (conda, bootstrap, populate), start with `[README.md](../README.md)`.

---

## 1. What you need running

Before querying, these should be active:


| What                                                               | Purpose                                          | How to check                             |
| ------------------------------------------------------------------ | ------------------------------------------------ | ---------------------------------------- |
| **Docker Desktop**                                                 | Runs PostGIS + Neo4j containers                  | Tray icon stable; `docker version` works |
| **Containers** `dm-south-sudan-postgis` and `dm-south-sudan-neo4j` | The two databases                                | `docker compose ps` → both **healthy**   |
| `**.env` file**                                                    | Connection settings (copied from `.env.example`) | File exists in project root              |
| **Miniforge / conda** (optional)                                   | Only needed to re-run loaders or Python scripts  | `conda activate dm-south-sudan`          |


You do **not** need conda open just to run SQL or Cypher — only Docker and a terminal (or a GUI client).

### Which terminal to use?


| Platform          | Recommended terminal                                         |
| ----------------- | ------------------------------------------------------------ |
| **Windows**       | **Miniforge Prompt** or PowerShell with PATH set (see below) |
| **macOS / Linux** | Regular terminal after `conda init`                          |


**Windows PATH** (if `docker` or `conda` not found in PowerShell):

```powershell
$env:Path = "$env:USERPROFILE\miniforge3\Scripts;C:\Program Files\Docker\Docker\resources\bin;" + $env:Path
cd C:\path\to\DM_South_Sudan-main
```

Always `cd` into the project folder before `docker compose` commands.

---

## 2. Daily startup (every work session)

### Step 1 — Start Docker Desktop

Launch **Docker Desktop** and wait until it reports running (whale icon idle, not “starting”).

### Step 2 — Start the database containers

From the project root:

```powershell
docker compose up -d
docker compose ps
```

```bash
docker compose up -d
docker compose ps
```

Wait until **both** services show `(healthy)`. Neo4j can take 1–2 minutes on first start (plugins download).

### Step 3 — Confirm data is loaded (quick check)

**PostgreSQL:**

```powershell
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM health_facilities;"
```

Expect **2251**.

**Neo4j:**

```powershell
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "MATCH (n:RoadNode) RETURN count(n);"
```

Expect **24779**.

If counts are zero or commands fail, re-run population (Section 8) or see `[phase3_database_population.md](phase3_database_population.md)`.

### Step 4 — Open your query tool

Choose one or more:


| Database       | Easiest option             | Alternative                                       |
| -------------- | -------------------------- | ------------------------------------------------- |
| **Neo4j**      | **Neo4j Browser** (web UI) | `cypher-shell` in terminal                        |
| **PostgreSQL** | `**psql` via docker exec** | pgAdmin, DBeaver, DataGrip, VS Code SQL extension |


---

## 3. Connection details

Defaults from `.env.example` (your `.env` may differ):


| Setting  | PostgreSQL                       | Neo4j                                |
| -------- | -------------------------------- | ------------------------------------ |
| Host     | `127.0.0.1`                      | `127.0.0.1`                          |
| Port     | **5432** (macOS: often **5433**) | HTTP **7474**, Bolt **7687**         |
| User     | `dm_ssd`                         | `neo4j`                              |
| Password | `dm_ssd_dev`                     | `dm_ssd_dev`                         |
| Database | `dm_south_sudan`                 | — (Neo4j uses default `neo4j` graph) |


**macOS:** if local Postgres already uses 5432, set `POSTGRES_PORT=5433` in `.env`, then `docker compose up -d` again. Connect GUI clients to port **5433**, not 5432.

**GUI client settings (PostgreSQL):**

- Type: PostgreSQL  
- Host: `127.0.0.1`  
- Port: from `.env` (`POSTGRES_PORT`)  
- Database: `dm_south_sudan`  
- User / password: `dm_ssd` / `dm_ssd_dev`

**GUI client settings (Neo4j):**

- URI: `bolt://127.0.0.1:7687`  
- User / password: `neo4j` / `dm_ssd_dev`

---

## 4. PostgreSQL / PostGIS

### Option A — Terminal (`psql` inside Docker) — recommended

**Open an interactive session:**

```powershell
docker exec -it dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan
```

```bash
docker exec -it dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan
```

You should see:

```text
dm_south_sudan=#
```

**Run one command without entering interactive mode:**

```powershell
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM road_edges;"
```

**Inside `psql` — useful meta-commands:**


| Command                | What it does     |
| ---------------------- | ---------------- |
| `\dt`                  | List tables      |
| `\d health_facilities` | Describe a table |
| `\dv`                  | List views       |
| `\q`                   | Quit             |


**Exit:** type `\q` or Ctrl+D.

### Option B — GUI (pgAdmin, DBeaver, etc.)

1. Install [DBeaver](https://dbeaver.io/) or [pgAdmin](https://www.pgadmin.org/) (or use VS Code PostgreSQL extension).
2. Create a new connection with the settings from Section 3.
3. Open SQL editor → run queries against `dm_south_sudan`.

PostGIS is enabled; geometry columns are on tables like `health_facilities`, `road_edges`, etc.

### Main tables (what to query)


| Table                                              | Rows (approx.) | Contents                                    |
| -------------------------------------------------- | -------------- | ------------------------------------------- |
| `health_facilities`                                | 2,251          | All facilities (with/without coordinates)   |
| `displacement_sites`                               | 77             | IOM DTM Round 11 camps                      |
| `road_nodes`                                       | 24,779         | Road graph nodes                            |
| `road_edges`                                       | 62,345         | Directed road segments                      |
| `poi_connectors`                                   | 2,094          | Camp/facility → road links                  |
| `routing_edges`                                    | 66,533         | Unified directed edges (roads + connectors) |
| `facility_road_access`                             | 2,017          | Facilities on the spatial graph             |
| `logistical_hubs`                                  | 5              | Referral hospitals                          |
| `admin_states` / `admin_counties` / `admin_payams` | 11 / 79 / 512  | Admin hierarchy                             |


View for aggregations: `v_state_humanitarian_stats`.

Schema details: `[phase2_relational_schema.md](phase2_relational_schema.md)`.

### Example PostgreSQL queries

**Row counts (sanity check):**

```sql
SELECT 'health_facilities' AS tbl, COUNT(*) FROM health_facilities
UNION ALL SELECT 'road_edges', COUNT(*) FROM road_edges
UNION ALL SELECT 'routing_edges', COUNT(*) FROM routing_edges;
```

**List hospitals:**

```sql
SELECT facility_id, name, state_code, latitude, longitude
FROM health_facilities
WHERE facility_type = 'Hospital'
ORDER BY name
LIMIT 10;
```

**Camps in Central Equatoria:**

```sql
SELECT site_id, site_name, idp_individuals
FROM displacement_sites
WHERE state_code = 'SS01'
ORDER BY idp_individuals DESC;
```

**PostGIS — check extension and sample geometry:**

```sql
SELECT PostGIS_Version();
SELECT facility_id, facility_name, ST_AsText(geom) AS wkt
FROM health_facilities
WHERE geom IS NOT NULL
LIMIT 3;
```

**Q4-style aggregation (relational showcase):**

```sql
SELECT * FROM v_state_humanitarian_stats
ORDER BY total_idp_individuals DESC
LIMIT 5;
```

**Q1 smoke test — camp has a connector:**

```sql
SELECT ds.site_id, ds.site_name, pc.road_node_id, pc.length_m
FROM displacement_sites ds
JOIN poi_connectors pc ON pc.poi_node_id = ds.site_id
WHERE ds.site_id = 'SSD-DS-SS0101_0005';
```

Full benchmark SQL templates: `[phase5_benchmark_queries.md](phase5_benchmark_queries.md)`.

**Run validation script from file:**

```powershell
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -f src/db/postgresql/load_data.sql
```

(On Windows, path is inside the container mount only if you exec from host with `-f` — the file must be reachable. Easier: copy/paste queries from `src/db/postgresql/load_data.sql`, or use the `-c` one-liners above.)

---

## 5. Neo4j

### Option A — Neo4j Browser (easiest)

1. Ensure containers are running (`docker compose ps`).
2. Open a browser: **[http://localhost:7474](http://localhost:7474)**
3. Connect:
  - URL: `bolt://localhost:7687` (or pre-filled)
  - Username: `neo4j`
  - Password: `dm_ssd_dev`
4. You get a prompt at the top — type Cypher and press **Run** (or Ctrl+Enter).

Neo4j Browser shows graph visualizations for queries that return nodes/relationships.

### Option B — Terminal (`cypher-shell`)

**One query:**

```powershell
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "MATCH (n:RoadNode) RETURN count(n);"
```

**Interactive session:**

```powershell
docker exec -it dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev
```

Then type Cypher (end statements with `;`). Exit with `:exit` or Ctrl+D.

### Main graph elements


| Label / type        | Count (approx.) | Meaning                           |
| ------------------- | --------------- | --------------------------------- |
| `:RoadNode`         | 24,779          | Intersections / dead-ends         |
| `:HealthFacility`   | 2,017           | Georeferenced facilities          |
| `:DisplacementSite` | 77              | Camps                             |
| `:LogisticalHub`    | 5               | Extra label on referral hospitals |
| `ROAD_SEGMENT`      | 62,345          | Directed road arcs                |
| `CONNECTOR`         | 2,094           | POI → road (outbound)             |
| `CONNECTOR_REVERSE` | 2,094           | Road → POI (for max-flow Q5)      |


Schema details: `[phase2_graph_schema.md](phase2_graph_schema.md)`.

### Example Cypher queries

**Counts:**

```cypher
MATCH (n:RoadNode) RETURN count(n) AS road_nodes;
MATCH ()-[r:ROAD_SEGMENT]->() RETURN count(r) AS road_segments;
MATCH (h:HealthFacility) RETURN count(h) AS facilities;
MATCH (d:DisplacementSite) RETURN count(d) AS camps;
```

**Check GDS plugin (needed for Q5):**

```cypher
RETURN gds.version();
```

**Browse one camp and its connector:**

```cypher
MATCH (c:DisplacementSite {poi_node_id: 'SSD-DS-SS0101_0005'})
      -[conn:CONNECTOR]->(rn:RoadNode)
RETURN c, conn, rn;
```

Click the graph view in Neo4j Browser to see the visualization.

**List logistical hubs:**

```cypher
MATCH (h:HealthFacility:LogisticalHub)
RETURN h.facility_id, h.name, h.state_code;
```

**Q1 — nearest Hospital/PHCC from Don Bosco camp:**

```cypher
MATCH (c:DisplacementSite {poi_node_id: 'SSD-DS-SS0101_0005'})-[cOut:CONNECTOR]->(start:RoadNode)
MATCH (hf:HealthFacility)
WHERE hf.facility_type IN ['Hospital', 'PHCC']
MATCH (hf)-[hOut:CONNECTOR]->(end:RoadNode)
MATCH p = shortestPath((start)-[:ROAD_SEGMENT*]->(end))
WITH c, hf, cOut, hOut, p,
     cOut.length_m + reduce(d = 0, r IN relationships(p) | d + r.length_m) + hOut.length_m AS total_m
RETURN c.name AS camp,
       hf.name AS facility,
       hf.facility_type AS type,
       total_m AS distance_m,
       length(p) AS road_hops
ORDER BY total_m
LIMIT 1;
```

More templates (Q2–Q5): `[phase5_benchmark_queries.md](phase5_benchmark_queries.md)`. Reference file: `src/db/neo4j/import.cypher`.

---

## 6. Side-by-side: same question on both databases

**Question:** How many road graph nodes do we have?


| PostgreSQL                         | Neo4j                                 |
| ---------------------------------- | ------------------------------------- |
| `SELECT COUNT(*) FROM road_nodes;` | `MATCH (n:RoadNode) RETURN count(n);` |


**Question:** Does Juba Teaching Hospital exist as a hub?


| PostgreSQL                                                           | Neo4j                                                                             |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `SELECT * FROM logistical_hubs WHERE facility_id = 'SSD-HF-000055';` | `MATCH (h:HealthFacility:LogisticalHub {facility_id: 'SSD-HF-000055'}) RETURN h;` |


**Question:** Shortest path routing from a camp


| PostgreSQL                                                   | Neo4j                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------ |
| Recursive CTE on `road_edges` + connectors (see Phase 5 doc) | `shortestPath` on `ROAD_SEGMENT` (see Section 5 above) |


---

## 7. Using Python (conda) with the databases

Open **Miniforge Prompt** (Windows) or terminal with conda:

```powershell
conda activate dm-south-sudan
cd C:\path\to\DM_South_Sudan-main
```

```bash
conda activate dm-south-sudan
cd /path/to/DM_South_Sudan-main
```

Connection settings are read from `.env` via `src/db/db_config.py`.

**Re-load both databases from processed files:**

```powershell
python scripts\populate_databases.py --reset
```

```bash
python scripts/populate_databases.py --reset
```

**Load one database only:**


| PostgreSQL                                  | Neo4j                                  |
| ------------------------------------------- | -------------------------------------- |
| `python scripts/load_postgresql.py --reset` | `python scripts/load_neo4j.py --reset` |


Requires Docker containers **running** and `data/processed/` populated (see `[README.md](../README.md)` Step 2).

---

## 8. Stop, restart, and reset

### Stop containers (keep data)

```powershell
docker compose stop
```

Data persists in Docker volumes `dm_postgis_data` and `dm_neo4j_data`.

### Start again

```powershell
docker compose start
# or
docker compose up -d
```

### Stop and remove containers (data volumes kept)

```powershell
docker compose down
```

### Full wipe (delete all DB data — destructive)

```powershell
docker compose down -v
docker compose up -d
python scripts\populate_databases.py --reset
```

Use `-v` only when you intentionally want empty databases.

---

## 9. Troubleshooting


| Symptom                           | Likely cause                                                | Fix                                                                |
| --------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------ |
| `docker: command not found`       | Docker not on PATH                                          | Start Docker Desktop; add `Docker\resources\bin` to PATH (Windows) |
| `Cannot connect to Docker daemon` | Docker Desktop not running                                  | Launch Docker Desktop                                              |
| `connection refused` on 5432      | Wrong port or container down                                | `docker compose ps`; check `POSTGRES_PORT` in `.env`               |
| `role "dm_ssd" does not exist`    | Connecting to **wrong** Postgres (host install, not Docker) | Use port from `docker compose ps` mapping                          |
| Neo4j auth failed                 | Wrong password                                              | Use password from `.env` (default `dm_ssd_dev`)                    |
| Neo4j Browser blank / not ready   | Container still starting                                    | Wait for `healthy`; retry after 2 min                              |
| Counts are 0                      | DB never populated                                          | `python scripts/populate_databases.py --reset`                     |
| `conda not found`                 | Conda not on PATH                                           | Use Miniforge Prompt                                               |


Platform-specific notes: `[phase3_database_population.md](phase3_database_population.md)`.

---

## 10. Quick reference card

```text
PROJECT ROOT:  DM_South_Sudan-main/
START:         Docker Desktop → docker compose up -d
CHECK:         docker compose ps  (both healthy)

POSTGRESQL
  Shell:       docker exec -it dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan
  One-liner:   docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT 1;"
  GUI:         DBeaver / pgAdmin → 127.0.0.1:5432 (or 5433 on macOS)

NEO4J
  Browser:     http://localhost:7474  (neo4j / dm_ssd_dev)
  Shell:       docker exec -it dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev
  Bolt URI:    bolt://127.0.0.1:7687

RELOAD DATA:   conda activate dm-south-sudan → python scripts/populate_databases.py --reset
STOP:          docker compose stop
```

---

## Related documents

- `[README.md](../README.md)` — full install pipeline (Windows + macOS)
- `[phase3_database_population.md](phase3_database_population.md)` — expected counts and validation
- `[phase5_benchmark_queries.md](phase5_benchmark_queries.md)` — Q1–Q5 query templates
- `[phase2_relational_schema.md](phase2_relational_schema.md)` — PostgreSQL tables
- `[phase2_graph_schema.md](phase2_graph_schema.md)` — Neo4j labels and relationships

