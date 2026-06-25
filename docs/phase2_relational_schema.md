# Phase 2 — Relational Schema (PostgreSQL / PostGIS)

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Date:** 2026-06-24  
**Status:** Complete — loaded in Phase 3

Executable DDL: [`src/db/postgresql/schema.sql`](../src/db/postgresql/schema.sql)  
**Apply and load:** [`README.md`](../README.md) Steps 4–5, or `scripts/load_postgresql.py --reset`

---

## 1. Purpose

This schema models the same humanitarian spatial domain as the Neo4j graph: admin hierarchy, health facilities, displacement sites, road network topology, POI connectors, and a unified routing edge layer for benchmark queries Q1–Q5.

---

## 2. Entity-relationship overview

```mermaid
erDiagram
    admin_states ||--o{ admin_counties : contains
    admin_counties ||--o{ admin_payams : contains
    admin_states ||--o{ health_facilities : locates
    admin_states ||--o{ displacement_sites : locates
    admin_states ||--o{ logistical_hubs : locates

    health_facilities ||--o| facility_road_access : has_access
    health_facilities ||--o| logistical_hubs : hub_facility
    road_nodes ||--o{ facility_road_access : serves
    road_nodes ||--o{ road_edges : starts
    road_nodes ||--o{ road_edges : ends
    road_nodes ||--o{ poi_connectors : connects
    road_nodes ||--o{ displacement_sites : nearest_snap

    admin_states {
        text state_code PK
        text state_name
    }

    admin_counties {
        text county_code PK
        text state_code FK
        text county_name
    }

    admin_payams {
        text payam_code PK
        text county_code FK
        text state_code FK
        text payam_name
    }

    logistical_hubs {
        text hub_id PK
        text facility_id
        text hub_name
        text state_code FK
        text role
        int admission_capacity
        geometry geom
    }

    health_facilities {
        text facility_id PK
        text facility_name
        text facility_type
        text state_code FK
        text county_code
        text payam_code
        float latitude
        float longitude
        bool has_coordinates
        int admission_capacity
        geometry geom
    }

    displacement_sites {
        text site_id PK
        text source_ssid UK
        text site_name
        text state_code FK
        int idp_individuals
        int idp_households
        bigint nearest_road_node_id
        float snap_distance_m
        geometry geom
    }

    road_nodes {
        bigint node_id PK
        float lon
        float lat
        int degree
        geometry geom
    }

    road_edges {
        bigint edge_id PK
        bigint start_node_id FK
        bigint end_node_id FK
        float length_m
        text highway
        bool oneway
        bigint capacity
        geometry geom
    }

    poi_connectors {
        bigint edge_id PK
        text poi_node_id
        text poi_type
        bigint road_node_id FK
        float length_m
        int capacity
        geometry geom
    }

    facility_road_access {
        text facility_id PK_FK
        text poi_node_id
        bigint road_node_id FK
        float connector_length_m
        text facility_type
    }

    routing_edges {
        bigint edge_id PK
        text edge_type
        text start_node_kind
        text start_node_id
        text end_node_kind
        text end_node_id
        float length_m
        bigint capacity
        text highway
    }
```

**Notes:**

- `routing_edges` is a **denormalized import/routing table** (no FK to `road_nodes` — POI IDs are text).
- `poi_connectors.poi_node_id` references `health_facilities.facility_id` or `displacement_sites.site_id` by convention (polymorphic).
- `logistical_hubs.facility_id` references `health_facilities.facility_id` logically (not enforced as FK in DDL).
- `v_state_humanitarian_stats` is a view over `admin_states`, `displacement_sites`, and `health_facilities` (Q4).

---

## 2.1 Full table definitions

See [`src/db/postgresql/schema.sql`](../src/db/postgresql/schema.sql) for executable DDL. Summary of all tables:

| Table | Primary key | Main foreign keys |
|-------|-------------|-------------------|
| `admin_states` | `state_code` | — |
| `admin_counties` | `county_code` | `state_code` → `admin_states` |
| `admin_payams` | `payam_code` | `county_code`, `state_code` |
| `logistical_hubs` | `hub_id` | `state_code` → `admin_states`; `facility_id` → `health_facilities` (logical) |
| `health_facilities` | `facility_id` | `state_code` → `admin_states` |
| `displacement_sites` | `site_id` | `state_code` → `admin_states` |
| `road_nodes` | `node_id` | — |
| `road_edges` | `edge_id` | `start_node_id`, `end_node_id` → `road_nodes` |
| `poi_connectors` | `edge_id` | `road_node_id` → `road_nodes` |
| `routing_edges` | `edge_id` | — (unified edge list for CTEs) |
| `facility_road_access` | `facility_id` | `facility_id` → `health_facilities`; `road_node_id` → `road_nodes` |

---

## 3. Table summary

| Table | Rows (expected) | Source file |
|-------|-----------------|-------------|
| `admin_states` | 11 | `data/processed/admin/admin_states.csv` |
| `admin_counties` | 79 | `data/processed/admin/admin_counties.csv` |
| `admin_payams` | 512 | `data/processed/admin/admin_payams.csv` |
| `logistical_hubs` | 5 | `data/processed/reference/logistical_hubs.csv` |
| `health_facilities` | 2,251 | `data/processed/health_facilities/health_facilities_with_capacity.csv` |
| `displacement_sites` | 77 | `data/processed/displacement_sites/displacement_sites_canonical.csv` + snap fields from `poi_nodes` |
| `road_nodes` | 24,779 | `data/processed/roads_hotosm/road_nodes.gpkg` |
| `road_edges` | 62,345 | `data/processed/roads_hotosm/road_edges.gpkg` |
| `poi_connectors` | 2,094 | `data/processed/network/connector_edges.gpkg` |
| `routing_edges` | 66,533 | `data/processed/network/routing_edges.csv` |
| `facility_road_access` | 2,017 | `data/processed/network/facility_road_access.csv` |

---

## 4. Design decisions

### 4.1 Typed node IDs in `routing_edges`

Road OSM node IDs are `BIGINT`; POI IDs are text (`SSD-HF-*`, `SSD-DS-*`). The unified `routing_edges` table stores all IDs as `TEXT` with `start_node_kind` / `end_node_kind` (`road` | `poi`) to avoid casting collisions and support recursive CTEs across both layers.

### 4.2 Directed road network

`road_edges` preserves OSMnx direction (`start_node_id` → `end_node_id`, `oneway`, `reversed`). ~97% of road links are two-way (opposing arc pairs); ~360 are one-way only. See `docs/road_network_topology.md` §3.3.

### 4.3 Capacity model (Q5)

| Edge type | `capacity` | Notes |
|-----------|------------|-------|
| `road_segment` | `999999999` | Unlimited for benchmark |
| `connector` (POI → road) | camp: `idp_individuals`; hospital: `admission_capacity` | Outbound from POI |
| `connector_reverse` (road → POI) | Same as outbound | Enables max-flow into hospitals |

Benchmark Q5 may override scenario values (`evacuees=200`, `hospital_free_slots=250`) at query time.

### 4.4 Admission capacity defaults

Synthetic defaults on `health_facilities.admission_capacity`:

| `facility_type` | Default capacity |
|-----------------|------------------|
| Hospital | 250 |
| PHCC | 100 |
| PHCU | 50 |
| unknown | NULL |

### 4.5 Facilities without coordinates

All 2,251 facilities are stored in `health_facilities`. Only 2,017 with `has_coordinates=true` appear in `facility_road_access` and the spatial graph.

---

## 5. Index strategy (query mapping)

| Query | Tables / indexes used |
|-------|----------------------|
| **Q1** Nearest hospital | `routing_edges` (recursive CTE), `facility_road_access`, `health_facilities` |
| **Q2** Multi-camp → hospital | `displacement_sites (state_code)`, `routing_edges` |
| **Q3** Reachability ≤ 50 km | `logistical_hubs`, `routing_edges`, `displacement_sites` |
| **Q4** State aggregations | `v_state_humanitarian_stats`, `road_edges (highway)` |
| **Q5** Max flow | `routing_edges` (application-layer NetworkX; not native SQL) |

**PostGIS:** GIST indexes on all `geom` columns. B-tree on `state_code`, `facility_type`, routing edge endpoints.

---

## 6. Import notes (Phase 3)

Phase 3 loaders (2026-06-25): `scripts/load_postgresql.py` applies `schema.sql` and loads all tables in FK order.

1. Run `schema.sql` to create tables (or `python scripts/load_postgresql.py --reset`).
2. Load CSV/GPKG files in FK order: admin → facilities/sites → road_nodes → road_edges → connectors → routing_edges.
3. Populate `geom` from `latitude`/`longitude` or source geometries during import.
4. Join `displacement_sites.nearest_road_node_id` and `snap_distance_m` from `poi_nodes` on `site_id = poi_node_id`.

**Load:** follow [`README.md`](../README.md) Steps 3–5.

| Windows | macOS / Linux |
|---------|---------------|
| `docker compose up -d` | same |
| `python scripts\populate_databases.py --reset` | `python scripts/populate_databases.py --reset` |

Validation counts: [`phase3_database_population.md`](phase3_database_population.md).

---

## 7. Known limitations

1. **Q4 road km by state** — road edges lack admin polygons; compute national primary+secondary km only.
2. **666 long POI snaps** — see `poi_snap_review.csv`; distances may be inflated in remote areas.
3. **651 `unknown` facility types** — excluded from Q1/Q2 routing unless reclassified.
4. **Q5 max flow** — not expressible efficiently in pure SQL; use application-layer solver on `routing_edges`.

---

## 8. Related documents

- [`docs/phase2_graph_schema.md`](phase2_graph_schema.md) — Neo4j equivalent model
- [`docs/phase5_benchmark_queries.md`](phase5_benchmark_queries.md) — canonical query templates
- [`docs/phase2_data_modeling.md`](phase2_data_modeling.md) — Phase 2 progress log
- [`README.md`](../README.md) — main setup guide (Windows + macOS)
- [`docs/phase3_database_population.md`](phase3_database_population.md) — validation counts and platform notes
