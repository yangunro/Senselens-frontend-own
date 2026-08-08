# SenseLens

## Overview

SenseLens is an intelligent sensory-aware navigation platform designed to provide safer and more comfortable walking routes throughout Melbourne CBD.

The system combines real-time pedestrian activity, historical pedestrian trends, construction information, street lighting data and user accessibility preferences to recommend walking routes tailored to individual sensory needs.

---

## System Architecture

```
                Melbourne Open Data
                        │
                        ▼
                 ETL Pipelines
                        │
                        ▼
             Supabase PostgreSQL
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
     FastAPI Backend             Vue Frontend
```

---

## Repository Structure

- `/app` — FastAPI backend
- `/etl` — Data ingestion pipelines
- `/frontend` — Vue application
- `/docs` — Technical documentation

---

## Technology Stack

- FastAPI
- Vue
- PostgreSQL
- Supabase
- SQLAlchemy
- Python
- Google Maps API
- Open Data Melbourne

---

## Features

- Live pedestrian monitoring
- Historical pedestrian analytics
- User sensory preferences
- Route recommendations
- Construction awareness
- Street lighting information
- Quiet refuge locations

---

## Documentation

| Folder | Description |
|---------|-------------|
| app | Backend APIs |
| etl | ETL Pipelines |
| docs | Project documentation |

---

## Team

Monash University

Industry Experience Project

2026