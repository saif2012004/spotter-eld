# Prompt 4 — Django Endpoint Wiring Everything Together

Implement the `/api/plan-trip/` endpoint in `backend/planner/views.py` and `backend/planner/urls.py`, plus the request/response serializers.

## Endpoint: POST /api/plan-trip/

### Request body (JSON)

```json
{
  "current_location": "Los Angeles, CA",
  "pickup_location": "Phoenix, AZ",
  "dropoff_location": "Dallas, TX",
  "cycle_used_hours": 20.5,
  "start_time": "2026-05-12T08:00:00"
}
```

`start_time` is optional, defaults to now.

### Response (JSON)

```json
{
  "route": {
    "total_miles": 0.0,
    "geometry": [[-118.24, 34.05], ["..."]],
    "legs": [
      {"from": "...", "to": "...", "miles": 0.0}
    ],
    "waypoints": [
      {"label": "Current", "lat": 0.0, "lon": 0.0, "display_name": "..."},
      {"label": "Pickup",  "lat": 0.0, "lon": 0.0, "display_name": "..."},
      {"label": "Dropoff", "lat": 0.0, "lon": 0.0, "display_name": "..."}
    ]
  },
  "stops": [
    {"type": "fuel | rest_30min | rest_10hr | restart_34hr", "at_mile": 0.0, "duration_hours": 0.0}
  ],
  "daily_logs": [
    {
      "date": "2026-05-12",
      "events": [
        {"start": "08:00", "end": "09:00", "status": "on_duty_not_driving", "location": "Pickup", "note": "..."}
      ],
      "totals": {"off_duty": 7.5, "sleeper": 0, "driving": 10, "on_duty_not_driving": 2.5},
      "miles_today": 0.0
    }
  ],
  "summary": {
    "total_driving_hours": 0.0,
    "total_on_duty_hours": 0.0,
    "total_trip_hours": 0.0,
    "cycle_hours_used_after": 0.0,
    "days": 0
  }
}
```

## Logic in the view

1. Validate input with a DRF serializer (all three locations required, `cycle_used_hours` between 0 and 70, `start_time` optional ISO format).
2. Geocode all three locations.
3. Get OSRM route current → pickup → dropoff.
4. Compute `miles_to_pickup` and `miles_pickup_to_dropoff` from `route.legs`.
5. Call `hos.plan_trip(...)` to get Event list.
6. Group events by calendar day → `daily_logs`.
7. Derive `stops` list from events where status changes for fuel/rest reasons.
8. Compute `summary`.
9. Return `Response(data)`.

## Wiring

Wire up `urls.py`: include `planner.urls` in `trip_planner/urls.py` at path `'api/'`, then `plan-trip/` inside `planner/urls.py`.

Add a try/except wrapper that returns 400 for validation errors, 502 for upstream API failures (Nominatim/OSRM), 500 otherwise, with helpful error messages in the body.

## Test

After implementing, manually test with curl:

```bash
curl -X POST http://localhost:8000/api/plan-trip/ \
  -H "Content-Type: application/json" \
  -d '{"current_location":"Los Angeles, CA","pickup_location":"Phoenix, AZ","dropoff_location":"Dallas, TX","cycle_used_hours":20}'
```

Print the response and confirm the shape matches the spec above.
