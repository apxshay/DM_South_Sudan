-- Q3 — Camps reachable within max road distance of a logistical hub (recursive CTE)
--
-- Secondary PostgreSQL baseline. Uses hop cap to avoid national-scale path explosion
-- (same trade-off as Q1 PG-CTE).
--
-- Usage:
--   Get-Content src/queries/postgresql/q3_hub_reachability.sql |
--     docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan \
--       -v hub_id=HUB-001 -v max_distance_m=50000 -v max_hops=50

WITH RECURSIVE
hub AS (
    SELECT
        lh.hub_id,
        pc.road_node_id AS hub_road_node_id,
        pc.length_m     AS hub_connector_m
    FROM logistical_hubs lh
    JOIN health_facilities hf ON hf.facility_id = lh.facility_id
    JOIN poi_connectors pc ON pc.poi_node_id = hf.facility_id
    WHERE lh.hub_id = :'hub_id'
),
search AS (
    SELECT
        h.hub_road_node_id AS node_id,
        h.hub_connector_m  AS cost_m,
        ARRAY[h.hub_road_node_id] AS visited,
        0 AS hops
    FROM hub h
    UNION ALL
    SELECT
        re.end_node_id,
        s.cost_m + re.length_m,
        s.visited || re.end_node_id,
        s.hops + 1
    FROM search s
    JOIN road_edges re ON re.start_node_id = s.node_id
    WHERE s.cost_m <= :max_distance_m
      AND s.hops < :max_hops
      AND NOT re.end_node_id = ANY (s.visited)
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
camp_distances AS (
    SELECT
        cn.site_id AS camp_id,
        cn.site_name AS camp_name,
        cn.state_code,
        MIN(s.cost_m + cn.camp_connector_m) AS total_m,
        MIN(s.cost_m - hub.hub_connector_m) AS road_cost_m
    FROM camp_nodes cn
    JOIN search s ON s.node_id = cn.camp_road_node_id
    CROSS JOIN hub
    GROUP BY cn.site_id, cn.site_name, cn.state_code
),
reachable AS (
    SELECT camp_id, camp_name, state_code, total_m, road_cost_m
    FROM camp_distances
    WHERE total_m <= :max_distance_m
),
isolated AS (
    SELECT cn.site_id AS camp_id, cn.site_name AS camp_name, cn.state_code
    FROM camp_nodes cn
    LEFT JOIN reachable r ON r.camp_id = cn.site_id
    WHERE r.camp_id IS NULL
)
SELECT 'reachable' AS result_set, camp_id, camp_name, state_code, total_m, road_cost_m::text AS extra
FROM reachable
UNION ALL
SELECT 'isolated' AS result_set, camp_id, camp_name, state_code, NULL::double precision, NULL::text
FROM isolated
ORDER BY result_set DESC, total_m NULLS LAST, camp_id;
