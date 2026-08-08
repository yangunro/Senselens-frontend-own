# ETL Pipeline Documentation

## SenseLens Backend

### Industry Experience Project 2026

---

# Overview

The ETL (Extract, Transform, Load) module is responsible for collecting, cleaning, validating, standardizing, and storing data from the City of Melbourne Open Data Platform into the SenseLens PostgreSQL database.

The pipeline has been designed with reliability, modularity, and maintainability in mind. Every dataset follows a common workflow:

```
City of Melbourne API
        │
        ▼
Extract
        │
        ▼
Transform
        │
        ▼
Validate & Clean
        │
        ▼
Load (UPSERT)
        │
        ▼
PostgreSQL
```

Rather than inserting raw API data directly into the database, every record passes through a validation and standardization layer before loading.

---

# ETL Architecture

```
etl/

├── client.py
├── repository.py
├── validators.py
├── initialize_checkpoint.py
│
├── sync_sensor_locations.py
├── sync_pedestrian_live.py
├── sync_pedestrian_history.py
├── sync_development.py
└── sync_streetlights.py
```

Each module has a dedicated responsibility.

---

# client.py

## Purpose

Provides a reusable API client for all City of Melbourne datasets.

Instead of every ETL script creating HTTP requests independently, all requests are handled centrally through this module.

Responsibilities include:

- HTTP requests
- Query parameter construction
- Pagination
- Retry logic
- Exponential backoff
- Rate limit handling
- Error handling

---

## Features

### Automatic Retry

When the City API returns

```
HTTP 429
Too Many Requests
```

the client automatically retries the request.

Example:

```
Attempt 1

↓

429

↓

Wait 1 second

↓

Retry

↓

429

↓

Wait 2 seconds

↓

Retry

↓

Wait 4 seconds

↓

Wait 8 seconds

↓

Wait 16 seconds
```

This significantly improves reliability for large historical imports.

---

# repository.py

## Purpose

Handles all database interaction.

The ETL scripts never execute SQL directly.

Instead they call repository functions such as

```
upsert_sensor()

upsert_pedestrian_count()

upsert_pedestrian_history()

upsert_development()
```

Advantages

- Centralized SQL
- Easier maintenance
- Reusable UPSERT logic
- Cleaner ETL scripts

---

## UPSERT Strategy

Instead of

```
INSERT
```

the project uses

```
INSERT

ON CONFLICT

DO UPDATE
```

Benefits

- No duplicate records
- Safe re-running of ETL
- Incremental loading
- Idempotent ingestion

---

# validators.py

## Purpose

Contains reusable validation and cleaning logic shared by every ETL.

Instead of repeating validation inside every script, all common rules are centralized.

---

## Current Validators

### Coordinate Validation

Ensures every location lies within the Melbourne metropolitan area.

Rejects

```
NULL

0,0

Invalid coordinates
```

---

### Text Cleaning

Removes

- leading spaces
- trailing spaces
- empty strings

Example

```
" Melbourne Central "

↓

"Melbourne Central"
```

---

### Status Normalization

Development statuses are standardized.

Example

```
UNDER CONSTRUCTION

↓

Under Construction
```

This prevents inconsistent categories.

---

### Count Validation

Rejects

- negative pedestrian counts
- NULL counts
- invalid numeric values

---

# initialize_checkpoint.py

## Purpose

Historical pedestrian data is loaded incrementally.

Instead of hardcoding dates, this script analyses the existing database and determines the last successfully loaded day.

It automatically creates or updates the ETL checkpoint.

Example

```
2025-01-01

...

2025-06-16

↓

Checkpoint

↓

2025-06-16
```

The historical ETL resumes from

```
2025-06-17
```

without requiring manual intervention.

---

# ETLCheckpoint Table

Purpose

Tracks historical ingestion progress.

Schema

```
Dataset

LastSuccessfulDate

UpdatedAt
```

Example

| Dataset | LastSuccessfulDate |
|----------|-------------------|
| PedestrianHourlyHistory | 2025-06-16 |

---

# Sensor Location ETL

File

```
sync_sensor_locations.py
```

Dataset

City of Melbourne Pedestrian Sensor Locations

Responsibilities

- Download sensor metadata
- Validate coordinates
- Clean descriptions
- UPSERT into PostgreSQL

Cleaning

- Coordinate validation
- Description trimming
- Duplicate prevention

Destination

```
SensorLocation
```

---

# Live Pedestrian ETL

File

```
sync_pedestrian_live.py
```

Dataset

Past Hour Counts Per Minute

Responsibilities

- Download latest pedestrian counts
- Validate counts
- Insert latest readings

Cleaning

- Reject missing Sensor IDs
- Reject invalid timestamps
- Reject negative counts

Destination

```
PedestrianCount
```

---

# Historical Pedestrian ETL

File

```
sync_pedestrian_history.py
```

Dataset

Monthly Counts Per Hour

Responsibilities

- Incremental loading
- Historical synchronization
- Resume after interruption

Unlike the live ETL, this pipeline loads one day at a time.

Workflow

```
Checkpoint

↓

Next Day

↓

Download

↓

Validate

↓

UPSERT

↓

Checkpoint Update
```

If the API returns

```
429
```

the ETL stops immediately.

The checkpoint is NOT updated.

The next execution resumes from exactly the failed day.

This prevents gaps in historical data.

---

## Historical Retry Strategy

```
429

↓

Retry

↓

Retry

↓

Retry

↓

Still failing

↓

STOP

↓

Checkpoint unchanged
```

This guarantees that failed days are never skipped.

---

# Development Activity ETL

File

```
sync_development.py
```

Dataset

Development Activity Monitor

Responsibilities

- Download development sites
- Standardize statuses
- Validate coordinates
- UPSERT data

Cleaning

- Status normalization
- Coordinate validation
- Text trimming

Destination

```
DevelopmentSite_Status
```

---

# Street Lights ETL

File

```
sync_streetlights.py
```

Status

Under development.

Current blocker

```
City API

↓

HTTP 429
```

The ETL architecture is complete, however testing is temporarily paused due to API rate limiting.

---

# Data Cleaning Pipeline

Every dataset follows the same process.

```
Raw API Record

↓

Transform

↓

Validate

↓

Clean

↓

UPSERT

↓

Database
```

---

# Error Handling

The ETL distinguishes between

### Recoverable Errors

Examples

- Missing field
- Invalid coordinate
- Invalid count

Action

```
Skip Record
```

---

### Fatal Errors

Examples

- API unavailable
- Rate limit exceeded
- Database unavailable

Action

```
Stop ETL

Checkpoint unchanged
```

This prevents incomplete historical imports.

---

# Advantages

The ETL framework provides

- Modular design
- Reusable validation
- Automatic retries
- Checkpoint recovery
- Incremental loading
- Duplicate prevention
- Safe reprocessing
- Centralized SQL
- Consistent data cleaning
- Maintainable architecture

---

# Current Progress

| Component | Status |
|------------|---------|
| API Client | ✅ Complete |
| Repository Layer | ✅ Complete |
| Validation Layer | ✅ Complete |
| Sensor Location ETL | ✅ Complete |
| Live Pedestrian ETL | ✅ Complete |
| Historical Pedestrian ETL | ✅ Complete (awaiting API availability) |
| Development Activity ETL | ✅ Complete |
| Street Lights ETL | 🚧 In Progress |

---

# Future Improvements

The current implementation is fully functional but several enhancements are planned.

- Bulk UPSERT operations for improved performance
- Logging framework
- Scheduler for automated ETL execution
- Configuration through environment variables
- Unit testing
- Docker support
- CI/CD pipeline
- Monitoring and alerting
- Additional City of Melbourne datasets

---

# Authors

Industry Experience Onboarding Project

Team Beyond KPI

Monash University

2026