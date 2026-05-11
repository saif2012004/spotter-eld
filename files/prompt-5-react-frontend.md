# Prompt 5 — React Frontend (Form, Map, Summary)

Implement the React frontend in `frontend/src/`. We're building the trip planning UI, minus the daily log sheet (that's the next step).

## src/api.js

- Export `planTrip(payload)` that POSTs to `import.meta.env.VITE_API_URL + '/api/plan-trip/'` and returns `response.data`
- Use axios with 60-second timeout

## src/App.jsx — top-level layout

- Title bar: "Spotter ELD — Trip Planner"
- Two-column layout on desktop (form left, results right), single column on mobile
- State: `loading`, `error`, `tripData`
- On form submit, call `planTrip`, set `tripData`; show error inline on failure

## src/components/TripForm.jsx

- Controlled form: `current_location`, `pickup_location`, `dropoff_location` (text inputs), `cycle_used_hours` (number, 0-70 step 0.5)
- "Plan Trip" button, disabled while loading, shows spinner when loading
- Sensible default values prefilled so the demo works in one click: `"Los Angeles, CA"`, `"Phoenix, AZ"`, `"Dallas, TX"`, `20`
- Inline validation: all 3 locations non-empty, cycle hours numeric 0-70

## src/components/RouteMap.jsx

- Use `react-leaflet` (`MapContainer`, `TileLayer`, `Polyline`, `Marker`, `Popup`)
- OpenStreetMap tiles: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` with attribution
- Draw the route polyline from `tripData.route.geometry` (remember: geometry is `[lon, lat]`, Leaflet wants `[lat, lon]` — swap them)
- Place markers at the 3 waypoints with popups showing their labels
- Fit bounds to the polyline on mount
- Import `'leaflet/dist/leaflet.css'` in `main.jsx`

## src/components/TripSummary.jsx

- Show summary stats (total miles, total driving hours, total trip hours, days) in a clean card layout
- Below: a stops table — type, at-mile, duration

## src/styles.css

- Clean, modern look. Use a system font stack, generous spacing, max-width 1400px centered container.
- Color palette: navy primary (`#1e3a8a`), white background, subtle gray borders, accent yellow (`#fbbf24`) for highlights — mirrors the FMCSA guide aesthetic the assessment shows.
- Mobile-responsive (stack columns under 900px).

## Misc

Create `.env.example` with `VITE_API_URL=http://localhost:8000`

## Test

Run `npm run dev`, point at a local Django backend at `:8000`, submit the default form, confirm map renders with route and markers, summary populates.

Don't build `DailyLogSheet` yet — leave a placeholder div that says "Daily logs render here".
