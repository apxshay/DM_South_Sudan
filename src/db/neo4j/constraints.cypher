// South Sudan humanitarian spatial graph — Neo4j constraints and indexes
// Phase 2 deliverable for Phase 3 population and Phase 5 benchmarking.
// Source: docs/phase2_graph_schema.md
//
// Run after initial data load or before MERGE-based import.

// ---------------------------------------------------------------------------
// Uniqueness constraints
// ---------------------------------------------------------------------------

CREATE CONSTRAINT road_node_id IF NOT EXISTS
FOR (n:RoadNode) REQUIRE n.node_id IS UNIQUE;

CREATE CONSTRAINT health_facility_poi_id IF NOT EXISTS
FOR (n:HealthFacility) REQUIRE n.poi_node_id IS UNIQUE;

CREATE CONSTRAINT health_facility_id IF NOT EXISTS
FOR (n:HealthFacility) REQUIRE n.facility_id IS UNIQUE;

CREATE CONSTRAINT displacement_site_poi_id IF NOT EXISTS
FOR (n:DisplacementSite) REQUIRE n.poi_node_id IS UNIQUE;

CREATE CONSTRAINT displacement_site_id IF NOT EXISTS
FOR (n:DisplacementSite) REQUIRE n.site_id IS UNIQUE;

CREATE CONSTRAINT logistical_hub_id IF NOT EXISTS
FOR (n:LogisticalHub) REQUIRE n.hub_id IS UNIQUE;

// ---------------------------------------------------------------------------
// Lookup indexes
// ---------------------------------------------------------------------------

CREATE INDEX health_facility_type_state IF NOT EXISTS
FOR (n:HealthFacility) ON (n.facility_type, n.state_code);

CREATE INDEX health_facility_road_node IF NOT EXISTS
FOR (n:HealthFacility) ON (n.nearest_road_node_id);

CREATE INDEX displacement_site_state IF NOT EXISTS
FOR (n:DisplacementSite) ON (n.state_code);

CREATE INDEX displacement_site_road_node IF NOT EXISTS
FOR (n:DisplacementSite) ON (n.nearest_road_node_id);

CREATE INDEX road_segment_highway IF NOT EXISTS
FOR ()-[r:ROAD_SEGMENT]-() ON (r.highway);

CREATE INDEX road_segment_edge_id IF NOT EXISTS
FOR ()-[r:ROAD_SEGMENT]-() ON (r.edge_id);

CREATE INDEX connector_edge_id IF NOT EXISTS
FOR ()-[r:CONNECTOR]-() ON (r.edge_id);

// ---------------------------------------------------------------------------
// Optional: composite labels applied at import time
// MERGE (h:HealthFacility:LogisticalHub {hub_id: $hub_id, ...})
// ---------------------------------------------------------------------------
