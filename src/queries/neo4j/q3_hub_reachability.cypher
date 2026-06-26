// Q3 — Hub reachability within max road distance (GDS Dijkstra)
//
// total_m = hub CONNECTOR + road_cost + camp CONNECTOR
//
// Parameters: $hub_id, $max_distance_m

CALL gds.graph.drop('q3_road_network', false)
YIELD graphName
WITH count(*) AS _
CALL gds.graph.project(
  'q3_road_network',
  'RoadNode',
  { ROAD_SEGMENT: { orientation: 'NATURAL', properties: 'length_m' } }
)
YIELD graphName
WITH graphName
MATCH (hub:LogisticalHub {hub_id: $hub_id})
MATCH (hf:HealthFacility {facility_id: hub.facility_id})-[hOut:CONNECTOR]->(hubStart:RoadNode)
WITH hOut, id(hubStart) AS sourceNode, $max_distance_m AS maxDistanceM
CALL gds.allShortestPaths.dijkstra.stream('q3_road_network', {
  sourceNode: sourceNode,
  relationshipWeightProperty: 'length_m'
})
YIELD targetNode, totalCost AS road_cost_m
WITH hOut, maxDistanceM, collect({nodeId: targetNode, road_cost_m: road_cost_m}) AS roadCosts
MATCH (c:DisplacementSite)-[cOut:CONNECTOR]->(campStart:RoadNode)
WITH c, cOut, hOut, maxDistanceM, roadCosts,
     [rc IN roadCosts WHERE rc.nodeId = id(campStart) | rc.road_cost_m][0] AS road_cost_m
WITH c, cOut, hOut, maxDistanceM, road_cost_m,
     CASE
       WHEN road_cost_m IS NULL THEN null
       ELSE hOut.length_m + road_cost_m + cOut.length_m
     END AS total_m
RETURN
  CASE
    WHEN total_m IS NOT NULL AND total_m <= maxDistanceM THEN 'reachable'
    ELSE 'isolated'
  END AS result_set,
  c.poi_node_id AS camp_id,
  c.name AS camp_name,
  c.state_code AS state_code,
  CASE WHEN total_m IS NOT NULL AND total_m <= maxDistanceM THEN total_m ELSE null END AS total_m,
  CASE WHEN total_m IS NOT NULL AND total_m <= maxDistanceM THEN road_cost_m ELSE null END AS road_cost_m
ORDER BY result_set DESC, total_m, camp_id;
