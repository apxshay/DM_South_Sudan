// Q1 — Nearest Hospital/PHCC from one displacement site (GDS Dijkstra, distance-weighted)
//
// Path cost (meters):
//   total_m = camp CONNECTOR + SUM(ROAD_SEGMENT.length_m) + hospital CONNECTOR
//
// Uses gds.allShortestPaths.dijkstra with length_m weights — not hop-based shortestPath().
//
// Parameter: $camp_id (e.g. 'SSD-DS-SS0101_0005')
//
// Usage:
//   Get-Content src/queries/neo4j/q1_nearest_hospital.cypher |
//     docker exec -i dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev
//       --param "camp_id => 'SSD-DS-SS0101_0005'"

CALL gds.graph.drop('q1_road_network', false)
YIELD graphName
WITH count(*) AS _
CALL gds.graph.project(
  'q1_road_network',
  'RoadNode',
  { ROAD_SEGMENT: { orientation: 'NATURAL', properties: 'length_m' } }
)
YIELD graphName
WITH graphName
MATCH (c:DisplacementSite {poi_node_id: $camp_id})-[cOut:CONNECTOR]->(start:RoadNode)
WITH c, cOut, id(start) AS sourceNode
CALL gds.allShortestPaths.dijkstra.stream('q1_road_network', {
  sourceNode: sourceNode,
  relationshipWeightProperty: 'length_m'
})
YIELD targetNode, totalCost AS road_cost_m, nodeIds
MATCH (end:RoadNode) WHERE id(end) = targetNode
MATCH (hf:HealthFacility)-[hOut:CONNECTOR]->(end)
WHERE hf.facility_type IN ['Hospital', 'PHCC']
WITH c, hf, cOut, hOut, road_cost_m, nodeIds,
     cOut.length_m + road_cost_m + hOut.length_m AS total_m
ORDER BY total_m ASC, hf.facility_id ASC
LIMIT 1
RETURN
  c.poi_node_id AS camp_id,
  c.name AS camp_name,
  hf.facility_id AS facility_id,
  hf.name AS facility_name,
  hf.facility_type AS facility_type,
  cOut.length_m AS camp_connector_m,
  road_cost_m AS road_cost_m,
  hOut.length_m AS hospital_connector_m,
  total_m,
  size(nodeIds) - 1 AS road_hops;
