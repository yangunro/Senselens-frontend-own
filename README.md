# SenseLens

## Overview

**SenseLens** is a sensory-aware navigation platform designed to support more comfortable walking experiences through Melbourne CBD.

Traditional navigation applications generally optimise routes based on factors such as distance and travel time. SenseLens aims to extend this by considering environmental and sensory conditions that may affect a person's walking experience.

The platform is designed to combine:

- Live pedestrian activity
- Historical pedestrian activity
- Construction and development activity
- Street-light information
- Quiet/refuge locations when available
- User sensory preferences
- Route information

The long-term goal is to recommend walking routes based not only on distance and duration, but also on the sensory preferences of the user.

> **Current status:** The database, ETL foundation, cloud database integration, and core FastAPI API layer have been implemented. Dynamic sensory-aware route generation and recommendation are the next major development phase.

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

### Data Flow

1. Public datasets are retrieved from City of Melbourne data sources.
2. ETL pipelines extract, validate, clean, standardise, and transform the data.
3. Processed data is stored in PostgreSQL hosted on Supabase.
4. The FastAPI backend reads application data from Supabase.
5. REST API endpoints expose the required data to the frontend.
6. The Vue frontend consumes these APIs to build the SenseLens user experience.

Future routing functionality will introduce a mapping/routing provider to generate candidate walking routes before SenseLens evaluates their sensory characteristics.

---

## Technology Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- Psycopg
- Pydantic
- Uvicorn

### Database

- PostgreSQL
- Supabase

### ETL

- Python
- Requests
- City of Melbourne Open Data APIs
- Incremental loading
- Checkpoint-based synchronisation

### Frontend

- Vue
- JavaScript
- Render

### Deployment

- Render — current frontend hosting
- FastAPI Cloud — backend deployment in progress
- Supabase — cloud PostgreSQL database

---

## Repository Structure

The project is separated into application and data-processing components.

```text
SenseLens/
│
├── README.md
├── requirements.txt
├── .python-version
├── .gitignore
│
├── app/
│   ├── README.md
│   ├── main.py
│   ├── database.py
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
└── ...
```

The exact structure may continue to evolve as routing, deployment, and frontend integration are developed.

---

## Backend Architecture

The FastAPI backend follows a layered structure:

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
SQLAlchemy
      │
      ▼
Supabase PostgreSQL
```

### Routers

Routers are responsible for:

- Defining HTTP endpoints
- Receiving requests
- Validating request parameters
- Calling the appropriate service functions
- Returning API responses

### Services

Services are responsible for:

- Business logic
- Database queries
- Data transformation
- Preparing frontend-friendly responses

This separation helps keep the backend maintainable as the application becomes more complex.

---

## Current Backend APIs

The following API endpoints have been implemented.

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/` | API root/status | Implemented |
| GET | `/health` | Backend health check | Implemented |
| GET | `/users` | Retrieve users | Implemented |
| POST | `/users` | Create a user | Implemented |
| GET | `/preferences` | Retrieve sensory preferences | Implemented |
| POST | `/preferences` | Save/update sensory preferences | Implemented |
| GET | `/cbd-status` | Retrieve current CBD activity status | Implemented |
| GET | `/refuges` | Retrieve refuge locations | Implemented |
| GET | `/saved-routes` | Retrieve saved routes | Implemented |
| GET | `/routes` | Retrieve available stored routes | Implemented |
| GET | `/routes/{route_id}` | Retrieve a specific route | Implemented |
| GET | `/routes/{route_id}/alerts` | Retrieve alerts associated with a route | Implemented |

### Empty API Responses

Some endpoints currently return empty arrays:

```json
[]
```

This is expected.

For example:

- `/refuges`
- `/saved-routes`
- `/routes`

may return empty arrays because the corresponding tables have not yet been populated.

The API endpoints have been implemented so the frontend contract is available before the routing and refuge-data pipelines are completed.

No artificial refuge or route data is generated simply to populate these endpoints.

---

## User Preferences

SenseLens currently supports the following sensory preferences.

### Sliders

```text
Crowd sensitivity
Noise sensitivity
Light sensitivity
```

The frontend uses:

```text
0 = Low
1 = Medium
2 = High
```

Noise and light sensitivity are stored in PostgreSQL using the `sensitivity_level` enum:

```text
Low
Medium
High
```

Crowd sensitivity is currently stored numerically.

### Toggles

Current preference toggles include:

- Avoid construction zones
- Show refuge spaces
- High contrast mode

Preferences can be retrieved using:

```text
GET /preferences
```

and updated using:

```text
POST /preferences
```

---

## Database and Data Pipeline

The SenseLens PostgreSQL database is hosted on **Supabase**.

The FastAPI backend connects directly to this shared cloud database rather than relying on a developer's local PostgreSQL installation.

### Core Tables

The database currently includes tables supporting:

- Users
- User preferences
- Pedestrian sensors
- Live pedestrian counts
- Historical pedestrian counts
- Development/construction information
- Street-light information
- Routes
- Route-to-sensor relationships
- Saved routes
- Sensory scores
- Refuge locations
- Transit congestion signals
- ETL checkpoints

Examples include:

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

## ETL Pipeline

The ETL layer is responsible for moving external public data into the SenseLens database.

The general ETL flow is:

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

### Implemented ETL Features

The ETL framework currently includes:

- API extraction
- Pagination
- Data transformation
- Data validation
- Missing-value checks
- Non-negative count validation
- Standardised database field mappings
- UPSERT operations
- Duplicate protection
- Incremental loading
- Historical loading
- ETL checkpoints
- Error handling
- Pedestrian data ingestion
- Development/construction data ingestion

### Historical Pedestrian Loading

Historical pedestrian data uses checkpoint-based incremental loading.

Conceptually:

```text
Last Successful Date
        │
        ▼
Next Required Date
        │
        ▼
Fetch Data
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

### Remaining ETL Work

The ETL framework is mostly complete, but additional work remains:

- Automated ETL scheduling
- Production job execution
- Additional retry handling
- Remaining street-light/data-source completion
- Production monitoring and logging

The ETL should therefore not yet be considered fully automated.

---

## Local Backend Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd SenseLens
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

The backend currently uses a minimal dependency set:

```text
fastapi[standard]
SQLAlchemy
psycopg[binary]
python-dotenv
requests
```

The dependency file intentionally contains only project dependencies rather than packages from a developer's complete local Conda environment.

---

## Environment Variables

Create a local `.env` file:

```env
DB_USER=YOUR_DATABASE_USER
DB_PASSWORD=YOUR_DATABASE_PASSWORD
DB_HOST=YOUR_SUPABASE_DATABASE_HOST
DB_PORT=5432
DB_NAME=postgres
```

Do not commit `.env` to Git.

Database credentials must not be stored directly in source code.

---

## Running the Backend Locally

Run:

```bash
fastapi dev app/main.py
```

The development server should start at:

```text
http://127.0.0.1:8000
```

Swagger documentation is available at:

```text
http://127.0.0.1:8000/docs
```

FastAPI automatically generates the OpenAPI specification at:

```text
http://127.0.0.1:8000/openapi.json
```

---

## Cloud Deployment

### Frontend

The Vue frontend is currently hosted on Render:

```text
https://senselens.onrender.com
```

### Backend

The FastAPI backend is currently being deployed through **FastAPI Cloud** using the project's GitHub repository.

The intended architecture is:

```text
Vue Frontend
Render
        │
        ▼
FastAPI Backend
FastAPI Cloud
        │
        ▼
Supabase PostgreSQL
```

The frontend and backend do not need to be hosted by the same provider.

### FastAPI Cloud Deployment Preparation

The deployment configuration has been cleaned so cloud builds do not attempt to install packages from a developer's local Conda/macOS environment.

The previous dependency file contained local paths similar to:

```text
file:///private/var/...
```

These are not portable to Linux cloud environments.

The project now uses the minimal dependency list shown above.

Python is also pinned to Python 3.13 using:

```text
.python-version
```

containing:

```text
3.13
```

The FastAPI Cloud deployment is currently **in progress** and should not be considered complete until the deployed API and Swagger documentation have been successfully verified.

Once deployment succeeds, the frontend team will receive:

```text
API Base URL
https://<backend-domain>

Swagger
https://<backend-domain>/docs
```

The frontend can then configure:

```env
VITE_API_BASE=https://<backend-domain>
```

---

## Current Project Status

| Component | Status |
|---|---|
| Database design | Complete |
| Supabase migration | Complete |
| ETL framework | Mostly complete |
| Pedestrian data pipeline | Implemented |
| Development/construction pipeline | Implemented |
| FastAPI backend structure | Complete |
| Core REST APIs | Complete |
| User preferences API | Complete |
| CBD status API | Complete |
| Route API contract | Complete |
| Refuge API contract | Complete |
| Saved routes API contract | Complete |
| Backend documentation | Complete |
| Backend cloud deployment | In progress |
| Frontend integration | In progress |
| Dynamic route generation | Not started |
| Sensory scoring engine | Not started |
| Route recommendation engine | Not started |
| Refuge data population | Not started / pending data source |
| ETL scheduling | Not started |
| Production monitoring | Not started |

---

## Next Development Phase

The next major phase is to turn the existing backend infrastructure into the sensory-aware navigation engine.

### 1. Complete Backend Deployment

Verify the FastAPI Cloud deployment and confirm that endpoints such as:

```text
/health
/cbd-status
/preferences
/routes
```

work from the public cloud URL.

Then provide the frontend team with:

```text
API Base URL
Swagger URL
```

---

### 2. Dynamic Route Generation

The current `Route` table stores route information, but dynamic walking-route generation has not yet been implemented.

The next routing architecture will be:

```text
User Origin + Destination
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

A suitable mapping/routing provider will be integrated to obtain route geometry, distance, duration, and alternative walking routes.

---

### 3. Associate Environmental Data with Routes

Candidate routes will then be evaluated against SenseLens data.

Potential inputs include:

```text
Pedestrian Sensors
        +
Historical Pedestrian Activity
        +
Construction / Development
        +
Street Lighting
        +
Refuge Locations
        ↓
Candidate Route Analysis
```

The `RouteSensor` relationship will help associate pedestrian sensors with routes.

---

### 4. Sensory Scoring

Each candidate route will receive sensory measurements such as:

- Pedestrian density
- Construction exposure
- Lighting comfort

These will be stored or represented through `SensoryScore`.

---

### 5. Preference-Aware Recommendation

User preferences will influence the route ranking.

Conceptually:

```text
Candidate Route
      +
Environmental Conditions
      +
User Preferences
      ↓
Sensory Score
      ↓
Route Ranking
      ↓
Recommended Route
```

For example, a user with high crowd sensitivity may prefer a slightly longer route with lower pedestrian activity.

A user who enables:

```text
Avoid construction zones = true
```

may receive a strong penalty for candidate routes passing through construction-heavy areas.

The exact scoring formula and thresholds still need to be designed, tested, and documented.

---

### 6. Refuge Integration

The `/refuges` API is implemented, but refuge-location data has not yet been populated.

Potential quiet/refuge spaces may eventually include suitable:

- Parks
- Libraries
- Community spaces
- Other curated low-stimulation locations

Refuge data must come from a verified dataset or a documented curation process.

SenseLens should **not fabricate refuge locations**.

---

### 7. Frontend Integration

Once the backend receives a public URL, the Vue frontend can begin consuming:

```text
GET /cbd-status

GET /preferences
POST /preferences

GET /routes
GET /routes/{route_id}
GET /routes/{route_id}/alerts

GET /saved-routes

GET /refuges
```

The map interface will eventually display candidate routes, environmental conditions, sensory information, and the recommended route.

---

### 8. ETL Automation

After the main application flow is functioning, the ETL pipelines will be scheduled automatically.

The intended production flow will become:

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

This will keep pedestrian and environmental information up to date without requiring developers to manually execute ETL scripts.

---

## Development Principles

The project currently follows several important principles:

### No fabricated data

If an underlying table contains no data, the API returns an empty or unavailable response rather than inventing values.

### Separation of responsibilities

```text
ETL
→ obtains and prepares external data

Database
→ stores application data

FastAPI
→ exposes business logic and APIs

Vue
→ handles the user interface
```

### Environment-based configuration

Secrets and database credentials are stored using environment variables rather than being committed to GitHub.

### Incremental development

Features are implemented and tested independently before additional complexity is introduced.

---

## Target Architecture

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
              ┌──────────┴──────────┐
              │                     │
              │              Environmental Data
              │                     │
              ▼                     ▼
        FastAPI Backend ◄──── Routing Provider
              │
              │
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

## Security Notes

- Never commit `.env`.
- Never commit database passwords.
- Never expose the Supabase PostgreSQL password to the frontend.
- The Vue frontend should communicate with FastAPI rather than directly using privileged database credentials.
- Production secrets should be configured through the hosting provider's environment/secrets management.
- Database access should follow least-privilege principles as the application moves toward production.

---

## Team

**SenseLens**

Monash University  
Industry Experience Onboarding Project  - TEAM Beyond-KPI
2026