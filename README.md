<<<<<<< HEAD
# SenseLens

Real-time, sensory-aware wayfinding for Melbourne's CBD. Built for FIT5120,
targeting UN SDG 11 (Sustainable Cities and Communities) — Target 11.2
(Accessible Transit) and 11.7 (Inclusive Public Spaces).

SenseLens helps neurodivergent, sensory-sensitive commuters route by sensory
load, not just shortest time — combining live crowd, transit, and
environmental data to suggest calmer paths and nearby quiet refuges before
they're needed.

## Team

| Name | Role |
|---|---|
| Shiza Maryam | Business Analyst — research, requirements, design |
| Wenlu Yang | Developer — builds & deploys the app |
| Sampreet Shibu George | Data Scientist — crowd-density analysis |
| Abdullah Mehmood | Data Engineer — data pipeline & database |
| Shashi Danasari | ML Engineer — predictive forecasting |
| Yu Zhang | ML Engineer — predictive forecasting |

## Stack decision

**Web app (PWA)**, not native. One developer + one iteration timeline means
native (Swift/Kotlin/Flutter) overhead isn't worth it, and a PWA still
delivers geolocation, push-style reroute alerts, and offline caching via
service workers — everything the prototype needs — without app store
review lead time.

## Data model

`schema.sql` in this folder is the full PostgreSQL DDL for the project ERD
(12 tables across four zones):

- **App-native** — `User`, `UserPreference`, `SavedRoute` (captured directly
  by the app, no external dependency)
- **Route request & computed** — `Route`, `SensoryScore`, `RouteSensor`
- **Open data & computed** — `SensorLocation`, `PedestrianCount`,
  `TransitCongestionSignal` (Transport Victoria GTFS-Realtime)
- **Open data & curated** — `RefugeLocation`, `DevelopmentSite_Status`,
  `StreetLight_LuxLevel` (spatially joined to a route at query time, not a
  persisted FK)

Two changes from the original ERD diagram, made to match the prototype:
`SensoryScore.SensoryIndicator` is now a three-level enum (Low/Medium/High)
instead of two, and `UserPreference` gained `LightSensitivity` to back the
Settings screen's brightness slider. Both are commented inline in
`schema.sql`.

Data sources: City of Melbourne Open Data Portal (Pedestrian Counting
System, Development Activity Monitor, Street Lights) and Transport
Victoria's GTFS / GTFS-Realtime feeds (`opendata.transport.vic.gov.au`).

## Roadmap

**Phase 0 — Setup**
Repo, Postgres provisioning, run `schema.sql`, register for the GTFS-Realtime
API key early (longest external lead time).

**Phase 1 — Data foundation** *(Abdullah)*
Load static open data, build/test the GTFS-Realtime poller, curate
~20–30 RefugeLocation entries, seed demo users.

**Phase 2 — Scoring & forecasting** *(Sampreet, Shashi, Yu)*
v1 SensoryScore formula; hindsight/insight/foresight logic behind the
"Sensory Forecast" feature; validate end-to-end on at least one real route.

**Phase 3 — Backend/API** *(Wenlu, Abdullah)*
Route request, refuge/quiet-space spatial lookup, preferences CRUD, saved
routes; wire in the Phase 2 scoring.

**Phase 4 — Frontend/PWA** *(Wenlu, Shiza)*
Home / Route selection / Map / Settings screens; manifest + service worker;
geolocation permission flow.

**Phase 5 — Testing & QA** *(whole team)*
Accessibility/usability testing, defect triage, verify against the
Definition of Done.

**Phase 6 — Docs & presentation** *(Shiza, Abdullah)*
ERD image, Data Insights slide, Security Risk Heatmap, Elevator Pitch,
STRIDE labelling, Data Management Plan, pitch rehearsal.

## Definition of Done

- [ ] User can enter a destination within Melbourne CBD
- [ ] System generates at least one sensory-aware route using City of
      Melbourne open data
- [ ] Routes carry a sensory indicator based on agreed factors (e.g.
      pedestrian volume)
- [ ] Recommendations adjust when crowd levels exceed the user's limits
- [ ] Accessibility and usability testing completed with representative
      users
- [ ] All critical and high-priority defects resolved
- [ ] Acceptance criteria met and approved by mentors
=======
# SenseLense
Onboarding Project: Building Sensory-Friendly Urban Futures
>>>>>>> 9ba8e26c8f7a2de8ae38e1f7a8efc8b61b25de61
