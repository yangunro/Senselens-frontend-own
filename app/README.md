# SenseLens Backend API

## Overview

The SenseLens Backend is built using **FastAPI** and provides RESTful APIs for the SenseLens application.

It acts as the communication layer between the Vue frontend and the PostgreSQL database hosted on Supabase.

Current responsibilities include:

- User management
- User preference management
- CBD activity status
- Route management
- Saved routes
- Refuge locations
- Sensory route information

---

# Architecture

```
Vue Frontend
      │
      ▼
FastAPI Backend
      │
      ▼
Supabase PostgreSQL
      ▲
      │
ETL Pipelines
```

The backend **never communicates directly with external data sources**.

All external data is first processed through the ETL pipelines and stored in PostgreSQL.

The backend only queries the database.

---

# Technology Stack

- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Supabase
- Psycopg
- Pydantic
- Uvicorn

---

# Project Structure

```
app/
│
├── database.py
├── main.py
│
├── routers/
│   ├── cbd_status.py
│   ├── preferences.py
│   ├── refuges.py
│   ├── routes.py
│   └── saved_routes.py
│
└── services/
    ├── cbd_status_service.py
    ├── preferences_service.py
    ├── refuges_service.py
    ├── routes_service.py
    └── saved_routes_service.py
```

---

# Running the Backend

## Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a `.env` file.

Example:

```env
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD
DB_HOST=db.your-project.supabase.co
DB_PORT=5432
DB_NAME=postgres
```

---

## Start the API

```bash
fastapi dev app/main.py
```

or

```bash
uvicorn app.main:app --reload
```

---

# Swagger Documentation

After starting the server:

```
http://127.0.0.1:8000/docs
```

Swagger automatically documents every endpoint.

---

# Current API Endpoints

## System

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | API status |
| GET | `/health` | Health check |

---

## Users

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/users` | Retrieve all users |
| POST | `/users` | Create a new user |

---

## Preferences

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/preferences` | Retrieve user preferences |
| POST | `/preferences` | Save user preferences |

---

## CBD

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/cbd-status` | Current CBD activity level |

---

## Routes

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/routes` | Retrieve available routes |
| GET | `/routes/{routeId}` | Retrieve a specific route |
| GET | `/routes/{routeId}/alerts` | Retrieve alerts for a route |

---

## Saved Routes

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/saved-routes` | Retrieve user's saved routes |

---

## Refuges

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/refuges` | Retrieve available refuge locations |

---

# Backend Design

The backend follows a layered architecture.

```
HTTP Request
      │
      ▼
Router
      │
      ▼
Service
      │
      ▼
PostgreSQL
```

### Routers

Responsible for:

- API endpoints
- Request validation
- HTTP responses

### Services

Responsible for:

- Business logic
- SQL queries
- Database interaction

This separation keeps the application modular and maintainable.

---

# Database

The backend connects to a PostgreSQL database hosted on Supabase.

Primary tables include:

- User
- UserPreference
- Route
- SavedRoute
- RouteSensor
- SensoryScore
- RefugeLocation
- SensorLocation
- PedestrianCount
- PedestrianHourlyHistory
- DevelopmentSite_Status
- StreetLight_LuxLevel
- TransitCongestionSignal

---

# Current Development Status

## Completed

- FastAPI project setup
- Supabase database integration
- User APIs
- Preference APIs
- CBD status API
- Saved routes API
- Refuge API
- Route APIs
- Route alerts API

## In Progress

- Dynamic route generation
- Route forecasting
- Sensor-aware routing
- Construction-aware routing
- Refuge recommendations
- Google Maps integration

---

# Future Improvements

- JWT authentication
- User login
- Route optimisation
- Google Directions API integration
- Real-time pedestrian updates
- Route forecasting
- Sensory score calculation
- Deployment to Render
- CI/CD pipeline

---

# Authors

SenseLens Industry Experience Team

Monash University

2026