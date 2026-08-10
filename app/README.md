# SenseLens

## Overview

**SenseLens** is a sensory-aware navigation platform designed to support more comfortable walking experiences through Melbourne CBD.

Traditional navigation applications generally optimise routes based on distance and travel time. SenseLens aims to extend this by considering environmental and sensory conditions that may affect a person's walking experience.

The platform is designed to combine:

- Live pedestrian activity
- Historical pedestrian activity
- Construction and development activity
- Street-light information
- Quiet/refuge locations when available
- User sensory preferences
- Walking-route information

The long-term goal is to recommend walking routes based not only on distance and duration, but also on the sensory preferences of the user.

> **Current status:** The database, Supabase migration, ETL foundation, FastAPI backend, core REST APIs, and frontend API contracts have been implemented. Backend cloud deployment and frontend integration are currently in progress. Dynamic sensory-aware route generation and recommendation are the next major development phase.

---

## System Architecture

The current high-level architecture is:

```text
Melbourne Open Data
        │
        ▼
   ETL Pipelines
        │
        ▼
Supabase PostgreSQL
        │
        ▼
  FastAPI Backend
        │
        ▼
    Vue Frontend
```

The production architecture is being configured as:

```text
City of Melbourne Open Data
          │
          ▼
     ETL Pipelines
          │
          ▼
Supabase PostgreSQL
   Session Pooler
          │
          ▼
     FastAPI Cloud
          │
          ▼
     Vue Frontend
        Render
```

### Data Flow

1. Public datasets are retrieved from City of Melbourne data sources.
2. ETL pipelines extract, validate, clean, standardise, and transform the data.
3. Processed data is stored in PostgreSQL hosted on Supabase.
4. FastAPI connects to the shared Supabase PostgreSQL database.
5. REST API endpoints expose application data to the frontend.
6. The Vue frontend consumes the APIs to build the SenseLens user experience.
7. Future routing functionality will introduce candidate walking routes that can be evaluated against environmental and sensory data.

---

## Technology Stack

### Backend

- Python 3.13
- FastAPI
- SQLAlchemy
- Psycopg
- Pydantic
- Uvicorn

### Database

- PostgreSQL
- Supabase
- Supabase Session Pooler

### ETL

- Python
- Requests
- City of Melbourne Open Data APIs
- Incremental loading
- Checkpoint-based synchronisation
- UPSERT-based database loading

### Frontend

- Vue
- JavaScript
- Google Maps integration being developed by the frontend/integration team

### Cloud Infrastructure

- **Render** — Vue frontend
- **FastAPI Cloud** — backend deployment
- **Supabase** — PostgreSQL database

---

# Repository Structure

The backend follows a router/service architecture.

```text
SenseLens/
│
├── README.md
├── requirements.txt
├── .python-version
├── .gitignore
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   │
│   ├── routers/
│   │   ├── cbd_status.py
│   │   ├── preferences.py
│   │   ├── refuges.py
│   │   ├── routes.py
│   │   └── saved_routes.py
│   │
│   └── services/
│       ├── cbd_status_service.py
│       ├── preferences_service.py
│       ├── refuges_service.py
│       ├── routes_service.py
│       └── saved_routes_service.py
│
├── etl/
│   ├── README.md
│   ├── client.py
│   ├── repository.py
│   ├── validators.py
│   └── ...
│
└── senselens-frontend/
    └── ...
```

The repository structure may continue to evolve as frontend integration, routing, and production deployment are completed.

---

# Backend Architecture

The FastAPI backend follows a layered architecture:

```text
HTTP Request
      │
      ▼
FastAPI Router
      │
      ▼
Service Layer
      │
      ▼
SQLAlchemy / SQL
      │
      ▼
Supabase PostgreSQL
```

## Routers

Routers are responsible for:

- Defining HTTP endpoints
- Receiving requests
- Validating parameters
- Calling service functions
- Returning API responses
- Returning appropriate HTTP status codes

## Services

Services are responsible for:

- Business logic
- Database queries
- Data transformation
- Preparing frontend-friendly responses

This keeps HTTP handling separate from database and application logic.

---

# Current Backend APIs

## System

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/` | API information/status | Implemented |
| GET | `/health` | Backend health check | Implemented |

---

## Users

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/users` | Retrieve users | Implemented |
| POST | `/users` | Create a user | Implemented |

---

## User Preferences

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/preferences` | Retrieve sensory preferences | Implemented |
| POST | `/preferences` | Save/update sensory preferences | Implemented |

---

## CBD Status

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/cbd-status` | Retrieve current CBD sensory/activity information | Implemented |

---

## Refuge Locations

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/refuges` | Retrieve available refuge locations | Implemented |

The endpoint is ready, but the `RefugeLocation` table is not currently populated with verified refuge data.

The backend does **not fabricate refuge locations**.

---

## Routes

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/routes` | Retrieve stored routes | Implemented |
| GET | `/routes/{route_id}` | Retrieve a specific route | Implemented |
| GET | `/routes/{route_id}/alerts` | Retrieve route alerts | Implemented |
| GET | `/routes/{route_id}/forecast` | Retrieve 1-3 hour route crowd predictions | Implemented |
| GET | `/pedestrian-forecasts?horizonHours=3` | Retrieve map-wide per-sensor crowd predictions | Implemented |
| GET | `/routes/{route_id}/quiet-spaces` | Retrieve quiet/refuge spaces associated with a route | API contract implemented |

### Route Forecast

The endpoint:

```text
GET /routes/{route_id}/forecast
```

returns per-sensor pedestrian predictions for the next 1, 2, and 3 hours.
The model is a per-sensor linear regression trained offline from
`PedestrianHourlyHistory`; the committed artifact is loaded by FastAPI at
request time, so the API does not retrain the model for every request.

The current artifact was trained from 1,225,895 hourly observations covering
2025-01-01 through 2026-08-09. It predicts pedestrians per minute from time
trend, hour-of-day, day-of-week, and weekend features. Sensors without enough
history use the global fallback regression.

The response preserves the fields consumed by the Map page and also provides
detailed forecasts and alerts:

```json
{
  "routeId": "...",
  "sensoryIndicator": "HIGH SENSORY",
  "level": "high",
  "basis": "...",
  "horizonHours": 3,
  "hasPredictiveAlert": true,
  "forecasts": [
    {
      "hoursAhead": 1,
      "forecastAt": "...",
      "maximumPredictedCountPerMinute": 21,
      "sensors": []
    }
  ],
  "alerts": []
}
```

The rounded prediction bands are Low 0-5, Medium 6-14, and High 15+.
For map-wide prediction markers, use:

```text
GET /pedestrian-forecasts?horizonHours=3
```

If no sensory/forecast information is available, the API returns:

```json
{
  "detail": "Forecast data not available for this route"
}
```

with:

```text
HTTP 404
```

If the model artifact is absent or incompatible, the API returns HTTP 503.
Retrain it after refreshing historical data with:

```text
python -m scripts.train_pedestrian_forecast
```

---

## Route Quiet Spaces

The endpoint:

```text
GET /routes/{route_id}/quiet-spaces
```

is implemented.

At the current development stage it may return:

```json
[]
```

This is intentional because:

- `RefugeLocation` has not yet been populated with verified refuge data.
- Route-to-refuge spatial matching has not yet been implemented.

SenseLens does not fabricate quiet-space matches simply to populate the response.

Once refuge data and route geometry are available, this endpoint can identify suitable spaces near a candidate walking route.

---

# Saved Routes

The Saved Routes API now supports the basic create/read/delete lifecycle.

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/saved-routes` | Retrieve saved routes | Implemented |
| POST | `/saved-routes` | Save a route | Implemented |
| DELETE | `/saved-routes/{saved_route_id}` | Delete a saved route | Implemented |

## Saving a Route

Example:

```text
POST /saved-routes
```

Request:

```json
{
  "routeId": "ROUTE_UUID",
  "label": "Home to Campus"
}
```

The `RouteID` must correspond to a valid route in the database.

If a nonexistent route is supplied, the database foreign-key relationship prevents an invalid saved route from being created and the API returns:

```json
{
  "detail": "Route not found"
}
```

with HTTP `404`.

---

## Deleting a Saved Route

Example:

```text
DELETE /saved-routes/{saved_route_id}
```

If the saved route exists, it is removed from the database.

If it does not exist, the API returns:

```json
{
  "detail": "Saved route not found"
}
```

with HTTP `404`.

---

# Empty API Responses

Some endpoints may currently return:

```json
[]
```

This does not necessarily indicate an API failure.

For example:

```text
GET /routes
GET /refuges
GET /saved-routes
GET /routes/{route_id}/quiet-spaces
```

can legitimately return empty arrays while their underlying database tables contain no applicable records.

The backend returns the actual database state rather than artificial demonstration data.

---

# User Preferences

SenseLens currently supports sensory preferences that can later influence route recommendations.

## Sensitivity Controls

```text
Crowd sensitivity
Noise sensitivity
Light sensitivity
```

The frontend represents sensitivity using:

```text
0 = Low
1 = Medium
2 = High
```

Noise and light sensitivity are mapped to the corresponding database representation.

## Preference Toggles

Current toggles include:

- Avoid construction zones
- Show refuge spaces
- High contrast mode

Preferences can be retrieved with:

```text
GET /preferences
```

and updated with:

```text
POST /preferences
```

---

# Database

SenseLens uses PostgreSQL hosted on **Supabase**.

The database was originally developed locally and subsequently migrated to the shared Supabase environment so all application services can use the same database.

## Main Database Areas

The database supports:

- Users
- User preferences
- Pedestrian sensors
- Current pedestrian counts
- Historical pedestrian counts
- Development/construction activity
- Street-light information
- Routes
- Route-to-sensor relationships
- Saved routes
- Sensory scores
- Refuge locations
- Transit congestion signals
- ETL checkpoints

Example tables include:

```text
User
UserPreference
SensorLocation
PedestrianCount
PedestrianHourlyHistory
DevelopmentSite_Status
StreetLight_LuxLevel
Route
RouteSensor
SavedRoute
SensoryScore
RefugeLocation
TransitCongestionSignal
ETLCheckpoint
```

---

# Supabase Database Connectivity

The backend now uses the **Supabase Session Pooler** for PostgreSQL connectivity.

This was selected because the direct Supabase database hostname was not reliably reachable from the local development environment.

The application uses environment variables:

```env
DB_USER=postgres.<PROJECT_REF>
DB_PASSWORD=<YOUR_DATABASE_PASSWORD>
DB_HOST=<SUPABASE_SESSION_POOLER_HOST>
DB_PORT=5432
DB_NAME=postgres
```

Real credentials must never be committed to Git.

The database connection is constructed in the backend using these environment variables.

The Session Pooler connection has been successfully tested from the local development environment.

---

# ETL Pipeline

The ETL layer retrieves and prepares environmental information used by SenseLens.

The general process is:

```text
City of Melbourne API
        │
        ▼
      Extract
        │
        ▼
Validate / Clean
        │
        ▼
   Standardise
        │
        ▼
    Transform
        │
        ▼
      UPSERT
        │
        ▼
Supabase PostgreSQL
```

## Implemented ETL Features

The ETL framework includes:

- API extraction
- Pagination
- Data transformation
- Validation
- Missing-value checks
- Non-negative pedestrian-count validation
- Standardised field mappings
- UPSERT operations
- Duplicate protection
- Incremental loading
- Historical loading
- ETL checkpoints
- Error handling
- Pedestrian-data ingestion
- Development/construction-data ingestion

---

# Historical Pedestrian Loading

Historical pedestrian data uses checkpoint-based incremental loading.

```text
ETLCheckpoint
      │
      ▼
Last Successfully Loaded Date
      │
      ▼
Determine Missing Dates
      │
      ▼
City of Melbourne API
      │
      ▼
Validate + Transform
      │
      ▼
UPSERT
      │
      ▼
Update Checkpoint
```

This avoids repeatedly downloading the complete historical dataset.

---

# Remaining ETL Work

The ETL framework is mostly complete, but production automation is still pending.

Remaining work includes:

- Automated ETL scheduling
- Production job execution
- Additional retry handling
- Remaining data-source completion
- Street-light pipeline completion where required
- Production monitoring
- Improved logging

The ETL should therefore not yet be considered fully automated.

---

# Local Backend Setup

## 1. Clone the repository

```bash
git clone <repository-url>
cd SenseLens
```

---

## 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The project uses a minimal cloud-compatible dependency list:

```text
fastapi[standard]
SQLAlchemy
psycopg[binary]
python-dotenv
requests
```

The dependency file intentionally avoids packages exported from an entire local Conda environment.

---

# Python Version

The cloud deployment uses Python 3.13.

The repository contains:

```text
.python-version
```

with:

```text
3.13
```

This prevents the cloud build environment from unexpectedly selecting a newer Python version that may not yet be compatible with every dependency.

---

# Environment Variables

Create a `.env` file locally:

```env
DB_USER=postgres.<PROJECT_REF>
DB_PASSWORD=<YOUR_DATABASE_PASSWORD>
DB_HOST=<SUPABASE_SESSION_POOLER_HOST>
DB_PORT=5432
DB_NAME=postgres
```

Do not commit `.env`.

Production environment variables should be configured through the cloud hosting platform.

---

# Running the Backend Locally

Run:

```bash
fastapi dev app/main.py
```

The development server should start at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

OpenAPI specification:

```text
http://127.0.0.1:8000/openapi.json
```

---

# CORS Configuration

The FastAPI backend uses `CORSMiddleware` so the Vue application can access the API from a different origin.

The currently allowed frontend origins are:

```text
https://senselens.onrender.com

http://localhost:5173

http://127.0.0.1:5173
```

This supports both:

- The deployed Vue frontend
- Local Vue development

The production frontend URL is:

```text
https://senselens.onrender.com
```

---

# Cloud Deployment

## Frontend

The Vue frontend is currently hosted on Render:

```text
https://senselens.onrender.com
```

## Backend

The FastAPI backend is connected to **FastAPI Cloud** through the project's GitHub repository.

The intended production flow is:

```text
Vue Frontend
   Render
      │
      ▼
FastAPI Backend
 FastAPI Cloud
      │
      ▼
Supabase Session Pooler
      │
      ▼
PostgreSQL
```

The latest backend deployment should be verified in FastAPI Cloud after changes are pushed to `main`.

Backend cloud deployment should not be considered complete until:

- The latest build succeeds
- `/health` responds publicly
- `/docs` loads publicly
- Supabase connectivity works from FastAPI Cloud
- The Render frontend can access the backend without CORS errors

---

# FastAPI Cloud Environment

The FastAPI Cloud environment must contain the same database configuration required by the application.

Example:

```text
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
DB_NAME
```

The production values should use the Supabase Session Pooler.

Local `.env` changes do **not** automatically update FastAPI Cloud environment variables.

Secrets must be configured using the cloud platform's environment/secrets functionality.

---

# Recent Backend Update

The latest backend development checkpoint includes:

- Route forecast API contract completed
- Route quiet-spaces API contract completed
- Saved-route creation API completed
- Saved-route deletion API completed
- Supabase Session Pooler connectivity tested locally
- Frontend CORS configuration added
- Local Swagger/OpenAPI testing completed
- Changes pushed to the `main` branch

Latest backend checkpoint commit:

```text
7bc19c2
```

---

# Current Project Status

| Component | Status |
|---|---|
| Database design | Complete |
| Supabase migration | Complete |
| Supabase Session Pooler configuration | Complete locally |
| ETL framework | Mostly complete |
| Pedestrian data pipeline | Implemented |
| Development/construction pipeline | Implemented |
| FastAPI backend architecture | Complete |
| Core REST APIs | Complete |
| User preferences API | Complete |
| CBD status API | Complete |
| Route API contract | Complete |
| Route forecast API contract | Complete |
| Quiet-spaces API contract | Complete |
| Saved-route read/create/delete APIs | Complete |
| Backend documentation | Complete |
| Frontend CORS configuration | Implemented |
| Backend cloud deployment | In progress / verification required |
| Frontend integration | In progress |
| Dynamic route generation | Not completed |
| Per-sensor 1-3 hour linear-regression forecasting | Complete |
| Route sensory scoring engine | Not completed |
| Route recommendation engine | Not completed |
| Refuge data population | Pending verified data source |
| Route-to-refuge spatial matching | Not completed |
| ETL scheduling | Not completed |
| Production monitoring | Not completed |

---

# Next Development Phase

The next phase focuses on completing the end-to-end application flow.

## 1. Verify FastAPI Cloud Deployment

Confirm:

```text
GET /
GET /health
GET /docs
```

from the public FastAPI Cloud URL.

Then verify database-backed endpoints.

---

## 2. Verify Frontend-to-Backend Communication

The deployed Vue application should call:

```text
Vue / Render
      │
      ▼
FastAPI Cloud
```

without CORS errors.

The frontend team can then configure its API base URL to point to the deployed backend.

---

## 3. Dynamic Route Generation

The frontend/integration work will provide or request candidate walking routes.

Conceptually:

```text
Origin + Destination
        │
        ▼
Mapping / Routing Provider
        │
        ▼
Candidate Walking Routes
        │
        ▼
SenseLens Backend
```

Dynamic route generation is not currently part of the completed FastAPI backend.

---

## 4. Associate Routes with Environmental Data

Candidate routes will eventually be evaluated against:

```text
Pedestrian Sensors
        +
Historical Pedestrian Activity
        +
Construction / Development
        +
Street Lighting
        +
Verified Refuge Locations
        ↓
Route Environmental Profile
```

The existing `RouteSensor` relationship can support association between routes and pedestrian sensors.

---

## 5. Sensory Scoring

Future route scoring will consider factors such as:

- Pedestrian density
- Construction exposure
- Lighting comfort
- Other validated sensory/environmental indicators

These can be represented through the existing `SensoryScore` data model.

---

## 6. Preference-Aware Route Recommendation

User preferences will eventually influence candidate-route ranking.

Conceptually:

```text
Candidate Route
      +
Environmental Conditions
      +
User Preferences
      │
      ▼
Sensory Scoring
      │
      ▼
Route Ranking
      │
      ▼
Recommended Route
```

For example, a user with high crowd sensitivity may prefer a slightly longer walking route with lower expected pedestrian activity.

The exact scoring algorithm still needs to be designed, validated, and documented.

---

## 7. Refuge Integration

The refuge API contract exists, but verified refuge-location data still needs to be identified and populated.

Potential categories may include suitable:

- Parks
- Libraries
- Community spaces
- Other verified low-stimulation locations

Any refuge dataset or curation methodology should be documented.

SenseLens should not fabricate refuge locations.

---

## 8. ETL Automation

After the main application flow is stable, ETL pipelines can be scheduled automatically.

The target production flow is:

```text
Scheduled Job
      │
      ▼
Melbourne Open Data
      │
      ▼
ETL Pipeline
      │
      ▼
Supabase
      │
      ▼
FastAPI
      │
      ▼
Frontend
```

This will keep environmental data updated without requiring manual execution.

---

# Development Principles

## No Fabricated Data

If underlying data is unavailable, the backend returns an empty or unavailable response instead of inventing values.

---

## Separation of Responsibilities

```text
ETL
→ retrieves and prepares external data

Supabase
→ stores shared application data

FastAPI
→ provides backend business logic and REST APIs

Vue
→ provides the user interface

Mapping Integration
→ handles map display and candidate route generation
```

---

## Secure Configuration

Secrets are stored using environment variables rather than being hard-coded in the repository.

---

## Stable API Contracts

Where possible, frontend-facing API contracts are established before more advanced internal functionality is implemented.

For example:

```text
GET /routes/{route_id}/forecast
```

can remain stable while the internal implementation evolves from the current sensory-state retrieval to a future predictive model.

---

# Target Architecture

The intended final architecture is:

```text
              City of Melbourne Open Data
                         │
                         ▼
                 Scheduled ETL Jobs
                         │
                         ▼
                 Supabase PostgreSQL
                         │
                         ▼
                  FastAPI Backend
                         ▲
                         │
                  Candidate Routes
                         │
                 Mapping Provider
                         │
                         ▼
                 Sensory Scoring
                         │
                         ▼
               Route Recommendation
                         │
                         ▼
                   Vue Frontend
                         │
                         ▼
                 Interactive Map
```

---

# Security Notes

- Never commit `.env`.
- Never commit database passwords.
- Never expose PostgreSQL credentials to the frontend.
- Database credentials belong only in the backend environment.
- The frontend should communicate with FastAPI rather than directly connecting to PostgreSQL.
- Production secrets should be configured through the hosting provider.
- Database access should follow least-privilege principles.
- Rotate credentials if they are accidentally exposed.

---

# Team

**SenseLens**

Monash University
Industry Experience Onboarding Project
2026
