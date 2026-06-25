# Phase 1 — Data Understanding Report

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Date:** 2025-06-23 (updated with HOT OSM roads)  
**Status:** Complete — no transformations applied

---

## 1. Overview

Five dataset families were profiled from `data/raw/` (two independent road network sources):

| Domain | Source (HDX) | Records | Spatial data | Content summary |
|--------|--------------|---------|--------------|-----------------|
| Roads (humanitarian) | [South Sudan: Road Network](https://data.humdata.org/dataset/south-sudan-road-network_hdx) | 976 line features | Yes (WGS84) | Road and river line geometries with segment attributes |
| Roads (HOT OSM) | [Roads of South Sudan](https://data.humdata.org/dataset/hotosm_ssd_roads) | 20,512 line features (filtered) | Yes (WGS84) | OpenStreetMap road lines; filtered to primary, secondary, tertiary, unclassified |
| Health facilities | [South Sudan - Health Facilities](https://data.humdata.org/dataset/south-sudan-health-facilities) | 1,513–1,988 per file | Partial (lat/lon) | Facility names, admin codes, coordinates; two files with different schemas |
| IDP displacements | [South Sudan - IDPs (IDMC)](https://data.humdata.org/dataset/idmc-idp-data-ssd) | 15 annual + 158 disaster events | No | National annual displacement totals and disaster-event records |
| Displacement sites | [South Sudan Displacement Data - Site Assessment (IOM DTM)](https://data.humdata.org/dataset/south-sudan-displacement-data-site-assessment-iom-dtm) | 77–94 sites per round (6 rounds) | Yes (GPS lat/lon) | Per-site IDP counts, admin codes, settlement attributes, survey responses |

### Summary observations

1. **Humanitarian roads:** 976 line features (966 `LineString`, 10 `MultiLineString`). The dataset mixes roads (690) and rivers (282). Several attributes (`name`, `surface_ty`, `status`) have high null rates.
2. **HOT OSM roads:** 182,544 line features in the raw export; 20,512 retained after filtering to `highway` values `primary`, `secondary`, `tertiary`, and `unclassified`. All filtered features are `LineString`. Includes OpenStreetMap tags and admin boundary codes at state/county/payam level. `name` is populated for only 8.3% of filtered segments.
3. **Health facilities:** Two files from the same HDX source with different vintages, schemas, and row counts. The 2023 file includes facility type and numeric codes; the 2025 WHO file has more rows and more complete coordinates but lacks facility type and a dedicated facility code column.
4. **IDMC IDP data:** National annual aggregates (15 rows, 2011–2025) and disaster-event records (158 rows) with no coordinates. Location information in disaster events appears only as free text in `event_name`.
5. **IOM DTM site assessments:** Six rounds of displacement site data. Round 11 contains 77 sites with full GPS coordinates, admin P-codes, and per-site household/individual IDP counts. This is the only dataset in the collection with georeferenced displacement site locations.

---

## 2. Road Network — Humanitarian Basemap (HDX)

**Path:** `data/raw/roads/SSD_road_network/SSD_Road_network.shp`  
**Format:** ESRI Shapefile, CRS **EPSG:4326** (WGS84)  
**Rows:** 976 features

### 2.1 Schema

| Column | Data type | Non-null | Null % | Unique | Description |
|--------|-----------|----------|--------|--------|-------------|
| `id` | float64 | 976 | 0% | 976 | Segment identifier (stored as float; no duplicates) |
| `name` | string | 490 | 49.8% | 65 | Road/river name |
| `type` | string | 976 | 0% | 3 | `road`, `river`, `small_river` |
| `surface_ty` | string | 72 | 92.6% | 1 | Surface type (`Unpaved` only, when present) |
| `status` | string | 460 | 52.9% | 5 | Operational status (mostly populated for rivers) |
| `capacity` | int64 | 976 | 0% | 3 | Numeric capacity class |
| `speed` | int64 | 976 | 0% | 4 | Speed value |
| `geometry` | LineString / MultiLineString | 976 | 0% | 976 | Segment geometry |

### 2.2 Value distributions

**`type`:** road (690), river (282), small_river (4)

**`status`:** NaN (516), Navigable all year (282), Warning (130), Closed (38), Open (6), Reaches with rapids (4)

**`capacity`:** 10 (690), 100 (282), 1 (4) — values correlate with `type`

**`speed`:** 40 (482), 20 (418), 70 (72), 8 (4)

### 2.3 Spatial extent

Bounding box (lon/lat): `[24.42, 3.54, 34.94, 12.60]` — falls within South Sudan.

- Null geometries: 0
- Invalid geometries: 0

### 2.4 Uniqueness and identifiers

- `id` is unique across all 976 rows (976 distinct values, 0 duplicates).
- `id` is stored as `float64` despite appearing to represent integer identifiers.
- No columns encode explicit start/end node references; connectivity information is present only in the geometry.

### 2.5 Data quality issues

| Issue | Severity | Notes |
|-------|----------|-------|
| Mixed feature types (road + river) | Medium | Single `type` column distinguishes categories |
| High null rate in `name`, `surface_ty`, `status` | Medium | 49.8%, 92.6%, and 52.9% null respectively |
| `id` stored as float64 | Low | No missing values; type mismatch with integer semantics |
| No explicit endpoint/node columns | Medium | Only geometry defines segment extent |
| No length attribute | Low | Not present as a column |

---

## 3. Road Network — HOT OSM (OpenStreetMap)

**HDX source:** [Roads of South Sudan](https://data.humdata.org/dataset/hotosm_ssd_roads)  
**Provider:** Humanitarian OpenStreetMap Team (HOT), exported via [oex](https://github.com/osgeonepal/oex)  
**Raw path:** `data/raw/roads_hotosm/roads_lines.shp`  
**Filtered path:** `data/raw/roads_hotosm/filtered/roads_lines_filtered.gpkg`  
**Format:** ESRI Shapefile (raw), GeoPackage (filtered), CRS **EPSG:4326** (WGS84)  
**OSM snapshot:** 2026-06-22

The raw export contains 182,544 line features tagged with OpenStreetMap `highway=*` values. The export also includes separate point (`roads_points.shp`, 345 features) and polygon (`roads_polygons.shp`, 77 features) layers, which were not included in this analysis.

A filtered subset retaining only `highway` values **primary**, **secondary**, **tertiary**, and **unclassified** was saved to the filtered GeoPackage (20,512 features).

### 3.1 Filter applied

| Stage | Row count |
|-------|-----------|
| Raw lines (`roads_lines.shp`) | 182,544 |
| After filter (`highway` ∈ primary, secondary, tertiary, unclassified) | 20,512 |

**Filtered `highway` distribution:**

| `highway` | Count |
|-----------|-------|
| unclassified | 18,115 |
| tertiary | 1,020 |
| primary | 947 |
| secondary | 430 |

Other `highway` values present in the raw data but excluded include `path` (102,333), `residential` (32,136), `track` (22,898), `service` (2,777), `footway` (1,668), `trunk` (58), and others.

### 3.2 Schema (filtered)

| Column | Data type | Null % | Unique | Description |
|--------|-----------|--------|--------|-------------|
| `id` | string | 0% | 20,512 | OSM feature identifier |
| `name` | string | 91.7% | 447 | Road name |
| `name_en` | string | 99.9% | 18 | English name |
| `highway` | string | 0% | 4 | OSM highway classification |
| `surface` | string | 66.8% | 14 | Surface material |
| `smoothness` | string | 99.8% | 5 | Surface smoothness |
| `width` | string | 99.9% | 4 | Road width |
| `lanes` | string | 99.6% | 4 | Lane count |
| `oneway` | string | 98.7% | 3 | One-way indicator (`yes`, `no`, `-1`) |
| `bridge` | string | 98.3% | 2 | Bridge indicator (`yes`, `low_water_crossing`) |
| `layer` | string | 98.2% | 2 | Z-order layer |
| `source` | object | 100% | 0 | Entirely null in filtered set |
| `adm0_pcode` | string | 0% | 1 | Country code |
| `adm0_name` | string | 0% | 1 | Country name |
| `adm1_pcode` | string | 0.2% | 10 | State P-code |
| `adm1_name` | string | 0.2% | 10 | State name |
| `adm2_pcode` | string | 0.2% | 78 | County P-code |
| `adm2_name` | string | 0.2% | 78 | County name |
| `adm3_pcode` | string | 0.2% | 453 | Payam P-code |
| `adm3_name` | string | 0.2% | 453 | Payam name |
| `adm4_pcode` | object | 100% | 0 | Entirely null |
| `adm4_name` | object | 100% | 0 | Entirely null |
| `name_latin` | string | 91.7% | 436 | Latin-script name variant |
| `geometry` | LineString | 0% | 20,512 | Segment geometry |

### 3.3 Value distributions (filtered)

**`surface` (non-null):** unpaved (6,252), ground (144), dirt (120), asphalt (108), paved (69), compacted (60), gravel (28), sand (14), other (17)

**`oneway` (non-null):** yes (224), no (49), -1 (1)

**`bridge` (non-null):** yes (351), low_water_crossing (1)

### 3.4 Spatial extent

Bounding box (lon/lat): `[24.55, 3.48, 35.95, 12.33]` — falls within South Sudan.

- Geometry type: LineString (20,512)
- Null geometries: 0
- Invalid geometries: 0

### 3.5 Uniqueness and identifiers

- `id` is unique across all 20,512 filtered rows (0 duplicates).
- 41 rows (0.2%) have null admin P-code/name fields at state, county, or payam level.
- No columns encode explicit start/end node references.

### 3.6 Comparison with humanitarian road network (Section 2)

| Aspect | Humanitarian (Section 2) | HOT OSM filtered (this section) |
|--------|--------------------------|----------------------------------|
| Feature count | 976 | 20,512 |
| Includes rivers | Yes (286 features) | No |
| Classification column | `type` (road/river) | `highway` (OSM tag) |
| Admin codes in data | No | Yes (state/county/payam P-codes) |
| `name` completeness | 50.2% | 8.3% |
| Source | HDX humanitarian basemap | OpenStreetMap community data |

The two road datasets share a similar geographic extent but differ substantially in feature count, classification scheme, and attribute completeness. They are independent sources with no shared segment identifier.

### 3.7 Data quality issues

| Issue | Severity | Notes |
|-------|----------|-------|
| Very high null rate in `name` | High | 91.7% null in filtered set |
| Sparse surface/oneway/bridge attributes | Medium | 67–99% null depending on column |
| `source`, `adm4_*` columns entirely null | Low | No values in filtered set |
| Unclassified dominates filtered set | Medium | 88.3% of filtered features are `unclassified` |
| Coverage varies by region | Medium | OSM mapping is community-driven; remote areas may be under-mapped |
| No shared ID with humanitarian roads | Medium | Two independent road sources |

---

## 4. Health Facilities Datasets

Two files from the same HDX dataset, different vintages and schemas.

### 4.1 WHO Master Facility List (April 2025)

**Path:** `data/raw/health_facilities/original/who-master-facility-list_april2025.xlsx`  
**Sheet:** `hsf_master_facility_list_202403`  
**Rows:** 1,988

| Column | Data type | Null % | Unique | Notes |
|--------|-----------|--------|--------|-------|
| `old_state` | string | 0% | 11 | State name (lowercase) |
| `state_code` | string | 0% | 11 | Codes SS00–SS10 |
| `county` | string | 0% | 79 | County name |
| `county_code` | string | 0% | 79 | e.g. SS0601 |
| `payam` | string | 1.2% | 478 | Sub-county |
| `payam_code` | string | 1.5% | 476 | e.g. SS060101 |
| `site` | string | 0% | 1,947 | Facility name (41 duplicate values) |
| `site_dhis2_name` | string | 32.1% | 1,330 | DHIS2 display name |
| `latitude` | float64 | 5.7% | 1,869 | WGS84 |
| `longitude` | float64 | 5.7% | 1,867 | WGS84 |

**Coordinates:** 1,875 of 1,988 rows have both latitude and longitude (94.3%). One longitude value falls outside the approximate South Sudan bounding box used for validation; no latitude outliers detected.

### 4.2 SS Final Master List with Codes (June 2023)

**Path:** `data/raw/health_facilities/original/ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx`

#### Sheet: `Health Facilities & Codes` — 1,513 rows

| Column | Data type | Null % | Unique | Notes |
|--------|-----------|--------|--------|-------|
| `State` | string | 0% | 12 | Title-case state names |
| `State_Code` | string | 0% | 19 | SS00–SS18 |
| `County` | string | 0% | 79 | |
| `County_Code` | string | 0% | 79 | |
| `Payam` | string | 0% | 472 | |
| `Payam_Code ` | string | 0% | 471 | Column name has trailing space |
| `Facility_Name` | string | 0% | 1,480 | 33 duplicate values |
| `Type` | string | 0% | 3 | PHCU (1,065), PHCC (373), Hospital (75) |
| `Facilities_Code` | int64 | 0% | 1,511 | 2 duplicate codes |
| `Latitude` | float64 | 14.9% | 1,268 | |
| `Longitude` | float64 | 14.9% | 1,264 | |

**Duplicate `Facilities_Code` values:**
- `75020101` — Panyang PHCU and Abiemnom PHCC
- `92040402` — Tore PHCC and Kundru PHCU

#### Sheet: `Admin_data` — 512 rows

Administrative hierarchy: State → County → Payam with codes.  
512 rows, 512 unique `Payam_Code` values.

### 4.3 Cross-file comparison

| Metric | WHO 2025 | SS 2023 |
|--------|----------|---------|
| Row count | 1,988 | 1,513 |
| Facility type column | Absent | Present (`Type`) |
| Dedicated facility code column | Absent | Present (`Facilities_Code`) |
| Coordinate completeness | 94.3% | 85.1% |
| Normalized site name overlap | — | 1,235 names appear in both files |

### 4.4 Uniqueness and identifiers

| File / sheet | Column(s) | Uniqueness |
|--------------|-----------|------------|
| WHO 2025 | `site` | 1,947 unique of 1,988 rows (41 duplicates) |
| WHO 2025 | (`state_code`, `county_code`, `payam_code`, `site`) | Not verified as unique composite |
| SS 2023 facilities | `Facilities_Code` | 1,511 unique of 1,513 rows (2 duplicates) |
| SS 2023 facilities | `Facility_Name` | 1,480 unique of 1,513 rows (33 duplicates) |
| SS 2023 admin | `Payam_Code` | 512 unique of 512 rows |

### 4.5 Shared admin codes

Both facility files use state/county/payam naming and coding conventions similar to the `Admin_data` sheet in the SS 2023 file. State codes in the WHO file span SS00–SS10 (11 values); the SS 2023 facilities sheet lists 19 distinct `State_Code` values for 12 state names.

### 4.6 Data quality issues

| Issue | Severity | Notes |
|-------|----------|-------|
| Two files with different schemas and row counts | High | Same HDX dataset, different vintages |
| Duplicate `Facilities_Code` (SS 2023) | High | 2 codes assigned to 2 facilities each |
| Duplicate site/facility names (both files) | Medium | 41 in WHO, 33 in SS 2023 |
| Missing coordinates | Medium | 5.7% (WHO), 14.9% (SS 2023) |
| Column naming inconsistency | Low | `Payam_Code ` trailing space; mixed case conventions |
| `State_Code` cardinality mismatch (SS 2023) | Medium | 19 distinct codes, 12 state names |

---

## 5. IDMC IDP Datasets

### 5.1 Annual country-level displacements

**Path:** `data/raw/idp/original/internal-displacements-new-displacements-idps_ssd.csv`  
**Rows:** 15 (years 2011–2025)  
**Source:** IDMC via HDX

| Column | Data type | Null % | Description |
|--------|-----------|--------|-------------|
| `iso3` | string | 0% | Country code (SSD) |
| `country_name` | string | 0% | South Sudan |
| `year` | int64 | 0% | Reference year |
| `new_displacement` | int64 | 0% | New displacements in year |
| `new_displacement_rounded` | int64 | 0% | Rounded variant |
| `total_displacement` | int64 | 0% | Stock of IDPs |
| `total_displacement_rounded` | int64 | 0% | Rounded variant |

**Uniqueness:** `year` has 15 distinct values across 15 rows (one row per year).

**Spatial content:** None. All rows refer to the country level.

### 5.2 Disaster-associated displacements

**Path:** `data/raw/idp/original/internal-displacements-new-displacements-associated-with-disasters_ssd.csv`  
**Rows:** 158 events (2012–2025)

| Column | Data type | Null % | Notes |
|--------|-----------|--------|-------|
| `iso3`, `country_name` | string | 0% | Constant (SSD / South Sudan) |
| `year` | int64 | 0% | 13 distinct years |
| `start_date`, `end_date` | string (date) | 0–1% | ISO-like date strings |
| `start_date_accuracy`, `end_date_accuracy` | string | 2–3% | Day / Week / Month |
| `event_name` | string | 0% | Free text; often contains place names |
| `hazard_*` | int / string | 0% | IDMC hazard taxonomy (category, type, sub-type) |
| `hazard_subtype_name` | float64 | **100%** | Entirely null |
| `new_displacement` | int64 | 0% | Event-level count |
| `new_displacement_rounded` | int64 | 0% | |
| `total_displacement` | float64 | **99.4%** | Populated in 1 of 158 rows |
| `total_displacement_rounded` | float64 | **99.4%** | Populated in 1 of 158 rows |
| `event_codes` | string | **96.2%** | Populated in 6 of 158 rows |

**Uniqueness:** `event_name` has 158 distinct values across 158 rows.

**Location content in `event_name`:** 149 of 158 events contain a `" - "` delimiter suggesting a place name; 9 appear country-level only. Recurring place-name tokens include Jonglei (29 events), Unity (36), Upper Nile (18), Warrap (17), and Equatoria (22). No latitude, longitude, or admin code columns are present.

### 5.3 Data quality issues

| Issue | Severity | Notes |
|-------|----------|-------|
| No coordinates | High | Neither file contains spatial columns |
| `hazard_subtype_name` 100% null | Low | Column contains no values |
| `total_displacement` 99.4% null (disasters) | Low | Only `new_displacement` is consistently populated |
| `event_codes` 96.2% null | Medium | External event IDs present for 6 events only |
| Date accuracy varies | Medium | Values include Day, Week, Month |
| No shared key with other datasets | Medium | No column links directly to IOM DTM or health facility data |

---

## 6. Displacement Sites Dataset (IOM DTM)

**HDX source:** [South Sudan Displacement Data - Site Assessment (IOM DTM)](https://data.humdata.org/dataset/south-sudan-displacement-data-site-assessment-iom-dtm)  
**Path:** `data/raw/displacement_sites/original/`  
**Provider:** IOM Displacement Tracking Matrix (DTM)  
**Description:** Site assessments record population presence, living conditions, and needs at displacement sites. Includes IDP household and individual counts with age/gender disaggregation at sub-national level.

Six assessment rounds are available (Rounds 4, 5, 6, 8, 10, 11). Round 11 is the most recent; detailed column analysis below uses Round 11.

### 6.1 Available files and round comparison

| File | Round | Main sheet | Sites (excl. metadata row) | Columns |
|------|-------|------------|---------------------------|---------|
| `dtm-south-sudan-site-assessment-round-4.xlsx` | 4 | `S_Sudan_SA_R4` | 77 | 121 |
| `dtm-south-sudan-site-assessment-round-5.xlsx` | 5 | `DTM_SS_SA_R5` | 93 | ~145 |
| `dtm-south-sudan-site-assessment-round-6.xlsx` | 6 | `DTM_SSD_SA_R6` | 84 | ~144 |
| `dtm-south-sudan-site-assessment-round-8.xlsx` | 8 | `DTM_SSD_SA_R8` | 87 | ~147 |
| `hdx_iom_dtm_ssd_mt10_sa.xlsx` | 10 | `DTM_SSD_SA_R10` | 92 | ~215 |
| `hdx_ssd-dtm-mobility-tracking-r11-site-assessment-dataset.xlsx` | 11 | `MT11 SA` | 77 | 214 |

Each file also includes `Dictionary` / `Data_Dictionary` sheets (variable definitions) and, from Round 8 onward, a `Notes` sheet. Column names and counts differ across rounds (human-readable names in R4 vs coded names in R11). Site counts range from 77 to 93 across rounds.

**Structural note:** Row 1 of each main sheet contains metadata labels (e.g. `#date+occurred`, `#geo+lon`) rather than site data. Excluding this row, Round 11 has 77 site records.

### 6.2 Round 11 — identity and location columns

**Path:** `data/raw/displacement_sites/original/hdx_ssd-dtm-mobility-tracking-r11-site-assessment-dataset.xlsx`  
**Sheet:** `MT11 SA`  
**Rows:** 77 (after excluding metadata row)  
**Columns:** 214 total

| Column | Data type | Null % | Unique | Description |
|--------|-----------|--------|--------|-------------|
| `a02.mt.round` | numeric | 0% | 1 | Assessment round (value: 11) |
| `b01.location.ssid` | string | 0% | 77 | Location SSID |
| `b02.location.name` | string | 0% | 77 | Site name |
| `b03.nearest.vn` | string | 0% | 68 | Nearest village/neighborhood |
| `b04.state.name` | string | 0% | 10 | State name |
| `b05.state.pcode` | string | 0% | 10 | State P-code (SS01–SS10) |
| `b06.county.name` | string | 0% | 29 | County name |
| `b07.county.pcode` | string | 0% | 29 | County P-code |
| `b08.payam.name` | string | 0% | 52 | Payam name |
| `b09.payam.pcode` | string | 0% | 52 | Payam P-code |
| `b10.gps.lon` | float64 | 0% | 77 | Longitude (WGS84) |
| `b11.gps.lat` | float64 | 0% | 77 | Latitude (WGS84) |
| `b13.accessibility` | string | 0% | 3 | Site accessibility |
| `b14.settlement.type` | string | 0% | 5 | Settlement classification |

**SSID format example:** `ssid_SS0101_0005`

### 6.3 Round 11 — population columns

| Column | Data type | Null % | Description |
|--------|-----------|--------|-------------|
| `c01.idp.hh` | int64 | 0% | IDP households (sum across sites: 69,669) |
| `c02.idp.ind` | int64 | 0% | IDP individuals (sum across sites: 388,049) |
| `c03.idp.m01` – `c14.idp.f60` | int64 | 0% | Age/gender-disaggregated IDP counts (12 groups) |

### 6.4 Round 11 — categorical distributions

**`b14.settlement.type`:** Spontaneous camp/site (26), Planned camp/site (25), Collective Centre (19), Dispersed settlement (6), Protection of Civilians (PoC) site (1)

**`b17.idp.disp.reason`:** Conflict (49), Communal clashes (17), Natural disaster (11)

**`b13.accessibility`:** Accessible by car (34), Accessible by foot (29), Accessible by other means (14)

**`b34.site.ownership`:** Public/Government (54), Ancestral (15), Private (8)

**`b04.state.name` distribution:** Jonglei (25), Central Equatoria (15), Unity (9), Warrap (8), Upper Nile (7), Western Bahr El Ghazal (4), Western Equatoria (3), Eastern Equatoria (2), Lakes (2), Northern Bahr El Ghazal (2)

### 6.5 Round 11 — remaining columns

Columns `b18`–`l04` cover displacement origins, shelter, water/sanitation, livelihoods, health, education, security, and mobility restrictions. Of 214 columns:

- 89 columns: 0% null
- 55 columns: >50% null
- 35 columns: 100% null

### 6.6 Spatial extent (Round 11)

- Bounding box (lon/lat): `[26.26, 3.55, 33.74, 10.44]`
- GPS coordinates present for all 77 sites
- Duplicate coordinate pairs: 0
- Coordinates outside approximate South Sudan bounds: 0

### 6.7 Uniqueness and identifiers

| Column | Unique values | Rows | Notes |
|--------|---------------|------|-------|
| `b01.location.ssid` | 77 | 77 | No duplicates in Round 11 |
| `b02.location.name` | 77 | 77 | No duplicates in Round 11 |
| `b10.gps.lon` | 77 | 77 | No duplicates in Round 11 |
| `b11.gps.lat` | 77 | 77 | No duplicates in Round 11 |

### 6.8 Overlap with other datasets (Round 11)

**Payam P-code overlap:**
- 52 distinct payam codes in Round 11
- 45 match `payam_code` in WHO 2025 health facilities
- 42 match `Payam_Code` in SS 2023 health facilities
- 7 payam codes appear only in the DTM data

**Population comparison with IDMC annual data:**
- Round 11 site-level IDP individuals (sum): 388,049
- IDMC `total_displacement` for 2024: 944,631
- IDMC `total_displacement` for 2025: 944,894

The site assessment covers a subset of the nationally reported IDP population.

### 6.9 Comparison with IDMC IDP data

| Aspect | IDMC (Section 5) | IOM DTM (this section) |
|--------|------------------|------------------------|
| Granularity | National annual + disaster events | Individual displacement sites |
| Coordinates | None | GPS for every site in Round 11 |
| Population fields | National or per-event aggregates | Per-site households and individuals |
| Admin codes | None | State, county, payam P-codes |
| Temporal coverage | 2011–2025 (annual), 2012–2025 (disasters) | 6 assessment rounds (site counts vary) |

No shared identifier column exists between IDMC and IOM DTM files.

### 6.10 Data quality issues

| Issue | Severity | Notes |
|-------|----------|-------|
| Schema changes across rounds | High | Column names and counts differ between rounds |
| Metadata row in main sheet | Medium | Row 1 is not a site record |
| Site count varies by round (77–93) | Medium | Different sites assessed in each round |
| 35 columns 100% null in R11 | Low | Unused questionnaire fields |
| 55 columns >50% null in R11 | Low | Sparsely populated survey responses |
| Site count vs national IDP totals | Medium | 388k individuals at assessed sites vs ~945k national total (IDMC 2024–2025) |
| No shared key with IDMC data | Medium | No direct join column between datasets |

---

## 7. Cross-Dataset Observations

Factual overlaps and differences observed across the five dataset families:

| Shared element | Datasets involved | Observation |
|----------------|-------------------|-------------|
| Road networks | Humanitarian roads, HOT OSM roads | Independent sources; 976 vs 20,512 filtered features; no shared segment ID; humanitarian set includes rivers |
| Admin P-codes | Health (SS 2023), Health (WHO), IOM DTM, HOT OSM roads | State/county/payam codes use similar `SS##` patterns; HOT OSM roads include admin codes; humanitarian roads do not |
| Coordinates | Both road sets, Health, IOM DTM | Road networks and sites have full spatial data; health facilities are partially geocoded; IDMC data has none |
| Facility/site names | Health (both files) | 1,235 normalized name matches between WHO 2025 and SS 2023; duplicates exist within each file |
| Payam codes | Health, IOM DTM | 45 of 52 DTM payam codes appear in WHO health data |
| IDP population figures | IDMC annual, IOM DTM | National totals (IDMC) exceed sum of site-level counts (IOM DTM Round 11) |
| Place names | IDMC disasters, IOM DTM | Both reference states/counties by name, but in different structures (free text vs coded admin columns) |
| Temporal data | IDMC, IOM DTM | IDMC spans 2011–2025; IOM DTM has 6 discrete assessment rounds with varying site lists |

---

## 8. Artifacts

| Artifact | Path |
|----------|------|
| This report | `docs/phase1_data_understanding.md` |
| Machine-readable profile | `docs/phase1_profile.json` |
| Exploration script | `scripts/explore_datasets.py` |

Regenerate the JSON profile:

```bash
data_env/bin/python scripts/explore_datasets.py
```

---

## 9. Analysis Checklist

- [x] Dataset descriptions (including HOT OSM roads)
- [x] Schemas and data types
- [x] Missing values analysis
- [x] Uniqueness and identifier analysis
- [x] Cross-dataset observations
- [x] Data quality issues
- [x] No transformations applied (except HOT OSM highway filter documented in Section 3.1)

---

## 10. Follow-up — Road Network Topology (2026-06-24)

Phase 1 noted that HOT OSM road segments lack explicit node identifiers (Section 3.5). A subsequent step built a **proper routable graph** using OSMnx:

| Item | Detail |
|------|--------|
| Method | Geofabrik OSM extract + OSMnx `graph_from_xml(simplify=True)` |
| Highway filter | Same as Section 3.1: `primary`, `secondary`, `tertiary`, `unclassified` |
| Output nodes | 24,779 (intersections and dead-ends only) |
| Output edges | 62,345 (with `length_m`, `highway`, `start_node_id`, `end_node_id`) |
| T-junction handling | OSMnx native topology |

Full report: `docs/road_network_topology.md`  
Processed files: `data/processed/roads_hotosm/`  
Validation map: `output/south_sudan_road_topology_validation.html`

---

## 11. Phase 2 — Data Modeling ✅ (complete)

Phase 2 deliverables (2026-06-24):

1. **Health facility reconciliation** — 2,251 canonical facilities (`merge_health_facilities.py`)
2. **Network integration** — 2,094 POI connectors to OSMnx road graph (`integrate_network.py`)
3. **Schema design** — PostgreSQL + Neo4j models; benchmark queries Q1–Q5
4. **DB import layers** — `routing_edges.csv`, admin dimensions, logistical hubs

Progress: `docs/phase2_data_modeling.md`  
Schemas: `docs/phase2_relational_schema.md`, `docs/phase2_graph_schema.md`  
Next: **Phase 3** — database population (`AGENT_PHASE3.md`)
