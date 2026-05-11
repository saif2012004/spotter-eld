# Prompt 2 — HOS Simulator (the brain — most important)

Implement the Hours of Service simulator in `backend/planner/services/hos.py`.

This is the most important file in the project. It models FMCSA HOS rules for a property-carrying CMV driver on the 70hr/8day cycle.

## Rules to encode

(FMCSA Interstate Truck Driver's Guide to Hours of Service)

1. **11-hour driving limit**: max 11 hours driving after 10 consecutive hours off duty
2. **14-hour driving window**: cannot drive after the 14th hour following coming on duty
3. **30-minute break**: required after 8 cumulative hours of driving since last 30+ min off-duty/sleeper break
4. **70-hour / 8-day limit**: cannot drive after 70 on-duty hours in any rolling 8-day period
5. **10-hour reset**: 10 consecutive hours off-duty restarts the 11/14 hour clocks

## Assumptions for this app

- Average truck driving speed: 55 mph
- Fuel stop every 1,000 miles, 15 minutes, on-duty (not driving)
- 1 hour at pickup (on-duty not driving)
- 1 hour at dropoff (on-duty not driving)
- No adverse driving conditions

## Public API of the module

```python
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class DutyStatus(str, Enum):
    OFF_DUTY = "off_duty"
    SLEEPER = "sleeper"
    DRIVING = "driving"
    ON_DUTY_NOT_DRIVING = "on_duty_not_driving"

@dataclass
class Event:
    start: datetime          # UTC or naive consistent
    end: datetime
    status: DutyStatus
    location: str            # "En route", "Pickup", "Dropoff", "Fuel stop", "Rest"
    note: str = ""
    miles: float = 0.0       # miles covered during this event (driving only)

def plan_trip(
    start_time: datetime,
    cycle_used_hours: float,       # hours already used in current 70/8 cycle
    miles_to_pickup: float,
    miles_pickup_to_dropoff: float,
) -> list[Event]:
    """
    Simulates the trip event-by-event respecting all HOS rules.
    Returns a chronological list of Event objects spanning from start_time
    until dropoff is complete (including a final off-duty event to close the day).
    """
```

## Algorithm

- Maintain running counters: `drive_hours_since_reset`, `on_duty_hours_since_reset` (the 14hr window), `drive_since_last_break`, `cycle_hours` (the rolling 70).
- Walk through legs in order: drive_to_pickup → pickup (1hr on-duty) → drive_to_dropoff (with fuel stops every 1000 mi) → dropoff (1hr on-duty).
- Before each driving segment, check all 4 limits. If any would be hit mid-segment, split the segment: drive what's allowed, then insert the appropriate rest (30-min break, or 10-hour off-duty reset).
- For 70-hour cycle exhaustion mid-trip, insert a 34-hour restart (off-duty).
- Emit Events for everything, no overlaps, no gaps. End each calendar day cleanly.

## Tests

Then in `backend/planner/tests.py`, write pytest-style Django TestCase tests covering:

- Short trip well within limits (no breaks needed)
- Trip that triggers the 30-min break
- Trip that triggers a 10-hour reset (multi-day trip)
- Driver starts with 65 cycle hours used — should hit 70-hour limit
- Fuel stop inserted at 1000 miles mark
- Pickup and dropoff each consume 1 on-duty hour

Use datetime arithmetic only — no external libs beyond stdlib. Make the function pure and deterministic.

Run the tests with `python manage.py test planner` and confirm they pass before finishing.
