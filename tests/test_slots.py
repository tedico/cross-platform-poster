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


def test_slot_not_due_other_time():
    now = datetime(2026, 7, 8, 16, 15, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == []


def test_tick_time_quantized_down():
    # 16:07 UTC quantizes to the 16:00 tick -> 12:00 ET slot is due
    now = datetime(2026, 7, 8, 16, 7, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "youtube-shorts")]


def test_evening_slot_in_local_tz():
    # 18:30 ET == 22:30 UTC in July
    now = datetime(2026, 7, 8, 22, 30, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "ig-reels")]


def test_rejects_naive_datetime():
    with pytest.raises(ValueError, match="aware"):
        due_slots(CFG, datetime(2026, 7, 8, 16, 0))
