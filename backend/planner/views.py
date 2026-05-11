import logging
from collections import defaultdict
from datetime import datetime, timedelta

from rest_framework.decorators import api_view
from rest_framework.response import Response

from planner.serializers import PlanTripRequestSerializer
from planner.services.geocoding import GeocodingError, geocode
from planner.services.hos import DutyStatus, plan_trip
from planner.services.routing import RoutingError, get_route

logger = logging.getLogger('planner')

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hours(ev) -> float:
    return (ev.end - ev.start).total_seconds() / 3600


def _round_q(v: float) -> float:
    """Round to nearest quarter-hour (FMCSA standard)."""
    return round(v * 4) / 4


def _fmt_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _split_at_midnight(events):
    """
    Split events that cross calendar-day boundaries so every segment
    belongs to exactly one date.  Miles are distributed proportionally.
    """
    result = []
    for ev in events:
        seg_start = ev.start
        total_secs = (ev.end - ev.start).total_seconds()

        while seg_start < ev.end:
            next_day = seg_start.date() + timedelta(days=1)
            midnight = datetime(next_day.year, next_day.month, next_day.day)
            seg_end = min(ev.end, midnight)

            if total_secs > 0 and ev.miles > 0:
                fraction = (seg_end - seg_start).total_seconds() / total_secs
                seg_miles = ev.miles * fraction
            else:
                seg_miles = 0.0

            result.append(
                ev.__class__(
                    start=seg_start,
                    end=seg_end,
                    status=ev.status,
                    location=ev.location,
                    note=ev.note,
                    miles=seg_miles,
                )
            )
            seg_start = seg_end

    return result


def _group_by_day(events):
    day_map = defaultdict(list)
    for ev in events:
        day_map[ev.start.date()].append(ev)
    return dict(sorted(day_map.items()))


def _build_daily_logs(events, cycle_used_hours: float = 0.0):
    split = _split_at_midnight(events)
    grouped = _group_by_day(split)

    logs = []
    cumulative_on_duty = 0.0  # on-duty hours from earlier days in this trip

    for day, day_events in grouped.items():
        totals = {"off_duty": 0.0, "sleeper": 0.0, "driving": 0.0, "on_duty_not_driving": 0.0}
        miles_today = 0.0

        for ev in day_events:
            h = _hours(ev)
            miles_today += ev.miles
            status_key = ev.status.value
            if status_key in totals:
                totals[status_key] += h

        on_duty_today = totals["driving"] + totals["on_duty_not_driving"]
        prev_7        = cycle_used_hours + cumulative_on_duty
        total_8       = on_duty_today + prev_7
        available     = max(0.0, 70.0 - total_8)

        logs.append(
            {
                "date": day.isoformat(),
                "events": [
                    {
                        "start": _fmt_time(ev.start),
                        "end": _fmt_time(ev.end),
                        "status": ev.status.value,
                        "location": ev.location,
                        "note": ev.note,
                    }
                    for ev in day_events
                ],
                "totals": {k: round(v, 2) for k, v in totals.items()},
                "miles_today": round(miles_today, 2),
                "recap": {
                    "on_duty_hours_today":           _round_q(on_duty_today),
                    "on_duty_hours_previous_7_days": _round_q(prev_7),
                    "total_on_duty_8_days":          _round_q(total_8),
                    "hours_available_tomorrow":      _round_q(available),
                },
            }
        )

        cumulative_on_duty += on_duty_today

    return logs


def _derive_stops(events):
    """
    Walk the event list and emit a stop record for every HOS interruption
    (fuel, 30-min break, 10-hr reset, 34-hr restart).
    `at_mile` is the cumulative driving distance at the moment of the stop.
    """
    _NOTE_TYPE = {
        "30-minute break": "rest_30min",
        "10-hour reset":   "rest_10hr",
        "34-hour restart": "restart_34hr",
    }

    stops = []
    cumulative_miles = 0.0

    for ev in events:
        if ev.status == DutyStatus.DRIVING:
            cumulative_miles += ev.miles
            continue

        stop_type = None
        if ev.location == "Fuel stop" and ev.status == DutyStatus.ON_DUTY_NOT_DRIVING:
            stop_type = "fuel"
        else:
            for fragment, stype in _NOTE_TYPE.items():
                if fragment in ev.note:
                    stop_type = stype
                    break

        if stop_type:
            stops.append(
                {
                    "type": stop_type,
                    "at_mile": round(cumulative_miles, 1),
                    "duration_hours": round(_hours(ev), 4),
                }
            )

    return stops


def _compute_summary(events, start_time: datetime, cycle_used_hours: float):
    # Cycle resets on a 34-hr restart; only hours after the last restart count.
    last_restart_idx = -1
    for i, ev in enumerate(events):
        if "34-hour restart" in ev.note:
            last_restart_idx = i

    post_restart = events[last_restart_idx + 1 :]
    on_duty_after = sum(
        _hours(e)
        for e in post_restart
        if e.status in (DutyStatus.DRIVING, DutyStatus.ON_DUTY_NOT_DRIVING)
    )
    base_cycle = 0.0 if last_restart_idx >= 0 else float(cycle_used_hours)

    total_driving = sum(_hours(e) for e in events if e.status == DutyStatus.DRIVING)
    total_on_duty = sum(
        _hours(e)
        for e in events
        if e.status in (DutyStatus.DRIVING, DutyStatus.ON_DUTY_NOT_DRIVING)
    )

    if events:
        total_trip_hours = (events[-1].end - start_time).total_seconds() / 3600
        start_date = events[0].start.date()
        end_date = events[-1].end.date()
        days = (end_date - start_date).days + 1
    else:
        total_trip_hours = 0.0
        days = 0

    return {
        "total_driving_hours": round(total_driving, 2),
        "total_on_duty_hours": round(total_on_duty, 2),
        "total_trip_hours": round(total_trip_hours, 2),
        "cycle_hours_used_after": round(base_cycle + on_duty_after, 2),
        "days": days,
    }


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


@api_view(["POST"])
def plan_trip_view(request):
    """
    POST /api/plan-trip/

    Geocodes three locations, fetches an OSRM route, runs the HOS simulator,
    and returns a structured trip plan with daily logs and a stops list.
    """
    serializer = PlanTripRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=400)

    data = serializer.validated_data

    # Normalise start_time — strip tz info so the HOS simulator stays naive.
    raw_start = data.get("start_time")
    if raw_start is None:
        start_time = datetime.now()
    elif hasattr(raw_start, "tzinfo") and raw_start.tzinfo is not None:
        start_time = raw_start.replace(tzinfo=None)
    else:
        start_time = raw_start

    # ------------------------------------------------------------------
    # 1. Geocode all three locations
    # ------------------------------------------------------------------
    try:
        current_geo = geocode(data["current_location"])
        pickup_geo  = geocode(data["pickup_location"])
        dropoff_geo = geocode(data["dropoff_location"])
    except GeocodingError as exc:
        logger.warning("Geocoding failed: %s", exc)
        return Response({"error": str(exc), "code": "geocoding_error"}, status=502)
    except Exception as exc:
        logger.error("Unexpected geocoding error: %s", exc, exc_info=True)
        return Response(
            {"error": "Geocoding service unavailable, please try again.", "code": "upstream_error"},
            status=502,
        )

    # ------------------------------------------------------------------
    # 2. Fetch OSRM route: current → pickup → dropoff
    # ------------------------------------------------------------------
    try:
        route = get_route(
            [
                (current_geo["lat"], current_geo["lon"]),
                (pickup_geo["lat"],  pickup_geo["lon"]),
                (dropoff_geo["lat"], dropoff_geo["lon"]),
            ]
        )
    except RoutingError as exc:
        logger.warning("Routing failed: %s", exc)
        return Response({"error": str(exc), "code": "routing_error"}, status=502)
    except Exception as exc:
        logger.error("Unexpected routing error: %s", exc, exc_info=True)
        return Response(
            {"error": "Routing service unavailable, please try again.", "code": "upstream_error"},
            status=502,
        )

    # ------------------------------------------------------------------
    # 3. HOS simulation + response assembly
    # ------------------------------------------------------------------
    try:
        miles_to_pickup          = route["legs"][0]["distance_miles"]
        miles_pickup_to_dropoff  = route["legs"][1]["distance_miles"]

        events = plan_trip(
            start_time,
            float(data["cycle_used_hours"]),
            miles_to_pickup,
            miles_pickup_to_dropoff,
        )

        response_data = {
            "route": {
                "total_miles": round(route["distance_miles"], 2),
                "geometry": route["geometry"],
                "legs": [
                    {
                        "from":  data["current_location"],
                        "to":    data["pickup_location"],
                        "miles": round(route["legs"][0]["distance_miles"], 2),
                    },
                    {
                        "from":  data["pickup_location"],
                        "to":    data["dropoff_location"],
                        "miles": round(route["legs"][1]["distance_miles"], 2),
                    },
                ],
                "waypoints": [
                    {"label": "Current", **current_geo},
                    {"label": "Pickup",  **pickup_geo},
                    {"label": "Dropoff", **dropoff_geo},
                ],
            },
            "stops":      _derive_stops(events),
            "daily_logs": _build_daily_logs(events, float(data["cycle_used_hours"])),
            "summary":    _compute_summary(events, start_time, data["cycle_used_hours"]),
        }

        logger.info(
            "Trip planned: %s → %s → %s | %.1f mi | %d days",
            data["current_location"],
            data["pickup_location"],
            data["dropoff_location"],
            response_data["route"]["total_miles"],
            response_data["summary"]["days"],
        )
        return Response(response_data)

    except Exception as exc:
        logger.error("HOS simulation error: %s", exc, exc_info=True)
        return Response(
            {"error": "An internal error occurred while planning the trip.", "code": "internal_error"},
            status=500,
        )
