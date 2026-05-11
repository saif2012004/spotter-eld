# Spotter ELD — Trip Planner

A full-stack web application that lets a commercial truck driver enter a current location, pickup, and dropoff, then instantly receives a complete FMCSA-compliant trip plan: an interactive route map, a chronological Hours of Service (HOS) stop schedule, and printable ELD daily log sheets rendered in SVG — all generated server-side in real time.

---

## Live Demo

| Resource | Link |
|---|---|
| Live app | https://spotter-eld-phi.vercel.app |
| API | https://spotter-eld-backend-s73n.onrender.com/api/plan-trip/ |
| Walkthrough video | _(coming soon)_ |

---

## Features

- **HOS simulator** — pure Python engine encoding all five FMCSA 70-hr/8-day property-carrier rules (11-hr drive, 14-hr window, 30-min break, 70-hr cycle, 10-hr reset, 34-hr restart)
- **Real geocoding** — Nominatim / OpenStreetMap; in-process LRU cache respects 1 req/s rate limit
- **Real routing** — OSRM public API; GeoJSON polyline fed directly to the Leaflet map
- **Interactive map** — React-Leaflet with auto-fit bounds, waypoint markers, and popup labels
- **Stops timeline** — fuel stops, 30-min breaks, 10-hr resets, and 34-hr restarts shown with cumulative mileage
- **Daily log SVG** — faithful reproduction of the FMCSA paper ELD form; one per calendar day; browser-printable (each sheet on its own page)
- **Multi-day trips** — events automatically split at midnight; correct calendar grouping
- **Zero paid APIs** — Nominatim + OSRM are free and require no key

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Django 5.0 + Django REST Framework 3.15 |
| Geocoding | Nominatim (OpenStreetMap) via `requests` |
| Routing | OSRM public demo API |
| Frontend | React 18 + Vite 5 |
| Map | Leaflet 1.9 + react-leaflet 4 |
| HTTP client | Axios (60 s timeout) |
| Static files | WhiteNoise (Django) |
| Deployment | Render (backend) + Vercel (frontend) |

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 18+

### Backend

```bash
cd backend

# Create and activate virtualenv
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env              # then edit .env — set a real SECRET_KEY
echo "SECRET_KEY=local-dev-key" >> .env
echo "DEBUG=True" >> .env

# Verify configuration
python manage.py check

# Apply migrations
python manage.py migrate

# Start dev server
python manage.py runserver        # http://localhost:8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env              # already contains VITE_API_URL=http://localhost:8000

# Start dev server
npm run dev                       # http://localhost:5173
```

Open `http://localhost:5173`, fill in the pre-loaded demo cities (LA → Phoenix → Dallas), and click **Plan Trip**.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **yes** | `dev-secret-change-me` | Django secret key — generate a long random string for prod |
| `DEBUG` | no | `False` | Set `True` for local dev |
| `ALLOWED_HOSTS` | no | `*` | Comma-separated allowed hostnames |
| `CORS_ALLOWED_ORIGINS` | no | _(empty)_ | Comma-separated frontend origins for prod (e.g. `https://your-app.vercel.app`) |

### Frontend (`frontend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_URL` | no | _(empty — uses Vite proxy)_ | Full URL of the deployed backend, e.g. `https://spotter-eld.onrender.com` |

---

## Deployment

### Backend → Render

1. Push repo to GitHub.
2. In Render, create a new **Web Service**, point it at the repo root.
3. Render reads `render.yaml` automatically — build command and start command are pre-configured.
4. Set environment variables in the Render dashboard: `SECRET_KEY`, `ALLOWED_HOSTS` (your Render domain), `CORS_ALLOWED_ORIGINS` (your Vercel domain).

### Frontend → Vercel

1. Import the repo in Vercel; set **Root Directory** to `frontend`.
2. Add environment variable `VITE_API_URL` = your Render backend URL.
3. `vercel.json` provides the SPA rewrite rule — no extra config needed.

---

## Architecture

```
Browser (React + Leaflet)
    │
    │  POST /api/plan-trip/  (JSON)
    ▼
Django REST Framework  ──►  Nominatim (geocoding, OSM)
    │                  ──►  OSRM       (routing, OSM)
    │
    ▼
HOS Simulator (pure Python, planner/services/hos.py)
    │
    │  list[Event]
    ▼
Response builder
  ├── route  (geometry, legs, waypoints)
  ├── stops  (fuel | rest_30min | rest_10hr | restart_34hr)
  ├── daily_logs  (per-calendar-day event lists + totals)
  └── summary  (totals, cycle state)
    │
    ▼
React renders:
  ├── RouteMap     (react-leaflet polyline + markers)
  ├── TripSummary  (stat cards + stops table)
  └── DailyLogSheet × N  (SVG ELD forms, print-ready)
```

---

## FMCSA HOS Rules Implemented

All rules are for **property-carrying CMV drivers on the 70-hr/8-day cycle** (49 CFR Part 395):

- **11-hour driving limit** — a driver may drive a maximum of 11 hours after 10 consecutive hours off duty.
- **14-hour on-duty window** — a driver may not drive beyond the 14th consecutive hour after coming on duty. Off-duty time does not extend the window.
- **30-minute break** — driving is not permitted after 8 cumulative hours of driving without at least a 30-minute off-duty or sleeper-berth break.
- **70-hour/8-day limit** — a driver may not drive after accumulating 70 on-duty hours in any 8 consecutive days.
- **10-hour reset** — 10 consecutive hours off duty restarts the 11-hour and 14-hour clocks.
- **34-hour restart** — 34 consecutive hours off duty restarts the 70-hour/8-day cycle.

Trip-specific assumptions:

- Average truck speed: **55 mph**
- Fuel stop every **1,000 miles** (15 minutes, on-duty not driving)
- **1 hour** on-duty at pickup; **1 hour** on-duty at dropoff

---

## Known Limitations / Future Work

| Item | Notes |
|---|---|
| No persistent storage | Trips are not saved; refresh clears the plan |
| SQLite only | Suitable for single-instance deploy; swap for Postgres for multi-instance |
| Sleeper-berth split provision | Not modelled (would require split sleeper rules per 49 CFR 395.1(g)) |
| Adverse driving conditions | +2 hr exception not implemented |
| No driver authentication | Single-driver demo; no account system |
| Real-time traffic | OSRM uses historical average speeds, not live traffic |
| Nominatim rate limit | 1 req/s; high traffic would need a self-hosted instance or paid geocoder |
| 60-hr/7-day cycle | Recap section renders placeholder values only |
