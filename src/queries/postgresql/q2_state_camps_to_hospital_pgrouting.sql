-- Q2 — All camps in one state → one referral hospital (pgRouting Dijkstra)
--
-- Path cost (meters):
--   total_m = camp_connector + road_path_cost + hospital_connector
--
-- Primary PostgreSQL track for Phase 5 routing benchmarks.
--
-- Usage:
--   Get-Content src/queries/postgresql/q2_state_camps_to_hospital_pgrouting.sql |
--     docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan \
--       -v state_code=SS01 -v target_hospital_id=SSD-HF-000055

WITH
camps AS (
    SELECT
        ds.site_id,
        ds.site_name,
        pc.road_node_id AS start_road_node_id,
        pc.length_m     AS camp_connector_m
    FROM displacement_sites ds
    JOIN poi_connectors pc ON pc.poi_node_id = ds.site_id
    WHERE ds.state_code = :'state_code'
),
hospital AS (
    SELECT
        hf.facility_id AS hospital_id,
        fra.road_node_id AS end_road_node_id,
        fra.connector_length_m AS hospital_connector_m
    FROM health_facilities hf
    JOIN facility_road_access fra ON fra.facility_id = hf.facility_id
    WHERE hf.facility_id = :'target_hospital_id'
),
paths AS (
    SELECT
        c.site_id AS camp_id,
        c.site_name AS camp_name,
        h.hospital_id,
        c.camp_connector_m + dc.agg_cost + h.hospital_connector_m AS total_m,
        dc.agg_cost AS road_cost_m
    FROM camps c
    CROSS JOIN hospital h
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
        h.end_road_node_id,
        directed := true
    ) AS dc
)
SELECT
    camp_id,
    camp_name,
    hospital_id,
    total_m,
    road_cost_m,
    NULL::integer AS road_hops
FROM paths
ORDER BY total_m, camp_id;
