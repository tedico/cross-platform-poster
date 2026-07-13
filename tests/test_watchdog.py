from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.watchdog import check


def test_fresh_stamp_no_stuck_rows_passes(tmp_path):
    now = datetime.now(timezone.utc)
    (tmp_path / "last_tick").write_text(now.isoformat())
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 0


def test_stale_stamp_fails(tmp_path):
    now = datetime.now(timezone.utc)
    (tmp_path / "last_tick").write_text((now - timedelta(hours=3)).isoformat())
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 1
    assert "stale" in msg


def test_missing_stamp_fails(tmp_path):
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path,
                      now=datetime.now(timezone.utc))
    assert code == 1


def test_fresh_posting_row_not_flagged(tmp_path):
    now = datetime.now(timezone.utc)
    (tmp_path / "last_tick").write_text(now.isoformat())
    notion = MagicMock()
    notion.databases.query.return_value = {"results": [
        {"last_edited_time": (now - timedelta(minutes=5))
            .strftime("%Y-%m-%dT%H:%M:%S.000Z")},
    ]}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 0


def test_old_stuck_row_flagged(tmp_path):
    now = datetime.now(timezone.utc)
    (tmp_path / "last_tick").write_text(now.isoformat())
    notion = MagicMock()
    notion.databases.query.return_value = {"results": [
        {"last_edited_time": (now - timedelta(hours=2))
            .strftime("%Y-%m-%dT%H:%M:%S.000Z")},
    ]}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 1
    assert "stuck in Posting" in msg


def test_unreadable_stamp_reports_problem(tmp_path):
    now = datetime.now(timezone.utc)
    (tmp_path / "last_tick").write_text("garbage")
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 1
    assert "unreadable" in msg


def test_heartbeat_on_first_of_month(tmp_path):
    now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    (tmp_path / "last_tick").write_text(now.isoformat())
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 1  # non-zero so the Zo automation SMSes the heartbeat
    assert "heartbeat" in msg.lower()
