-- Q3 — Camps reachable within max road distance of a logistical hub (pgRouting)
--
-- Returns two result sets:
--   1) reachable camps (total_m <= max_distance_m)
--   2) isolated camps (not reachable within threshold)
--
-- total_m = hub_connector + road_cost + camp_connector
--
-- Usage:
--   Get-Content src/queries/postgresql/q3_hub_reachability_pgrouting.sql |
--     docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan \
--       -v hub_id=HUB-001 -v max_distance_m=50000

WITH
hub AS (
    SELECT
        lh.hub_id,
        hf.facility_id,
        pc.road_node_id AS hub_road_node_id,
        pc.length_m     AS hub_connector_m
    FROM logistical_hubs lh
    JOIN health_facilities hf ON hf.facility_id = lh.facility_id
    JOIN poi_connectors pc ON pc.poi_node_id = hf.facility_id
    WHERE lh.hub_id = :'hub_id'
),
camp_nodes AS (
    SELECT
        ds.site_id,
        ds.site_name,
        ds.state_code,
        pc.road_node_id AS camp_road_node_id,
        pc.length_m     AS camp_connector_m
    FROM displacement_sites ds
    JOIN poi_connectors pc ON pc.poi_node_id = ds.site_id
),
camp_targets AS (
    SELECT ARRAY_AGG(DISTINCT camp_road_node_id ORDER BY camp_road_node_id) AS node_ids
    FROM camp_nodes
),
road_costs AS (
    SELECT
        dc.end_vid AS camp_road_node_id,
        dc.agg_cost AS road_cost_m
    FROM hub h
    CROSS JOIN camp_targets ct
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
        h.hub_road_node_id,
        ct.node_ids,
        directed := true
    ) AS dc
),
camp_distances AS (
    SELECT
        cn.site_id AS camp_id,
        cn.site_name AS camp_name,
        cn.state_code,
        h.hub_connector_m + rc.road_cost_m + cn.camp_connector_m AS total_m,
        rc.road_cost_m
    FROM camp_nodes cn
    JOIN road_costs rc ON rc.camp_road_node_id = cn.camp_road_node_id
    CROSS JOIN hub h
),
reachable AS (
    SELECT camp_id, camp_name, state_code, total_m, road_cost_m
    FROM camp_distances
    WHERE total_m <= :max_distance_m
    ORDER BY total_m, camp_id
),
isolated AS (
    SELECT cn.site_id AS camp_id, cn.site_name AS camp_name, cn.state_code
    FROM camp_nodes cn
    LEFT JOIN reachable r ON r.camp_id = cn.site_id
    WHERE r.camp_id IS NULL
    ORDER BY cn.site_id
)
SELECT 'reachable' AS result_set, camp_id, camp_name, state_code, total_m, road_cost_m::text AS extra
FROM reachable
UNION ALL
SELECT 'isolated' AS result_set, camp_id, camp_name, state_code, NULL::double precision, NULL::text
FROM isolated
ORDER BY result_set DESC, total_m NULLS LAST, camp_id;
