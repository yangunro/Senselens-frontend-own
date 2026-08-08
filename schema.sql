-- =====================================================================
-- SenseLens — Database Schema (PostgreSQL, normalised to 3NF)
-- FIT5120 — Sensory-Friendly Urban Navigation
-- =====================================================================
-- Mirrors the project ERD (v3, zone-panel design). Identifiers are
-- double-quoted to preserve the PascalCase naming used in the ERD
-- diagram and DMP documentation — keep quoting consistent in all
-- queries against this schema.
--
-- Two deliberate amendments vs. the original ERD image, made to match
-- the prototype (see "Innovation" prototype screens):
--   1. SensoryIndicator is ENUM(Low, Medium, High) — the prototype's
--      route-selection screen shows three sensory tiers, not two.
--   2. UserPreference gains "LightSensitivity" — the prototype's
--      Settings screen has a Bright Light Sensitivity slider that the
--      original schema had no column to store.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- ENUM TYPES
-- ---------------------------------------------------------------------
CREATE TYPE sensitivity_level     AS ENUM ('Low', 'Medium', 'High');
CREATE TYPE sensory_indicator     AS ENUM ('Low', 'Medium', 'High');
CREATE TYPE route_type            AS ENUM ('Low', 'Balanced', 'Fast');
CREATE TYPE vehicle_mode          AS ENUM ('Train', 'Tram', 'Bus');
CREATE TYPE congestion_level      AS ENUM ('Smooth', 'StopGo', 'Congested', 'Severe');
CREATE TYPE occupancy_status      AS ENUM ('ManySeats', 'FewSeats', 'Standing', 'Full', 'NotAccepting');
CREATE TYPE refuge_category       AS ENUM ('Park', 'Library', 'CommunityCentre', 'Cafe', 'Other');
CREATE TYPE development_status    AS ENUM ('Proposed', 'Permit Issued', 'Under Construction', 'Completed');

-- =====================================================================
-- ZONE 1 — APP-NATIVE: Accounts & Saved Routes
-- Captured directly by the app. No external dependency.
-- =====================================================================

CREATE TABLE "User" (
    "UserID"        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "Email"         VARCHAR(255) NOT NULL UNIQUE,
    "DisplayName"   VARCHAR(100),
    "AuthProvider"  VARCHAR(50) NOT NULL,
    "CreatedAt"     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE "UserPreference" (
    "UserID"            UUID PRIMARY KEY REFERENCES "User"("UserID") ON DELETE CASCADE,
    "NoiseSensitivity"  sensitivity_level NOT NULL DEFAULT 'Medium',
    "CrowdThreshold"    SMALLINT NOT NULL DEFAULT 50 CHECK ("CrowdThreshold" BETWEEN 0 AND 100),
    "LightSensitivity"  sensitivity_level NOT NULL DEFAULT 'Medium', -- amendment #2, see header
    "AvoidConstruction" BOOLEAN NOT NULL DEFAULT TRUE,
    "ShowRefuges"       BOOLEAN NOT NULL DEFAULT TRUE,
    "HighContrastMode"  BOOLEAN NOT NULL DEFAULT FALSE,
    "ReducedMotion"     BOOLEAN NOT NULL DEFAULT FALSE
);

-- =====================================================================
-- ZONE 2 — ROUTE REQUEST & COMPUTED SENSORY SCORE
-- =====================================================================

CREATE TABLE "Route" (
    "RouteID"        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "OriginLat"      DECIMAL(9,6) NOT NULL,
    "OriginLng"      DECIMAL(9,6) NOT NULL,
    "DestLat"        DECIMAL(9,6) NOT NULL,
    "DestLng"        DECIMAL(9,6) NOT NULL,
    "RouteType"      route_type NOT NULL,
    "DistanceM"      INT,
    "EstDurationMin" SMALLINT
);

CREATE TABLE "SavedRoute" (
    "SavedRouteID" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "UserID"       UUID NOT NULL REFERENCES "User"("UserID") ON DELETE CASCADE,
    "RouteID"      UUID NOT NULL REFERENCES "Route"("RouteID") ON DELETE CASCADE,
    "Label"        VARCHAR(100),
    "SavedAt"      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Computed / derived — calculated by the backend from the feeds below,
-- not sourced directly.
CREATE TABLE "SensoryScore" (
    "ScoreID"                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "RouteID"                   UUID NOT NULL REFERENCES "Route"("RouteID") ON DELETE CASCADE,
    "SensoryIndicator"          sensory_indicator NOT NULL, -- amendment #1, see header
    "PedestrianDensityScore"    DECIMAL(4,2),
    "ConstructionExposureScore" DECIMAL(4,2),
    "LightingComfortScore"      DECIMAL(4,2),
    "ComputedAt"                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- ZONE 3 — OPEN DATA & COMPUTED: Pedestrian & Transit Sensor Network
-- =====================================================================

-- Open data feed — City of Melbourne Pedestrian Counting System
CREATE TABLE "SensorLocation" (
    "SensorID"          INT PRIMARY KEY,
    "SensorDescription" VARCHAR(150),
    "Lat"               DECIMAL(9,6) NOT NULL,
    "Lng"               DECIMAL(9,6) NOT NULL,
    "Status"            VARCHAR(20),
    "InstallationDate"  DATE
);

-- Open data feed — hourly pedestrian counts per sensor
CREATE TABLE "PedestrianCount" (
    "CountID"      BIGSERIAL PRIMARY KEY,
    "SensorID"     INT NOT NULL REFERENCES "SensorLocation"("SensorID") ON DELETE CASCADE,
    "DateTimeHour" TIMESTAMPTZ NOT NULL,
    "HourlyCount"  INT NOT NULL CHECK ("HourlyCount" >= 0),
    UNIQUE ("SensorID", "DateTimeHour")
);

-- Computed / derived — junction table: which sensors a route passes,
-- in order
CREATE TABLE "RouteSensor" (
    "RouteID"       UUID NOT NULL REFERENCES "Route"("RouteID") ON DELETE CASCADE,
    "SensorID"      INT NOT NULL REFERENCES "SensorLocation"("SensorID") ON DELETE CASCADE,
    "SequenceOrder" SMALLINT NOT NULL,
    PRIMARY KEY ("RouteID", "SensorID")
);

-- Open data feed — Transport Victoria GTFS-Realtime (polled ~30s;
-- source does not persist history, so the backend stores its own
-- snapshots here)
CREATE TABLE "TransitCongestionSignal" (
    "SignalID"         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "RouteID"          UUID NOT NULL REFERENCES "Route"("RouteID") ON DELETE CASCADE,
    "VehicleMode"      vehicle_mode NOT NULL,
    "CongestionLevel"  congestion_level NOT NULL,
    "OccupancyStatus"  occupancy_status NOT NULL,
    "OccupancyPct"     SMALLINT CHECK ("OccupancyPct" BETWEEN 0 AND 100),
    "ObservedAt"       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- ZONE 4 — OPEN DATA & CURATED: Spatial Context Layer
-- No persisted FK to Route — these are spatially joined at query time
-- via a lat/lng radius lookup.
-- =====================================================================

-- Curated / composite — synthesised from multiple City of Melbourne
-- datasets (parks, libraries, community centres) with light manual QA.
-- CuratedQuietScore is team-assessed, not sourced.
CREATE TABLE "RefugeLocation" (
    "RefugeID"         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "Name"             VARCHAR(100) NOT NULL,
    "Lat"              DECIMAL(9,6) NOT NULL,
    "Lng"              DECIMAL(9,6) NOT NULL,
    "Category"         refuge_category NOT NULL,
    "SourceDataset"    VARCHAR(80),
    "CuratedQuietScore" DECIMAL(3,1) CHECK ("CuratedQuietScore" BETWEEN 0 AND 10)
);

-- Open data feed — City of Melbourne Development Activity Monitor
-- (quarterly refresh)
CREATE TABLE "DevelopmentSite_Status" (
    "PropertyID"      INT PRIMARY KEY,
    "CLUE_SmallArea"  VARCHAR(50),
    "Status"          development_status NOT NULL,
    "DevelopmentType" VARCHAR(80),
    "Lat"             DECIMAL(9,6) NOT NULL,
    "Lng"             DECIMAL(9,6) NOT NULL
);

-- Open data feed — City of Melbourne Street Lights (Lux) dataset
-- (periodic snapshot)
CREATE TABLE "StreetLight_LuxLevel" (
    "LightID"  INT PRIMARY KEY,
    "Lat"      DECIMAL(9,6) NOT NULL,
    "Lng"      DECIMAL(9,6) NOT NULL,
    "LuxLabel" VARCHAR(50)
);

-- ---------------------------------------------------------------------
-- INDEXES — support the query patterns above (FK lookups + spatial
-- radius joins). Swap the Lat/Lng B-tree pairs for PostGIS + GiST if
-- the project adds the postgis extension later.
-- ---------------------------------------------------------------------
CREATE INDEX idx_savedroute_user            ON "SavedRoute" ("UserID");
CREATE INDEX idx_savedroute_route           ON "SavedRoute" ("RouteID");
CREATE INDEX idx_sensoryscore_route         ON "SensoryScore" ("RouteID");
CREATE INDEX idx_pedestriancount_sensor     ON "PedestrianCount" ("SensorID");
CREATE INDEX idx_routesensor_sensor         ON "RouteSensor" ("SensorID");
CREATE INDEX idx_transitsignal_route        ON "TransitCongestionSignal" ("RouteID");
CREATE INDEX idx_refuge_latlng              ON "RefugeLocation" ("Lat", "Lng");
CREATE INDEX idx_devsite_latlng             ON "DevelopmentSite_Status" ("Lat", "Lng");
CREATE INDEX idx_streetlight_latlng         ON "StreetLight_LuxLevel" ("Lat", "Lng");

COMMIT;
