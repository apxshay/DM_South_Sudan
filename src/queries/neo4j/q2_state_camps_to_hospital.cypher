// Q2 — All camps in one state → one referral hospital (GDS Dijkstra)
//
// Path cost (meters):
//   total_m = camp CONNECTOR + SUM(ROAD_SEGMENT.length_m) + hospital CONNECTOR
//
// Parameters: $state_code, $target_facility_id
//
// Usage:
//   Get-Content src/queries/neo4j/q2_state_camps_to_hospital.cypher |
//     docker exec -i dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev
//       --param "state_code => 'SS01'" --param "target_facility_id => 'SSD-HF-000055'"

CALL gds.graph.drop('q2_road_network', false)
YIELD graphName
WITH count(*) AS _
CALL gds.graph.project(
  'q2_road_network',
  'RoadNode',
  { ROAD_SEGMENT: { orientation: 'NATURAL', properties: 'length_m' } }
)
YIELD graphName
WITH graphName
MATCH (target:HealthFacility {facility_id: $target_facility_id})-[tOut:CONNECTOR]->(end:RoadNode)
MATCH (c:DisplacementSite {state_code: $state_code})-[cOut:CONNECTOR]->(start:RoadNode)
WITH c, target, cOut, tOut, id(start) AS sourceNode, id(end) AS targetNode
CALL gds.shortestPath.dijkstra.stream('q2_road_network', {
  sourceNode: sourceNode,
  targetNode: targetNode,
  relationshipWeightProperty: 'length_m'
})
YIELD totalCost AS road_cost_m
RETURN
  c.poi_node_id AS camp_id,
  c.name AS camp_name,
  target.facility_id AS hospital_id,
  cOut.length_m + road_cost_m + tOut.length_m AS total_m,
  road_cost_m,
  NULL AS road_hops
ORDER BY total_m, camp_id;
