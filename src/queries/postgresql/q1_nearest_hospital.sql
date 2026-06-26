-- Q1 — Nearest Hospital/PHCC from one displacement site (PG-CTE baseline)
--
-- Secondary PostgreSQL track for Phase 5 ("pure SQL without extensions").
-- Path cost (meters):
--   total_m = camp_connector + SUM(road_segment.length_m) + hospital_connector
--
-- Approach: directed traversal on road_edges via recursive CTE, excluding
-- facility_type = 'unknown'. Among all simple paths up to max_hops, picks the
-- minimum total_m to any Hospital/PHCC access node.
--
-- Discovery notes (Phase 4):
--   - pgRouting is not installed.
--   - Unbounded path-exploration CTE did not complete in >3 min.
--   - plpgsql Dijkstra over 62k edges was too slow in interpreted loops.
--   - Hop limit 30 completes ~12–36 s on smoke camp and matches GDS Dijkstra.
--
-- Usage (pipe into container — project dir is not mounted in Docker):
--   Get-Content src/queries/postgresql/q1_nearest_hospital.sql |
--     docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan \
--       -v camp_id=SSD-DS-SS0101_0005 -v max_hops=30

WITH RECURSIVE
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
search AS (
    SELECT
        c.start_road_node_id AS node_id,
        c.camp_connector_m   AS cost_m,
        ARRAY[c.start_road_node_id] AS visited,
        0 AS hops
    FROM camp c
    UNION ALL
    SELECT
        re.end_node_id,
        s.cost_m + re.length_m,
        s.visited || re.end_node_id,
        s.hops + 1
    FROM search s
    JOIN road_edges re ON re.start_node_id = s.node_id
    WHERE s.hops < :max_hops
      AND NOT re.end_node_id = ANY (s.visited)
),
ranked AS (
    SELECT
        t.facility_id,
        t.facility_name,
        t.facility_type,
        t.hospital_connector_m,
        s.cost_m + t.hospital_connector_m AS total_m,
        s.cost_m - camp.camp_connector_m AS road_cost_m,
        s.hops AS road_hops,
        ROW_NUMBER() OVER (
            PARTITION BY t.facility_id
            ORDER BY s.cost_m + t.hospital_connector_m, s.hops
        ) AS rn
    FROM search s
    JOIN targets t ON t.road_node_id = s.node_id
    CROSS JOIN camp
)
SELECT
    camp.site_id   AS camp_id,
    camp.site_name AS camp_name,
    r.facility_id,
    r.facility_name,
    r.facility_type,
    camp.camp_connector_m,
    r.road_cost_m,
    r.hospital_connector_m,
    r.total_m,
    r.road_hops
FROM ranked r
CROSS JOIN camp
WHERE r.rn = 1
ORDER BY r.total_m, r.facility_id
LIMIT 1;
