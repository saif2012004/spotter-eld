"""
Hours of Service simulator for property-carrying CMV drivers — 70 hr / 8-day cycle.

FMCSA rules encoded:
  1. 11-hour driving limit after 10 consecutive hours off duty
  2. 14-hour on-duty window from coming on duty
  3. 30-minute break after 8 cumulative driving hours since last 30+ min break
  4. 70-hour / 8-day cycle limit
  5. 10-hour off-duty reset restarts clocks 1–3; 34-hour restart resets all four
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPEED_MPH          = 55.0
FUEL_INTERVAL_MI   = 1_000.0
FUEL_STOP_HRS      = 15.0 / 60.0   # 0.25 hr — on-duty not driving

PICKUP_HRS         = 1.0            # on-duty not driving
DROPOFF_HRS        = 1.0            # on-duty not driving

MAX_DRIVE_HRS      = 11.0           # 11-hour driving limit
MAX_WINDOW_HRS     = 14.0           # 14-hour on-duty window
BREAK_TRIGGER_HRS  = 8.0            # cumulative driving hours before mandatory break
BREAK_HRS          = 0.5            # 30-minute break (off-duty)
MAX_CYCLE_HRS      = 70.0           # 70-hour / 8-day cycle
RESET_HRS          = 10.0           # consecutive off-duty hours to restart 11/14 clocks
RESTART_HRS        = 34.0           # off-duty hours to restart the full 70-hr cycle

_EPS               = 1e-6           # float comparison tolerance

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class DutyStatus(str, Enum):
    OFF_DUTY            = "off_duty"
    SLEEPER             = "sleeper"
    DRIVING             = "driving"
    ON_DUTY_NOT_DRIVING = "on_duty_not_driving"


@dataclass
class Event:
    start:    datetime
    end:      datetime
    status:   DutyStatus
    location: str
    note:     str   = ""
    miles:    float = 0.0


# ---------------------------------------------------------------------------
# Internal mutable state
# ---------------------------------------------------------------------------


@dataclass
class _State:
    # Driving hours since last 10-hr reset (limit: MAX_DRIVE_HRS)
    drive_hours: float = 0.0
    # Elapsed wall-clock hours since last 10-hr reset (limit: MAX_WINDOW_HRS).
    # Off-duty breaks within the 14-hr window still count toward this clock.
    window_hours: float = 0.0
    # Driving hours since last 30+ min off-duty break (limit: BREAK_TRIGGER_HRS)
    drive_since_break: float = 0.0
    # On-duty hours accumulated in the rolling 8-day cycle (limit: MAX_CYCLE_HRS)
    cycle_hours: float = 0.0
    # Driving miles since last fuel stop (limit: FUEL_INTERVAL_MI)
    miles_since_fuel: float = 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _on_duty_stop(
    state: _State,
    events: list,
    t: datetime,
    duration: float,
    location: str,
    note: str = "",
) -> datetime:
    """Emit an ON_DUTY_NOT_DRIVING event and advance window + cycle clocks."""
    end = t + timedelta(hours=duration)
    events.append(Event(t, end, DutyStatus.ON_DUTY_NOT_DRIVING, location, note=note))
    state.window_hours += duration
    state.cycle_hours  += duration
    return end


def _rest(
    state: _State,
    events: list,
    t: datetime,
    duration: float,
    note: str,
) -> datetime:
    """Emit an OFF_DUTY event. Caller is responsible for resetting state counters."""
    end = t + timedelta(hours=duration)
    events.append(Event(t, end, DutyStatus.OFF_DUTY, "Rest", note=note))
    return end


def _drive(
    state: _State,
    events: list,
    t: datetime,
    miles: float,
    location: str,
) -> datetime:
    """
    Drive `miles` miles starting at time `t`, inserting HOS-mandated breaks,
    resets, restarts, and fuel stops as required.  Returns the time at which
    the segment is complete.
    """
    remaining = miles

    while remaining > _EPS:
        # ---- available driving hours before each limit ----------------------
        avail_drive  = max(0.0, MAX_DRIVE_HRS      - state.drive_hours)
        avail_window = max(0.0, MAX_WINDOW_HRS      - state.window_hours)
        avail_break  = max(0.0, BREAK_TRIGGER_HRS   - state.drive_since_break)
        avail_cycle  = max(0.0, MAX_CYCLE_HRS       - state.cycle_hours)
        miles_to_fuel = max(0.0, FUEL_INTERVAL_MI   - state.miles_since_fuel)

        can_drive_mi = min(
            remaining,
            avail_drive  * SPEED_MPH,
            avail_window * SPEED_MPH,
            avail_break  * SPEED_MPH,
            avail_cycle  * SPEED_MPH,
            miles_to_fuel,
        )

        # ---- drive the segment (if any) ------------------------------------
        if can_drive_mi > _EPS:
            h   = can_drive_mi / SPEED_MPH
            end = t + timedelta(hours=h)
            events.append(Event(t, end, DutyStatus.DRIVING, location, miles=can_drive_mi))
            state.drive_hours       += h
            state.window_hours      += h
            state.drive_since_break += h
            state.cycle_hours       += h
            state.miles_since_fuel  += can_drive_mi
            remaining               -= can_drive_mi
            t = end
            if remaining <= _EPS:
                break

        # ---- check which limit triggered the stop (priority order) ---------
        at_cycle  = state.cycle_hours       >= MAX_CYCLE_HRS      - _EPS
        at_drive  = state.drive_hours       >= MAX_DRIVE_HRS      - _EPS
        at_window = state.window_hours      >= MAX_WINDOW_HRS     - _EPS
        at_break  = state.drive_since_break >= BREAK_TRIGGER_HRS  - _EPS
        at_fuel   = state.miles_since_fuel  >= FUEL_INTERVAL_MI   - _EPS

        if at_cycle:
            # 34-hour restart resets everything including the 70-hr cycle
            t = _rest(state, events, t, RESTART_HRS, "34-hour restart")
            state.drive_hours       = 0.0
            state.window_hours      = 0.0
            state.drive_since_break = 0.0
            state.cycle_hours       = 0.0

        elif at_drive or at_window:
            # 10-hour off-duty reset restarts the 11-hr and 14-hr clocks
            t = _rest(state, events, t, RESET_HRS, "10-hour reset")
            state.drive_hours       = 0.0
            state.window_hours      = 0.0
            state.drive_since_break = 0.0
            # cycle_hours is NOT reset by a 10-hr break

        elif at_break:
            # Mandatory 30-minute off-duty break.
            # The 14-hr window wall-clock keeps ticking during this break.
            t = _rest(state, events, t, BREAK_HRS, "30-minute break")
            state.window_hours      += BREAK_HRS
            state.drive_since_break  = 0.0

        elif at_fuel:
            # 15-minute fuel stop — on-duty not driving
            t = _on_duty_stop(state, events, t, FUEL_STOP_HRS, "Fuel stop")
            state.miles_since_fuel = 0.0

        else:
            raise RuntimeError(f"No HOS limit triggered but cannot drive. State: {state}")

    return t


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def plan_trip(
    start_time: datetime,
    cycle_used_hours: float,
    miles_to_pickup: float,
    miles_pickup_to_dropoff: float,
) -> list[Event]:
    """
    Simulate a full trip respecting all FMCSA HOS rules.

    Parameters
    ----------
    start_time              : trip start (UTC or naive, must be consistent)
    cycle_used_hours        : on-duty hours already consumed in the 70-hr cycle
    miles_to_pickup         : driving distance from current location to pickup
    miles_pickup_to_dropoff : driving distance from pickup to dropoff

    Returns
    -------
    Chronological list of Event objects with no gaps or overlaps, ending after
    a final 10-hour off-duty rest following dropoff.
    """
    events: list[Event] = []
    state = _State(cycle_hours=float(cycle_used_hours))
    t = start_time

    # 1. Drive to pickup
    t = _drive(state, events, t, miles_to_pickup, "En route")

    # 2. Pickup — 1 hr on-duty not driving
    t = _on_duty_stop(state, events, t, PICKUP_HRS, "Pickup")

    # 3. Drive pickup → dropoff (fuel stops every 1,000 mi handled inside _drive)
    t = _drive(state, events, t, miles_pickup_to_dropoff, "En route")

    # 4. Dropoff — 1 hr on-duty not driving
    t = _on_duty_stop(state, events, t, DROPOFF_HRS, "Dropoff")

    # 5. Final off-duty rest to close the trip log
    _rest(state, events, t, RESET_HRS, "End of trip — 10-hour rest")

    return events
