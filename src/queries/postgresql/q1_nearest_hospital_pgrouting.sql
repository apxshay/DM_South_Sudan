-- Q1 — Nearest Hospital/PHCC from one displacement site (pgRouting Dijkstra)
--
-- Path cost (meters):
--   total_m = camp_connector + road_path_cost + hospital_connector
--
-- Uses pgr_dijkstraCost on directed road_edges (length_m weights).
-- Primary PostgreSQL track for Phase 5 routing benchmarks (fair vs Neo4j GDS).
--
-- Usage (pipe into container — project dir is not mounted in Docker):
--   Get-Content src/queries/postgresql/q1_nearest_hospital_pgrouting.sql |
--     docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan \
--       -v camp_id=SSD-DS-SS0101_0005

WITH
camp AS (
    SELECT
        ds.site_id,
        ds.site_name,
        pc.road_node_id AS start_road_node_id,
        pc.length_m     AS camp_connector_m
    FROM displacement_sites ds
    JOIN poi_connectors pc ON pc.poi_node_id = ds.site_id
    WHERE ds.site_id = :'camp_id'
),
targets AS (
    SELECT
        fra.road_node_id,
        fra.facility_id,
        fra.connector_length_m AS hospital_connector_m,
        hf.facility_name,
        hf.facility_type
    FROM facility_road_access fra
    JOIN health_facilities hf ON hf.facility_id = fra.facility_id
    WHERE hf.facility_type IN ('Hospital', 'PHCC')
),
target_nodes AS (
    SELECT ARRAY_AGG(DISTINCT road_node_id ORDER BY road_node_id) AS node_ids
    FROM targets
),
road_costs AS (
    SELECT
        dc.end_vid AS road_node_id,
        dc.agg_cost AS road_cost_m
    FROM camp c
    CROSS JOIN target_nodes tn
    CROSS JOIN LATERAL pgr_dijkstraCost(
        $$
        SELECT
            edge_id AS id,
            start_node_id AS source,
            end_node_id AS target,
            length_m AS cost,
            CASE WHEN oneway IS TRUE THEN -1 ELSE length_m END AS reverse_cost
        FROM road_edges
        $$,
        c.start_road_node_id,
        tn.node_ids,
        directed := true
    ) AS dc
),
ranked AS (
    SELECT
        t.facility_id,
        t.facility_name,
        t.facility_type,
        c.camp_connector_m,
        rc.road_cost_m,
        t.hospital_connector_m,
        c.camp_connector_m + rc.road_cost_m + t.hospital_connector_m AS total_m,
        ROW_NUMBER() OVER (
            PARTITION BY t.facility_id
            ORDER BY c.camp_connector_m + rc.road_cost_m + t.hospital_connector_m
        ) AS rn
    FROM camp c
    CROSS JOIN targets t
    JOIN road_costs rc ON rc.road_node_id = t.road_node_id
)
SELECT
    camp.site_id   AS camp_id,
    camp.site_name AS camp_name,
    r.facility_id,
    r.facility_name,
    r.facility_type,
    r.camp_connector_m,
    r.road_cost_m,
    r.hospital_connector_m,
    r.total_m,
    NULL::integer AS road_hops
FROM ranked r
CROSS JOIN camp
WHERE r.rn = 1
ORDER BY r.total_m, r.facility_id
LIMIT 1;
