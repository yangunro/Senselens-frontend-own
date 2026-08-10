# SenseLens

**Sensory-aware walking navigation for the Melbourne CBD.**

SenseLens plans walking routes that account for more than distance and time. It
ranks candidate routes by real-time crowd exposure, flags active construction,
reflects street lighting, surfaces nearby quiet/refuge spaces, and forecasts how
busy an area is likely to be over the next few hours — so people who are
sensitive to crowds, noise, and visual clutter can choose a calmer way through
the city.

> Monash University · Industry Experience Onboarding Project · Team Beyond-KPI · 2026

---

## Table of Contents

1. [What it does](#what-it-does)
2. [Live deployment](#live-deployment)
3. [System architecture](#system-architecture)
4. [Technology stack](#technology-stack)
5. [Repository structure](#repository-structure)
6. [How routing & sensory scoring works](#how-routing--sensory-scoring-works)
7. [Backend API reference](#backend-api-reference)
8. [Data model & database](#data-model--database)
9. [ETL pipeline](#etl-pipeline)
10. [Pedestrian forecast model](#pedestrian-forecast-model)
11. [Frontend](#frontend)
12. [Local development setup](#local-development-setup)
13. [Environment variables](#environment-variables)
14. [Cloud deployment](#cloud-deployment)
15. [Testing](#testing)
16. [Git & branching workflow](#git--branching-workflow)
17. [Development principles](#development-principles)
18. [Team](#team)

---

## What it does

Given an origin and a destination in the Melbourne CBD, SenseLens:

- **Generates multiple walking routes** and ranks them by a live **sensory
  score** (crowd exposure relative to currently-reporting pedestrian sensors).
- **Explains the trade-off** between routes in plain language
  (e.g. _"3 min longer, significantly more crowded"_).
- **Flags active construction** along each route, and — when the user opts in —
  steers the recommendation toward routes that pass fewer construction sites.
- **Reflects street lighting** along a route (_Well lit / Moderately lit /
  Dimly lit_), from the City of Melbourne street-light lux dataset.
- **Surfaces quiet/refuge spaces** (parks, libraries, quiet cafés) that lie on
  the way, and lets the user navigate straight to one.
- **Forecasts crowding** 1–3 hours ahead, per sensor, from a model trained on
  ~1.23M historical hourly observations.
- **Shows a live crowd heatmap** on the map, plus a per-sensor "now / 1h / 2h /
  3h" toggle.
- **Saves routes** for quick recall, and hands off to the phone's native maps
  app for turn-by-turn with voice guidance.

Everything is driven by **real data**. When a dataset can't support an answer
(e.g. no sensor is near enough to score a route), the API returns an honest
"insufficient data" state rather than a fabricated number.

---

## Live deployment

| Layer | Platform | URL |
|---|---|---|
| Frontend (Vue) | Render (static site) | `https://senselens.onrender.com` and `https://senselense-duk4.onrender.com` |
| Backend (FastAPI) | FastAPI Cloud | `https://senselense.fastapicloud.dev` |
| Database | Supabase (PostgreSQL, Session Pooler) | private |

API docs (Swagger) are served at `/docs` on the backend, and the OpenAPI spec at
`/openapi.json`.

---

## System architecture

```text
                 City of Melbourne Open Data  +  Transport Victoria GTFS-Realtime
                                     │
                                     ▼
                     ETL pipelines (etl/*, scheduled via GitHub Actions)
                                     │
                                     ▼
                       Supabase PostgreSQL (Session Pooler)
                                     │
                                     ▼
   Mapbox Directions API  ─────►  FastAPI backend (app/*)  ◄─────  offline-trained
   (walking geometry)              route generation +                forecast model
                                   sensory scoring +                (scripts/, loaded
                                   spatial matching                  at request time)
                                     │
                                     ▼
                          REST API  (/routes, /refuges, …)
                                     │
                                     ▼
                        Vue 3 frontend (senselens-frontend/)
                          Render static site + Mapbox GL JS
```

**Data flow**

1. Public datasets are pulled from City of Melbourne Open Data (and Transport
   Victoria GTFS-Realtime) by the ETL pipelines.
2. ETL validates, cleans, standardises, and UPSERTs into Supabase PostgreSQL.
   GitHub Actions run the pipelines on schedules (see [ETL pipeline](#etl-pipeline)).
3. The FastAPI backend reads the shared database and, on a route request, calls
   the **Mapbox Directions API** to compute walking geometry, then scores and
   ranks routes against the live sensor/construction/lighting/refuge data.
4. The Vue frontend consumes the REST API and renders the interactive map,
   route cards, refuge list, heatmap, and forecast toggles with **Mapbox GL JS**.

---

## Technology stack

**Backend** — Python 3.13 · FastAPI · SQLAlchemy · Psycopg 3 · Pydantic ·
Uvicorn · `requests` · `polyline` · `gtfs-realtime-bindings`

**Database** — PostgreSQL on Supabase, accessed through the Supabase Session
Pooler.

**Routing / maps** — **Mapbox Directions API** (server-side, walking profile)
for route geometry and turn-by-turn steps; **Mapbox GL JS** and **Mapbox
Geocoding/Search** on the frontend for map rendering and address autocomplete.

> Note: route *computation* moved from the Google Routes API to Mapbox
> Directions. Mapbox is now the single mapping provider for both display and
> routing. The frontend still deep-links to Google/Apple Maps for optional
> native turn-by-turn hand-off — that needs no API key.

**Machine learning** — per-sensor linear regression implemented in **pure
Python** (least squares, standard-library `math` only — no NumPy or scikit-learn
dependency). Trained offline and committed as a JSON artifact that the backend
loads (and caches) at request time.

**Frontend** — Vue 3 (`<script setup>`) · Vue Router · Vite · Mapbox GL JS.

**Cloud** — Render (frontend static site) · FastAPI Cloud (backend) ·
Supabase (database) · GitHub Actions (ETL scheduling).

---

## Repository structure

```text
SenseLens/
│
├── README.md                     # this file
├── schema.sql                    # canonical PostgreSQL schema (ERD, 3NF)
├── requirements.txt              # backend Python dependencies
├── render.yaml                   # Render static-site config for the frontend
├── .env.example                  # backend environment-variable template
├── .python-version               # pins Python 3.13 for cloud builds
│
├── app/                          # FastAPI backend
│   ├── main.py                   # app, CORS, routers, /, /health, /users
│   ├── database.py               # SQLAlchemy engine + session (DATABASE_URL/DB_*)
│   ├── models.py                 # SQLAlchemy ORM models
│   │
│   ├── routers/                  # HTTP layer (endpoints, validation)
│   │   ├── cbd_status.py         # GET /cbd-status
│   │   ├── preferences.py        # GET/POST /preferences
│   │   ├── pedestrian.py         # GET /pedestrian-counts/latest, /pedestrian-forecasts
│   │   ├── refuges.py            # GET /refuges
│   │   ├── routes.py             # /routes and /routes/{id}/* family
│   │   └── saved_routes.py       # GET/POST/DELETE /saved-routes
│   │
│   └── services/                 # business logic + SQL
│       ├── mapbox_routes_service.py   # Mapbox Directions + alternative synthesis
│       ├── routes_service.py          # route generation, scoring, sorting, caching
│       ├── route_analysis_service.py  # geometry, sensor/construction/lighting/refuge matching, percentile scoring
│       ├── dynamic_route_store.py     # in-memory LRU cache of generated routes
│       ├── construction_service.py    # active development-site lookup
│       ├── lighting_service.py        # street-light lux lookup by bounding box
│       ├── refuges_service.py         # refuge-location lookup
│       ├── pedestrian_service.py      # latest live sensor snapshot
│       ├── forecast_service.py        # per-sensor crowd prediction (model at request time)
│       ├── preferences_service.py     # user sensory preferences
│       ├── cbd_status_service.py      # aggregate CBD activity snapshot
│       └── saved_routes_service.py    # persist/list/delete saved routes
│
├── etl/                          # ETL pipelines (City of Melbourne + Transit)
│   ├── README.md
│   ├── client.py                 # Open Data API client (ODS Explore v2.1)
│   ├── transit_client.py         # Transport Victoria GTFS-Realtime client
│   ├── repository.py             # UPSERT helpers into Supabase
│   ├── validators.py             # validation / cleaning
│   ├── geo.py, cbd_boundary.py   # CBD bounding-box helpers
│   ├── initialize_checkpoint.py  # ETL checkpoint bootstrap
│   ├── sync_sensor_locations.py  # SensorLocation
│   ├── sync_pedestrian_live.py   # live PedestrianCount (every 15 min)
│   ├── sync_pedestrian_history.py# PedestrianHourlyHistory (checkpointed)
│   ├── sync_development.py        # DevelopmentSite_Status
│   ├── sync_streetlights.py       # StreetLight_LuxLevel
│   ├── sync_refuge.py             # RefugeLocation
│   └── sync_transit_congestion.py# TransitCongestionSignal (every 5 min)
│
├── scripts/                      # offline model training / validation
│   ├── train_pedestrian_forecast.py
│   └── validate_pedestrian_forecast.py
│
├── senselens_pipeline/           # standalone scoring/pipeline experiments
│   ├── pipeline.py, scoring.py, database.py
│
├── migrations/                   # reviewed, hand-applied SQL migrations
│   ├── 001_add_route_geometry.sql
│   └── README.md
│
├── .github/workflows/            # scheduled ETL (GitHub Actions)
│   ├── etl-live.yml              # */15 min  — live pedestrian counts
│   ├── etl-transit.yml           # */5 min   — transit congestion
│   ├── etl-daily.yml             # 03:00 UTC — history, development, streetlights
│   └── etl-weekly.yml            # Mon 03:00 — sensor locations, refuges
│
├── tests/                        # pytest suite (backend)
│   ├── test_routes_api.py
│   ├── test_routes_service.py
│   ├── test_route_analysis_service.py
│   ├── test_mapbox_routes_service.py
│   └── test_forecast_service.py
│
└── senselens-frontend/           # Vue 3 frontend (see “Frontend”)
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── .env.example
    └── src/
        ├── main.js, App.vue, style.css
        ├── router/index.js
        ├── pages/            # Home, Routes, Map, Refuges, SavedRoutes, HowItWorks, Setting, NotFound
        ├── components/       # BottomNav, Icon, PageShell, ProgressBar, SegmentedTabs, SkeletonBlock
        ├── composables/      # usePreferences, useMapboxSearch
        └── services/         # http, routes, map, refuges, preferences, geolocation,
                              #   geocode, mapbox, polyline, routeProgress,
                              #   externalNavigation, savedRoutes, home
```

---

## How routing & sensory scoring works

This is the core of the app. A request to `GET /routes?destination=…` with
origin/destination coordinates flows through the following pipeline
(`app/services/routes_service.py` orchestrates it):

### 1. Route geometry — Mapbox + synthesised alternatives

`mapbox_routes_service.get_mapbox_routes()` calls the Mapbox Directions API
(walking profile). Mapbox's walking profile returns **only one route** even with
`alternatives=true`, which would leave nothing to rank. So when fewer than three
routes come back, the service **synthesises genuine alternatives**: it routes
through waypoints offset perpendicular to the straight origin→destination line,
nudging the path onto parallel streets. Because the CBD is a grid, these are
real, walkable options — not invented geometry.

- Variants are de-duplicated geometrically (symmetric average nearest-neighbour
  distance) so near-identical paths don't appear twice.
- A detour cap rejects any variant more than 1.8× the direct route's length.
- The two offset requests run in parallel.

### 2. Sensory (crowd) scoring — interpolated percentile

`route_analysis_service.analyse_route()` decodes each route's polyline and:

- Finds live pedestrian sensors within ~150 m of the path.
- Computes a distance-weighted average of their per-minute counts.
- Converts that to a **percentile against all currently-reporting sensors**,
  using **linear interpolation** across the empirical distribution. (A plain
  step-rank collapses genuinely different routes to the same number when only a
  handful of sensors are reporting a lumpy distribution; interpolation keeps
  distinct routes distinct.)

Percentile → level:

| Score | Level |
|---|---|
| `< 35` | LOW SENSORY |
| `35 – 64` | MEDIUM SENSORY |
| `≥ 65` | HIGH SENSORY |
| `None` (no nearby sensor) | INSUFFICIENT DATA |

### 3. Construction & lighting factors

- **Construction** — `construction_service` returns active
  (`Under Construction`) development sites; routes within ~75 m of one are
  flagged with a count.
- **Lighting** — `lighting_service` fetches street-lights in the route's
  bounding box (one query covering all alternatives); the average lux along the
  path yields a comfort label: `< 10` Dimly lit, `< 30` Moderately lit, else
  Well lit. (Bands are calibrated to Melbourne's own lux distribution.)

### 4. Refuge (quiet-space) matching

`route_analysis_service.refuges_near_route()` matches curated refuge locations
(parks, libraries, quiet cafés) that lie within the corridor of a route, powering
`/routes/{id}/quiet-spaces` and the "on the way" badges in the app.

### 5. Ranking

Routes are sorted by an effective score. When the user has **Avoid construction
zones** enabled, each construction site a route passes adds a proportional
penalty (8 points/site) to its ranking score — nudging the recommendation toward
routes with fewer sites without letting one site override a much calmer path.
Insufficient-data routes always sink below scored routes. The recommended card
explains *why* it was chosen ("Lowest measured crowd exposure" / "Fewer
construction zones" / "Avoids active construction").

### 6. Caching & follow-ups

Generated routes are held in a 100-entry in-memory LRU cache
(`dynamic_route_store`). The follow-up endpoints (`/routes/{id}`,
`/routes/{id}/alerts`, `/routes/{id}/forecast`, `/routes/{id}/quiet-spaces`) read
from that cache, so the polyline, steps, and scoring don't need recomputation.
Saving a route persists a real `Route` row first (so the `SavedRoute` foreign key
is valid), since live routes otherwise exist only in the cache.

---

## Backend API reference

Base URL (production): `https://senselense.fastapicloud.dev`

### System & users

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | API name / version / status |
| `GET` | `/health` | Health check |
| `GET` | `/users` | List users |
| `POST` | `/users` | Create a user (`Email`, `DisplayName`, `AuthProvider`) |

### Preferences, CBD status, pedestrian data

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/preferences` | Sensory preferences (sliders + toggles) |
| `POST` | `/preferences` | Save/update sensory preferences |
| `GET` | `/cbd-status` | Aggregate current CBD activity snapshot |
| `GET` | `/pedestrian-counts/latest` | Latest live per-sensor readings + coordinates |
| `GET` | `/pedestrian-forecasts?horizonHours=3` | Map-wide per-sensor crowd predictions (1–3 h) |

### Refuges & saved routes

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/refuges` | All refuge locations |
| `GET` | `/saved-routes` | List saved routes |
| `POST` | `/saved-routes` | Save a route (`routeId`, `label`) |
| `DELETE` | `/saved-routes/{saved_route_id}` | Delete a saved route |

### Routes

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/routes` | Stored routes (no destination) |
| `GET` | `/routes?destination=…&originLat=…&originLng=…` | **Generate live scored walking routes** |
| `GET` | `/routes/{route_id}` | Full route detail (polyline, steps, factors) |
| `GET` | `/routes/{route_id}/alerts` | Alerts for a route (high crowd / construction) |
| `GET` | `/routes/{route_id}/forecast` | Next 1–3 h crowd forecast for the route |
| `GET` | `/routes/{route_id}/quiet-spaces` | Refuge spaces on/near the route |

**Route generation query parameters**

| Param | Alias | Notes |
|---|---|---|
| `destination` | | Free-text label (required to generate) |
| `originLat`, `originLng` | | Required when generating — the browser's current location or a chosen start |
| `destinationLat`, `destinationLng` | | Optional but recommended; must be supplied together |
| `avoidConstruction` | | `true` to weight construction into ranking |

Example:

```text
GET /routes?destination=Queen%20Victoria%20Market&originLat=-37.8183&originLng=144.9671&destinationLat=-37.8076&destinationLng=144.9568&avoidConstruction=true
```

Each returned route includes: `id`, `tag`, `name`, `level`, `levelLabel`,
`sensoryScore`, `duration`/`durationMinutes`, `description`, `footnote`,
`recommended`, `hasActiveConstruction`, `constructionSitesNearby`, `averageLux`,
`lightingComfort`, and a `factors[]` list (crowd / construction / lighting chips).

**Honest empty / unavailable states**

- `/routes`, `/refuges`, `/saved-routes` may return `[]` when the relevant data
  legitimately has nothing to report.
- `/routes/{id}/forecast` returns `404` when no forecast applies, and `503` if
  the model artifact is missing/incompatible.
- A route with no nearby sensor returns `sensoryScore: null` and
  `INSUFFICIENT DATA` rather than a made-up score.

---

## Data model & database

PostgreSQL on Supabase. The canonical schema is [`schema.sql`](schema.sql),
normalised to 3NF, with PascalCase, double-quoted identifiers mirroring the
project ERD. Keep quoting consistent in all queries.

The schema is organised into four zones:

- **Zone 1 — App-native:** `User`, `UserPreference`, `SavedRoute`
- **Zone 2 — Route & computed score:** `Route`, `SensoryScore`
- **Zone 3 — Sensor network:** `SensorLocation`, `PedestrianCount`,
  `RouteSensor`, `TransitCongestionSignal`
- **Zone 4 — Spatial context (radius-joined at query time, no FK to Route):**
  `RefugeLocation`, `DevelopmentSite_Status`, `StreetLight_LuxLevel`

In addition to the ERD tables, the live database holds
`PedestrianHourlyHistory` (the historical training corpus) and an
`ETLCheckpoint` table used for incremental loading.

**Approximate live data volumes** (feeds refresh on schedule, so these drift):

| Table | Rows | Source |
|---|---:|---|
| `PedestrianHourlyHistory` | ~1,225,000 | City of Melbourne — historical pedestrian counts |
| `StreetLight_LuxLevel` | 12,378 | City of Melbourne — street-light lux |
| `DevelopmentSite_Status` | 1,169 | City of Melbourne — development activity |
| `RefugeLocation` | 740 | Curated from CoM parks/libraries/community datasets |
| `SensorLocation` | 134 | City of Melbourne — pedestrian sensor locations |
| `PedestrianCount` | ~640 | City of Melbourne — live per-sensor counts |

**Connectivity** — the backend connects through the **Supabase Session Pooler**
(the direct database host was not reliably reachable from all environments).
Configure with either `DATABASE_URL` or the `DB_*` variables (see
[Environment variables](#environment-variables)).

---

## ETL pipeline

Each pipeline extracts from an open-data source, validates and cleans, then
UPSERTs into Supabase (idempotent, duplicate-safe). Historical pedestrian
loading is **checkpoint-based**: `ETLCheckpoint` records the last loaded date, so
only missing dates are fetched rather than re-downloading the full corpus.

Pipelines are scheduled with **GitHub Actions** (each also supports manual
`workflow_dispatch`):

| Workflow | Schedule (UTC) | Runs |
|---|---|---|
| `etl-live.yml` | every 15 min | `sync_pedestrian_live` |
| `etl-transit.yml` | every 5 min | `sync_transit_congestion` |
| `etl-daily.yml` | daily 03:00 | `sync_pedestrian_history`, `sync_development`, `sync_streetlights` |
| `etl-weekly.yml` | Mon 03:00 | `sync_sensor_locations`, `sync_refuge` |

Run any pipeline manually:

```bash
python -m etl.sync_pedestrian_live
python -m etl.sync_development
python -m etl.sync_refuge
```

See [`etl/README.md`](etl/README.md) for pipeline-specific detail.

> **Known external blocker:** `sync_transit_congestion` needs a Transport
> Victoria GTFS-Realtime *Subscription Key*. The data-platform token type issued
> so far is not the correct credential, so `TransitCongestionSignal` is not yet
> populated. The pipeline and schema are ready for it.

---

## Pedestrian forecast model

`/routes/{id}/forecast` and `/pedestrian-forecasts` are backed by a **per-sensor
linear regression**, implemented in pure Python (least squares, no external ML
library), trained offline from `PedestrianHourlyHistory` (~1.23M hourly
observations, 2025-01-01 → 2026-08-09). Features: time trend, hour-of-day,
day-of-week, weekend flag. Sensors without enough history fall back to a global
regression. The model is stored as a committed **JSON artifact** that FastAPI
loads (and caches via `lru_cache`) — the API never retrains per request.

Rounded prediction bands: **Low 0–5**, **Medium 6–14**, **High 15+** pedestrians
per minute.

Retrain after refreshing history:

```bash
python -m scripts.train_pedestrian_forecast
python -m scripts.validate_pedestrian_forecast
```

If the artifact is absent or incompatible, forecast endpoints return `503`.

---

## Frontend

Vue 3 (`<script setup>`) + Vue Router + Vite, rendered with Mapbox GL JS.
Deployed as a Render static site.

**Pages** (`src/pages/`)

| Route | Page | Purpose |
|---|---|---|
| `/` | `Home.vue` | Destination + optional origin search (Mapbox autocomplete) |
| `/routes` | `Routes.vue` | Ranked route cards with sensory badge, factors, trade-off notes |
| `/map` | `Map.vue` | Interactive map: route line, sensor markers, crowd heatmap, forecast toggle, live progress, save/navigate |
| `/refuges` | `Refuges.vue` | Nearby refuges, "on the way" badges, one-tap navigate |
| `/saved-routes` | `SavedRoutes.vue` | Saved routes (tap re-generates a fresh live route) |
| `/how-it-works` | `HowItWorks.vue` | Honest explanation of what the score does and doesn't use |
| `/settings` | `Setting.vue` | Preferences (placeholder) |
| `*` | `NotFound.vue` | 404 |

**Services** (`src/services/`) wrap the backend API with a mock fallback:
`withApiFallback()` tries the real backend when `VITE_API_BASE` is set and only
falls back to mock data when it isn't — so a real outage surfaces as an error
state, never as fake data. Key modules: `routes.js`, `map.js`, `refuges.js`,
`preferences.js`, `savedRoutes.js`, `geolocation.js`, `geocode.js`,
`routeProgress.js` (foreground turn-by-turn estimation),
`externalNavigation.js` (native maps hand-off), `mapbox.js`, `polyline.js`.

**State** — a shared reactive `usePreferences` composable keeps sensory
preferences consistent app-wide; cross-page route context (e.g. the active route
for "on the way" refuge detection) is passed via `sessionStorage`.

**Theme** — a single light theme, pinned with `color-scheme: light` so browsers
with "auto dark mode for web content" don't recolor the UI.

---

## Local development setup

### Backend

```bash
git clone <repository-url>
cd SenseLens

python -m venv .venv
source .venv/bin/activate          # macOS/Linux

pip install -r requirements.txt

cp .env.example .env               # then fill in real values
fastapi dev app/main.py
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

Python is pinned to **3.13** via `.python-version` so cloud builds don't pick a
newer, possibly-incompatible interpreter.

### Frontend

```bash
cd senselens-frontend
npm install

cp .env.example .env               # set VITE_API_BASE + VITE_MAPBOX_ACCESS_TOKEN
npm run dev                        # http://localhost:5173
npm run build                      # production build → dist/
```

---

## Environment variables

### Backend (`.env`, or the cloud platform's secrets)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Full PostgreSQL connection URL **(or use the `DB_*` set below)** |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` | Supabase Session Pooler settings |
| `MAPBOX_ACCESS_TOKEN` | **Server-side** Mapbox token for the Directions API (route computation) |
| `FRONTEND_ORIGIN` | Comma-separated CORS origins, no trailing slashes |

### Frontend (`senselens-frontend/.env`)

| Variable | Purpose |
|---|---|
| `VITE_API_BASE` | Backend base URL, no trailing slash |
| `VITE_MAPBOX_ACCESS_TOKEN` | Mapbox token for map rendering + address search |

> **Two different Mapbox tokens by role:** the backend's `MAPBOX_ACCESS_TOKEN`
> (Directions API) is server-side and must never be exposed through a `VITE_*`
> variable. The frontend's `VITE_MAPBOX_ACCESS_TOKEN` is public by design (it
> ships in the browser bundle) and is scoped to map display and search.

Never commit `.env`. Never expose database credentials to the frontend.

---

## Cloud deployment

### Frontend — Render (static site)

Deploys from `senselens-frontend/` on `main`. [`render.yaml`](render.yaml) at the
repo root declares the build command, publish path, SPA rewrite, and required env
vars so the deploy is reproducible by anyone on the team.

- Build: `npm install && npm run build` · Publish: `dist`
- SPA rewrite: `/* → /index.html` (so `/map`, `/refuges`, … don't 404)
- Secrets (set in Render): `VITE_API_BASE`, `VITE_MAPBOX_ACCESS_TOKEN`

### Backend — FastAPI Cloud

Auto-deploys from GitHub `main`. Configure secrets in the FastAPI Cloud
dashboard: the database connection (`DATABASE_URL` or `DB_*`),
`MAPBOX_ACCESS_TOKEN`, and `FRONTEND_ORIGIN`. Local `.env` changes do **not**
propagate to the cloud — set them in the platform.

A deploy is healthy when `/health` and `/docs` respond publicly, Supabase
connectivity works from the cloud, and the Render frontend can reach the backend
without CORS errors.

---

## Testing

Backend tests use `pytest`:

```bash
.venv/bin/python -m pytest tests/ -q
```

Coverage includes route generation & ranking, the interpolated percentile
scorer, geometry/sensor matching, the Mapbox alternative-synthesis (HTTP mocked),
the routes API contract, and the forecast service.

---

## Git & branching workflow

- **`main`** — full stack (backend `app/`, `etl/`, frontend `senselens-frontend/`).
  Backend and the FastAPI Cloud + Render deployments track this branch.
- **`wenlu`** — the actively-maintained **frontend** branch; it contains no
  backend directory.

Because the two branches carry different subsets of the tree, the convention is:

- **Frontend changes** land on `wenlu` and are cherry-picked into `main` (and
  vice-versa) so both stay in sync.
- **Backend changes** are `main`-only (`wenlu` has no `app/`), so they need no
  cherry-pick.

Yu Zhang's `fastapi-google-map`, `google-map-integration`, and
`forecast-model-backend` branches hold earlier integration work and are not part
of the current deploy path.

---

## Development principles

- **No fabricated data.** If the underlying data can't answer, the API returns an
  empty or "insufficient data" response rather than inventing values.
- **Separation of responsibilities.** ETL prepares external data · Supabase
  stores it · FastAPI routers handle HTTP while services hold business logic and
  SQL · Vue renders the UI · Mapbox handles map display and route geometry.
- **Stable API contracts.** Frontend-facing contracts are kept stable while the
  internals evolve.
- **Secure configuration.** Secrets live in environment variables, never in the
  repo; database credentials stay server-side only; rotate anything exposed.

---

## Team

**SenseLens** — Monash University, Industry Experience Onboarding Project,
Team Beyond-KPI, 2026.
