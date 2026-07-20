from datetime import datetime, timezone

import pytest

from src.slots import due_slots

CFG = {
    "useful-math": {
        "platforms": {
            "youtube-shorts": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
            "ig-reels": {"slot": "18:30", "tz": "America/New_York", "cadence": "daily"},
        }
    }
}


def test_slot_due_at_exact_local_time():
    # 12:00 America/New_York in July == 16:00 UTC (EDT)
    now = datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "youtube-shorts")]


def test_slot_not_due_other_hour():
    # 17:15 UTC == 13:15 ET — a different hour than the 12:00 ET slot
    now = datetime(2026, 7, 8, 17, 15, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == []


def test_slot_due_any_minute_within_hour():
    # 16:07 UTC == 12:07 ET — inside the 12-hour -> 12:00 ET slot is due
    now = datetime(2026, 7, 8, 16, 7, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "youtube-shorts")]


def test_slot_fires_any_minute_within_hour():
    # Last minute of the slot's local hour: 16:59 UTC == 12:59 ET -> due
    now = datetime(2026, 7, 8, 16, 59, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "youtube-shorts")]
    # One minute before the hour opens: 15:59 UTC == 11:59 ET -> not due
    now = datetime(2026, 7, 8, 15, 59, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == []


def test_evening_slot_in_local_tz():
    # 18:30 ET == 22:30 UTC in July
    now = datetime(2026, 7, 8, 22, 30, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "ig-reels")]


def test_rejects_naive_datetime():
    with pytest.raises(ValueError, match="aware"):
        due_slots(CFG, datetime(2026, 7, 8, 16, 0))


DAYS_CFG = {
    "useful-math": {
        "platforms": {
            "youtube-shorts": {"slot": "00:00", "tz": "America/New_York",
                               "cadence": "daily", "days": ["sun"]},
        }
    }
}


def test_days_slot_due_on_listed_weekday():
    # 2026-07-19 is a Sunday; 00:00 ET (EDT) == 04:00 UTC — same Sunday
    now = datetime(2026, 7, 19, 4, 0, tzinfo=timezone.utc)
    assert due_slots(DAYS_CFG, now) == [("useful-math", "youtube-shorts")]


def test_days_slot_not_due_on_other_weekday():
    # 2026-07-20 is a Monday; same local time, wrong day
    now = datetime(2026, 7, 20, 4, 0, tzinfo=timezone.utc)
    assert due_slots(DAYS_CFG, now) == []


def test_days_evaluated_in_slot_timezone_not_utc():
    # Weekday must come from the slot's OWN timezone. Sunday 00:00 ET is
    # Sunday 04:00 UTC — a [sat] slot must NOT fire at that moment even
    # though Saturday was the most recent UTC-adjacent day boundary.
    sat_cfg = {
        "useful-math": {
            "platforms": {
                "youtube-shorts": {"slot": "00:00", "tz": "America/New_York",
                                   "cadence": "daily", "days": ["sat"]},
            }
        }
    }
    now = datetime(2026, 7, 19, 4, 0, tzinfo=timezone.utc)  # Sunday in ET and UTC
    assert due_slots(sat_cfg, now) == []
    # And the [sun] slot IS due at that exact instant (ET weekday wins)
    assert due_slots(DAYS_CFG, now) == [("useful-math", "youtube-shorts")]
