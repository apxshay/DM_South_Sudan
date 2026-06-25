-- Phase 3 PostgreSQL data load reference
-- Primary loader: python scripts/load_postgresql.py
--
-- Load order (respects foreign keys):
--   1. admin_states, admin_counties, admin_payams
--   2. health_facilities
--   3. displacement_sites (+ snap fields from poi_nodes.csv)
--   4. logistical_hubs
--   5. road_nodes, road_edges
--   6. poi_connectors
--   7. facility_road_access
--   8. routing_edges
--
-- Validation:
SELECT COUNT(*) FROM health_facilities;           -- expect 2251
SELECT COUNT(*) FROM displacement_sites;          -- expect 77
SELECT COUNT(*) FROM road_nodes;                  -- expect 24779
SELECT COUNT(*) FROM road_edges;                  -- expect 62345
SELECT COUNT(*) FROM routing_edges;               -- expect 66533
SELECT * FROM v_state_humanitarian_stats LIMIT 5;

-- Q1 smoke prerequisites
SELECT ds.site_id
FROM displacement_sites ds
JOIN poi_connectors pc ON pc.poi_node_id = ds.site_id
WHERE ds.site_id = 'SSD-DS-SS0101_0005';

SELECT hf.facility_id
FROM health_facilities hf
JOIN logistical_hubs lh ON lh.facility_id = hf.facility_id
WHERE hf.facility_id = 'SSD-HF-000055';
