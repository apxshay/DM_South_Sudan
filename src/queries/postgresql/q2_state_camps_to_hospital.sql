-- Q2 — All camps in one state → one referral hospital (hop-bounded recursive CTE)
--
-- Secondary PostgreSQL baseline ("pure SQL without extensions").
-- Runs one hop-bounded path search per camp (expected slow at scale).
--
-- Usage:
--   Get-Content src/queries/postgresql/q2_state_camps_to_hospital.sql |
--     docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan \
--       -v state_code=SS01 -v target_hospital_id=SSD-HF-000055 -v max_hops=30

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
per_camp AS (
    SELECT
        c.site_id AS camp_id,
        c.site_name AS camp_name,
        h.hospital_id,
        c.camp_connector_m + best.road_cost_m + h.hospital_connector_m AS total_m,
        best.road_cost_m,
        best.road_hops
    FROM camps c
    CROSS JOIN hospital h
    CROSS JOIN LATERAL (
        WITH RECURSIVE search AS (
            SELECT
                c.start_road_node_id AS node_id,
                0::double precision AS road_cost_m,
                ARRAY[c.start_road_node_id] AS visited,
                0 AS hops
            UNION ALL
            SELECT
                re.end_node_id,
                s.road_cost_m + re.length_m,
                s.visited || re.end_node_id,
                s.hops + 1
            FROM search s
            JOIN road_edges re ON re.start_node_id = s.node_id
            WHERE s.hops < :max_hops
              AND NOT re.end_node_id = ANY (s.visited)
        )
        SELECT
            MIN(s.road_cost_m) AS road_cost_m,
            NULL::integer AS road_hops
        FROM search s
        WHERE s.node_id = h.end_road_node_id
    ) AS best
    WHERE best.road_cost_m IS NOT NULL
)
SELECT camp_id, camp_name, hospital_id, total_m, road_cost_m, road_hops
FROM per_camp
ORDER BY total_m, camp_id;
