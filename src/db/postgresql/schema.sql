-- South Sudan humanitarian spatial graph — PostgreSQL / PostGIS schema
-- Phase 2 deliverable for Phase 3 population and Phase 5 benchmarking.
-- Source: docs/phase2_relational_schema.md

CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------------------------------------------------------------------------
-- Admin dimensions (SS 2023 Admin_data)
-- ---------------------------------------------------------------------------

CREATE TABLE admin_states (
    state_code   TEXT PRIMARY KEY,
    state_name   TEXT NOT NULL
);

CREATE TABLE admin_counties (
    county_code  TEXT PRIMARY KEY,
    state_code   TEXT NOT NULL REFERENCES admin_states (state_code),
    county_name  TEXT NOT NULL
);

CREATE TABLE admin_payams (
    payam_code   TEXT PRIMARY KEY,
    county_code  TEXT NOT NULL REFERENCES admin_counties (county_code),
    state_code   TEXT NOT NULL REFERENCES admin_states (state_code),
    payam_name   TEXT NOT NULL
);

CREATE INDEX idx_admin_counties_state ON admin_counties (state_code);
CREATE INDEX idx_admin_payams_state ON admin_payams (state_code);
CREATE INDEX idx_admin_payams_county ON admin_payams (county_code);

-- ---------------------------------------------------------------------------
-- Reference: logistical hubs (curated referral hospitals for Q3)
-- ---------------------------------------------------------------------------

CREATE TABLE logistical_hubs (
    hub_id              TEXT PRIMARY KEY,
    facility_id         TEXT NOT NULL,
    hub_name            TEXT NOT NULL,
    state_code          TEXT REFERENCES admin_states (state_code),
    role                TEXT,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    facility_type       TEXT,
    admission_capacity  INTEGER,
    geom                GEOMETRY(POINT, 4326)
);

CREATE INDEX idx_logistical_hubs_facility ON logistical_hubs (facility_id);
CREATE INDEX idx_logistical_hubs_geom ON logistical_hubs USING GIST (geom);

-- ---------------------------------------------------------------------------
-- Health facilities (all 2,251 rows; graph routing uses subset with coords)
-- ---------------------------------------------------------------------------

CREATE TABLE health_facilities (
    facility_id           TEXT PRIMARY KEY,
    facility_name         TEXT NOT NULL,
    facility_type         TEXT NOT NULL,
    state_code            TEXT REFERENCES admin_states (state_code),
    state_name            TEXT,
    county_code           TEXT,
    payam_code            TEXT,
    latitude              DOUBLE PRECISION,
    longitude             DOUBLE PRECISION,
    has_coordinates       BOOLEAN NOT NULL DEFAULT FALSE,
    admission_capacity    INTEGER,
    source                TEXT,
    merge_status          TEXT,
    who_site_name         TEXT,
    ss_facilities_code    TEXT,
    geom                  GEOMETRY(POINT, 4326)
);

CREATE INDEX idx_health_facilities_type ON health_facilities (facility_type);
CREATE INDEX idx_health_facilities_state ON health_facilities (state_code);
CREATE INDEX idx_health_facilities_coords ON health_facilities (has_coordinates);
CREATE INDEX idx_health_facilities_geom ON health_facilities USING GIST (geom);

-- ---------------------------------------------------------------------------
-- Displacement sites (IOM DTM Round 11)
-- ---------------------------------------------------------------------------

CREATE TABLE displacement_sites (
    site_id               TEXT PRIMARY KEY,
    source_ssid           TEXT NOT NULL UNIQUE,
    site_name             TEXT NOT NULL,
    state_code            TEXT REFERENCES admin_states (state_code),
    state_name            TEXT,
    county_code           TEXT,
    payam_code            TEXT,
    payam_name            TEXT,
    latitude              DOUBLE PRECISION NOT NULL,
    longitude             DOUBLE PRECISION NOT NULL,
    idp_individuals       INTEGER NOT NULL,
    idp_households        INTEGER,
    settlement_type       TEXT,
    accessibility         TEXT,
    nearest_road_node_id  BIGINT,
    snap_distance_m       DOUBLE PRECISION,
    geom                  GEOMETRY(POINT, 4326)
);

CREATE INDEX idx_displacement_sites_state ON displacement_sites (state_code);
CREATE INDEX idx_displacement_sites_road_node ON displacement_sites (nearest_road_node_id);
CREATE INDEX idx_displacement_sites_geom ON displacement_sites USING GIST (geom);

-- ---------------------------------------------------------------------------
-- Road network graph (OSMnx processed)
-- ---------------------------------------------------------------------------

CREATE TABLE road_nodes (
    node_id   BIGINT PRIMARY KEY,
    lon       DOUBLE PRECISION NOT NULL,
    lat       DOUBLE PRECISION NOT NULL,
    degree    INTEGER NOT NULL,
    geom      GEOMETRY(POINT, 4326) NOT NULL
);

CREATE INDEX idx_road_nodes_geom ON road_nodes USING GIST (geom);

CREATE TABLE road_edges (
    edge_id         BIGINT PRIMARY KEY,
    start_node_id   BIGINT NOT NULL REFERENCES road_nodes (node_id),
    end_node_id     BIGINT NOT NULL REFERENCES road_nodes (node_id),
    length_m        DOUBLE PRECISION NOT NULL,
    highway         TEXT,
    oneway          BOOLEAN,
    reversed        TEXT,
    capacity        BIGINT DEFAULT 999999999,
    osm_id          TEXT,
    name            TEXT,
    geom            GEOMETRY(LINESTRING, 4326) NOT NULL
);

CREATE INDEX idx_road_edges_start ON road_edges (start_node_id);
CREATE INDEX idx_road_edges_end ON road_edges (end_node_id);
CREATE INDEX idx_road_edges_highway ON road_edges (highway);
CREATE INDEX idx_road_edges_geom ON road_edges USING GIST (geom);

-- ---------------------------------------------------------------------------
-- POI connectors (camp/facility → road node)
-- ---------------------------------------------------------------------------

CREATE TABLE poi_connectors (
    edge_id         BIGINT PRIMARY KEY,
    poi_node_id     TEXT NOT NULL,
    poi_type        TEXT NOT NULL CHECK (poi_type IN ('health_facility', 'displacement_site')),
    road_node_id    BIGINT NOT NULL REFERENCES road_nodes (node_id),
    length_m        DOUBLE PRECISION NOT NULL,
    capacity        INTEGER,
    geom            GEOMETRY(LINESTRING, 4326) NOT NULL
);

CREATE INDEX idx_poi_connectors_poi ON poi_connectors (poi_node_id);
CREATE INDEX idx_poi_connectors_road ON poi_connectors (road_node_id);

-- ---------------------------------------------------------------------------
-- Denormalized routing layer (unified directed edges for Q1–Q3 CTEs, Q5 flow)
-- ---------------------------------------------------------------------------

CREATE TABLE routing_edges (
    edge_id           BIGINT PRIMARY KEY,
    edge_type         TEXT NOT NULL CHECK (
        edge_type IN ('road_segment', 'connector', 'connector_reverse')
    ),
    start_node_kind   TEXT NOT NULL CHECK (start_node_kind IN ('road', 'poi')),
    start_node_id     TEXT NOT NULL,
    end_node_kind     TEXT NOT NULL CHECK (end_node_kind IN ('road', 'poi')),
    end_node_id       TEXT NOT NULL,
    length_m          DOUBLE PRECISION NOT NULL,
    capacity          BIGINT,
    highway           TEXT,
    oneway            BOOLEAN,
    poi_type          TEXT,
    poi_node_id       TEXT
);

CREATE INDEX idx_routing_edges_start ON routing_edges (start_node_kind, start_node_id);
CREATE INDEX idx_routing_edges_end ON routing_edges (end_node_kind, end_node_id);
CREATE INDEX idx_routing_edges_type ON routing_edges (edge_type);

-- Facility → road access lookup (Q1 target matching)
CREATE TABLE facility_road_access (
    facility_id          TEXT PRIMARY KEY REFERENCES health_facilities (facility_id),
    poi_node_id          TEXT NOT NULL,
    road_node_id         BIGINT NOT NULL REFERENCES road_nodes (node_id),
    connector_length_m   DOUBLE PRECISION NOT NULL,
    facility_type        TEXT
);

CREATE INDEX idx_facility_road_access_node ON facility_road_access (road_node_id);
CREATE INDEX idx_facility_road_access_type ON facility_road_access (facility_type);

-- ---------------------------------------------------------------------------
-- Optional view: per-state humanitarian stats helper (Q4 building block)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_state_humanitarian_stats AS
SELECT
    s.state_code,
    s.state_name,
    COUNT(DISTINCT ds.site_id) AS displacement_site_count,
    COALESCE(SUM(ds.idp_individuals), 0) AS idp_individuals_total,
    COUNT(DISTINCT hf.facility_id) FILTER (
        WHERE hf.has_coordinates
          AND hf.facility_type IN ('Hospital', 'PHCC')
    ) AS hospital_phcc_count
FROM admin_states s
LEFT JOIN displacement_sites ds ON ds.state_code = s.state_code
LEFT JOIN health_facilities hf ON hf.state_code = s.state_code
GROUP BY s.state_code, s.state_name
ORDER BY s.state_code;
