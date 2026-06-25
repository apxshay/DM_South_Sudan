// Phase 3 Neo4j import reference
// Primary loader: python scripts/load_neo4j.py
//
// Import order:
//   1. RoadNode (road_nodes.gpkg)
//   2. HealthFacility, DisplacementSite (poi_nodes.gpkg + CSV enrichments)
//   3. ROAD_SEGMENT (road_edges.gpkg)
//   4. CONNECTOR (connector_edges.gpkg)
//   5. CONNECTOR_REVERSE (routing_edges.csv WHERE edge_type = 'connector_reverse')
//   6. LogisticalHub secondary label (logistical_hubs.csv)
//   7. constraints.cypher
//
// Validation
MATCH (n:RoadNode) RETURN count(n);                         // 24779
MATCH ()-[r:ROAD_SEGMENT]->() RETURN count(r);              // 62345
MATCH (h:HealthFacility) RETURN count(h);                   // 2017
MATCH (d:DisplacementSite) RETURN count(d);                 // 77
MATCH ()-[r:CONNECTOR]->() RETURN count(r);                 // 2094
MATCH ()-[r:CONNECTOR_REVERSE]->() RETURN count(r);           // 2094
MATCH (:LogisticalHub) RETURN count(*);                     // 5

// Q1 smoke test
MATCH (c:DisplacementSite {poi_node_id: 'SSD-DS-SS0101_0005'})-[cOut:CONNECTOR]->(start:RoadNode)
MATCH (hf:HealthFacility)
WHERE hf.facility_type IN ['Hospital', 'PHCC']
MATCH (hf)-[hOut:CONNECTOR]->(end:RoadNode)
MATCH p = shortestPath((start)-[:ROAD_SEGMENT*]->(end))
RETURN c.poi_node_id, hf.facility_id, length(p) AS road_hops
LIMIT 1;
