from datetime import datetime, timedelta

from django.test import TestCase

from planner.views import _build_daily_logs, _split_at_midnight
from planner.services.hos import (
    BREAK_HRS,
    BREAK_TRIGGER_HRS,
    DROPOFF_HRS,
    FUEL_INTERVAL_MI,
    FUEL_STOP_HRS,
    MAX_CYCLE_HRS,
    PICKUP_HRS,
    RESET_HRS,
    RESTART_HRS,
    SPEED_MPH,
    DutyStatus,
    plan_trip,
)

_START = datetime(2024, 1, 1, 8, 0, 0)


def _hours(event):
    return (event.end - event.start).total_seconds() / 3600


def _assert_contiguous(test_case, events):
    """Events must be strictly sequential with no gaps or overlaps."""
    for i in range(1, len(events)):
        test_case.assertEqual(
            events[i].start,
            events[i - 1].end,
            f"Gap/overlap between event {i - 1} ({events[i - 1]}) "
            f"and event {i} ({events[i]})",
        )


class ShortTripTest(TestCase):
    """Short trip that fits within all HOS limits — no intermediate breaks needed."""

    def test_no_breaks_or_resets(self):
        # 50 mi to pickup + 100 mi to dropoff = 150 mi total = 2.73 hrs driving
        events = plan_trip(_START, 0.0, 50.0, 100.0)
        _assert_contiguous(self, events)

        off_duty = [e for e in events if e.status == DutyStatus.OFF_DUTY]
        self.assertEqual(len(off_duty), 1, "Only the final rest should be off-duty")
        self.assertEqual(off_duty[0].note, "End of trip — 10-hour rest")

    def test_total_driving_miles(self):
        events = plan_trip(_START, 0.0, 50.0, 100.0)
        total_mi = sum(e.miles for e in events if e.status == DutyStatus.DRIVING)
        self.assertAlmostEqual(total_mi, 150.0, places=3)

    def test_events_are_contiguous(self):
        events = plan_trip(_START, 0.0, 50.0, 100.0)
        _assert_contiguous(self, events)
        self.assertGreater(len(events), 0)


class ThirtyMinBreakTest(TestCase):
    """Break is required after 8 cumulative driving hours since the last rest."""

    def test_break_inserted(self):
        # 0 mi to pickup; 500 mi to dropoff.
        # After pickup (1 hr window used) the driver can drive
        # BREAK_TRIGGER_HRS * 55 = 440 mi before the break fires.
        events = plan_trip(_START, 0.0, 0.0, 500.0)
        _assert_contiguous(self, events)

        breaks = [e for e in events if "30-minute break" in e.note]
        self.assertGreaterEqual(len(breaks), 1, "Expected at least one 30-minute break")

    def test_break_duration(self):
        events = plan_trip(_START, 0.0, 0.0, 500.0)
        breaks = [e for e in events if "30-minute break" in e.note]
        for b in breaks:
            self.assertAlmostEqual(_hours(b), BREAK_HRS, places=4)

    def test_break_fires_at_correct_mileage(self):
        # Drive 440 miles before break, then 60 more after.
        events = plan_trip(_START, 0.0, 0.0, 500.0)
        driving_before_break = []
        for e in events:
            if "30-minute break" in e.note:
                break
            if e.status == DutyStatus.DRIVING:
                driving_before_break.append(e)
        miles_before = sum(e.miles for e in driving_before_break)
        expected = BREAK_TRIGGER_HRS * SPEED_MPH   # 440.0 miles (pickup uses window, not break counter)
        self.assertAlmostEqual(miles_before, expected, places=2)


class TenHourResetTest(TestCase):
    """Long trip forces a 10-hour off-duty reset (multi-day trip)."""

    def test_reset_inserted(self):
        # 700 mi to dropoff > 11-hr limit (605 mi) so a reset is required
        events = plan_trip(_START, 0.0, 0.0, 700.0)
        _assert_contiguous(self, events)

        resets = [e for e in events if "10-hour reset" in e.note]
        self.assertGreaterEqual(len(resets), 1, "Expected at least one 10-hour reset")

    def test_reset_duration(self):
        events = plan_trip(_START, 0.0, 0.0, 700.0)
        for r in [e for e in events if "10-hour reset" in e.note]:
            self.assertAlmostEqual(_hours(r), RESET_HRS, places=4)

    def test_all_miles_covered(self):
        events = plan_trip(_START, 0.0, 0.0, 700.0)
        total_mi = sum(e.miles for e in events if e.status == DutyStatus.DRIVING)
        self.assertAlmostEqual(total_mi, 700.0, places=3)


class CycleExhaustionTest(TestCase):
    """Driver starts with 65 cycle hours — hits 70-hour limit mid-trip."""

    def test_34hr_restart_inserted(self):
        # 5 hrs remaining in cycle = 275 mi; use 400 mi trip → restart fires
        events = plan_trip(_START, 65.0, 0.0, 400.0)
        _assert_contiguous(self, events)

        restarts = [e for e in events if "34-hour restart" in e.note]
        self.assertGreaterEqual(len(restarts), 1, "Expected 34-hour restart")

    def test_restart_duration(self):
        events = plan_trip(_START, 65.0, 0.0, 400.0)
        for r in [e for e in events if "34-hour restart" in e.note]:
            self.assertAlmostEqual(_hours(r), RESTART_HRS, places=4)

    def test_all_miles_covered_after_restart(self):
        events = plan_trip(_START, 65.0, 0.0, 400.0)
        total_mi = sum(e.miles for e in events if e.status == DutyStatus.DRIVING)
        self.assertAlmostEqual(total_mi, 400.0, places=3)

    def test_full_cycle_at_start_triggers_immediate_restart(self):
        # Driver already at 70 hours — cannot drive a single mile without restart
        events = plan_trip(_START, 70.0, 0.0, 100.0)
        restarts = [e for e in events if "34-hour restart" in e.note]
        self.assertGreaterEqual(len(restarts), 1)
        # Restart must come before any driving
        first_drive = next((e for e in events if e.status == DutyStatus.DRIVING), None)
        first_restart = next((e for e in events if "34-hour restart" in e.note), None)
        self.assertIsNotNone(first_drive)
        self.assertLess(first_restart.start, first_drive.start)


class FuelStopTest(TestCase):
    """Fuel stop inserted every 1,000 miles of driving."""

    def test_fuel_stop_present(self):
        # 1,100 mi leg → fuel stop fires somewhere after 1,000 mi
        events = plan_trip(_START, 0.0, 0.0, 1_100.0)
        _assert_contiguous(self, events)

        fuel_stops = [e for e in events if e.location == "Fuel stop"]
        self.assertGreaterEqual(len(fuel_stops), 1, "Expected at least one fuel stop")

    def test_fuel_stop_is_on_duty_not_driving(self):
        events = plan_trip(_START, 0.0, 0.0, 1_100.0)
        for fs in [e for e in events if e.location == "Fuel stop"]:
            self.assertEqual(fs.status, DutyStatus.ON_DUTY_NOT_DRIVING)

    def test_fuel_stop_duration(self):
        events = plan_trip(_START, 0.0, 0.0, 1_100.0)
        for fs in [e for e in events if e.location == "Fuel stop"]:
            self.assertAlmostEqual(_hours(fs), FUEL_STOP_HRS, places=4)

    def test_miles_before_first_fuel_stop(self):
        events = plan_trip(_START, 0.0, 0.0, 1_100.0)
        miles_before = 0.0
        for e in events:
            if e.location == "Fuel stop":
                break
            miles_before += e.miles
        self.assertAlmostEqual(miles_before, FUEL_INTERVAL_MI, places=2)

    def test_two_fuel_stops_for_very_long_trip(self):
        # 2,200 mi → at least 2 fuel stops
        events = plan_trip(_START, 0.0, 0.0, 2_200.0)
        fuel_stops = [e for e in events if e.location == "Fuel stop"]
        self.assertGreaterEqual(len(fuel_stops), 2)


class PickupDropoffTest(TestCase):
    """Pickup and dropoff each consume exactly 1 on-duty hour."""

    def test_pickup_is_one_hour(self):
        events = plan_trip(_START, 0.0, 50.0, 50.0)
        pickup = [e for e in events if e.location == "Pickup"]
        self.assertEqual(len(pickup), 1)
        self.assertAlmostEqual(_hours(pickup[0]), PICKUP_HRS, places=4)

    def test_dropoff_is_one_hour(self):
        events = plan_trip(_START, 0.0, 50.0, 50.0)
        dropoff = [e for e in events if e.location == "Dropoff"]
        self.assertEqual(len(dropoff), 1)
        self.assertAlmostEqual(_hours(dropoff[0]), DROPOFF_HRS, places=4)

    def test_pickup_status_is_on_duty_not_driving(self):
        events = plan_trip(_START, 0.0, 50.0, 50.0)
        pickup = [e for e in events if e.location == "Pickup"][0]
        self.assertEqual(pickup.status, DutyStatus.ON_DUTY_NOT_DRIVING)

    def test_dropoff_status_is_on_duty_not_driving(self):
        events = plan_trip(_START, 0.0, 50.0, 50.0)
        dropoff = [e for e in events if e.location == "Dropoff"][0]
        self.assertEqual(dropoff.status, DutyStatus.ON_DUTY_NOT_DRIVING)

    def test_pickup_immediately_follows_drive_to_pickup(self):
        events = plan_trip(_START, 0.0, 50.0, 50.0)
        _assert_contiguous(self, events)
        # Find pickup event index
        idx = next(i for i, e in enumerate(events) if e.location == "Pickup")
        self.assertGreater(idx, 0)
        self.assertEqual(events[idx - 1].status, DutyStatus.DRIVING)

    def test_exactly_one_pickup_and_one_dropoff(self):
        events = plan_trip(_START, 0.0, 100.0, 200.0)
        self.assertEqual(len([e for e in events if e.location == "Pickup"]),  1)
        self.assertEqual(len([e for e in events if e.location == "Dropoff"]), 1)


class RecapFieldsTest(TestCase):
    """Recap fields are computed correctly per day in _build_daily_logs."""

    def test_recap_keys_present(self):
        events = plan_trip(_START, 0.0, 0.0, 100.0)
        logs = _build_daily_logs(events, cycle_used_hours=0.0)
        for log in logs:
            self.assertIn("recap", log)
            for key in ("on_duty_hours_today", "on_duty_hours_previous_7_days",
                        "total_on_duty_8_days", "hours_available_tomorrow"):
                self.assertIn(key, log["recap"])

    def test_day0_previous_equals_cycle_input(self):
        events = plan_trip(_START, 20.0, 0.0, 100.0)
        logs = _build_daily_logs(events, cycle_used_hours=20.0)
        self.assertEqual(logs[0]["recap"]["on_duty_hours_previous_7_days"], 20.0)

    def test_total_8_days_is_sum(self):
        events = plan_trip(_START, 10.0, 0.0, 100.0)
        logs = _build_daily_logs(events, cycle_used_hours=10.0)
        for log in logs:
            r = log["recap"]
            self.assertAlmostEqual(
                r["total_on_duty_8_days"],
                r["on_duty_hours_today"] + r["on_duty_hours_previous_7_days"],
                places=2,
            )

    def test_hours_available_never_negative(self):
        events = plan_trip(_START, 68.0, 0.0, 400.0)
        logs = _build_daily_logs(events, cycle_used_hours=68.0)
        for log in logs:
            self.assertGreaterEqual(log["recap"]["hours_available_tomorrow"], 0.0)

    def test_multiday_previous_accumulates(self):
        # Multi-day trip: day 1's previous should be cycle_used; day 2's should include day 1 on-duty
        events = plan_trip(_START, 0.0, 0.0, 700.0)
        logs = _build_daily_logs(events, cycle_used_hours=5.0)
        self.assertEqual(logs[0]["recap"]["on_duty_hours_previous_7_days"], 5.0)
        self.assertGreater(
            logs[1]["recap"]["on_duty_hours_previous_7_days"],
            5.0,
            "Day 2 previous-7-days should include day 1 on-duty hours",
        )

    def test_values_rounded_to_quarter_hour(self):
        events = plan_trip(_START, 0.0, 0.0, 300.0)
        logs = _build_daily_logs(events, cycle_used_hours=0.0)
        for log in logs:
            for val in log["recap"].values():
                self.assertEqual(val, round(val * 4) / 4, f"{val} is not a quarter-hour multiple")
