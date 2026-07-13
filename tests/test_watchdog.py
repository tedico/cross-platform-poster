from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.watchdog import check, tick_run_problems

NOW = datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)  # not the 1st


def _gh_response(runs, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"workflow_runs": runs}
    return resp


def _run(updated_at, status="completed", conclusion="success"):
    return {"status": status, "conclusion": conclusion,
            "updated_at": updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "html_url": "https://github.com/tedico/cross-platform-poster/actions/runs/1"}


def _healthy_api(mocker, now):
    return mocker.patch(
        "src.watchdog.requests.get",
        return_value=_gh_response([_run(now - timedelta(minutes=5))]))


def _empty_notion():
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    return notion


def test_recent_successful_run_healthy(mocker):
    _healthy_api(mocker, NOW)
    assert tick_run_problems(NOW) == []
    code, msg = check(_empty_notion(), "db1", now=NOW)
    assert code == 0
    assert msg == "healthy"


def test_no_recent_run_flagged(mocker):
    mocker.patch("src.watchdog.requests.get",
                 return_value=_gh_response([_run(NOW - timedelta(hours=2))]))
    problems = tick_run_problems(NOW)
    assert any("no completed tick run" in p for p in problems)


def test_failed_run_flagged(mocker):
    mocker.patch("src.watchdog.requests.get", return_value=_gh_response([
        _run(NOW - timedelta(minutes=5)),
        _run(NOW - timedelta(minutes=10), conclusion="failure"),
    ]))
    problems = tick_run_problems(NOW)
    assert any("failed tick run" in p for p in problems)
    assert any("https://github.com/" in p for p in problems)


def test_github_api_error_flagged(mocker):
    mocker.patch("src.watchdog.requests.get",
                 return_value=_gh_response([], status_code=500))
    problems = tick_run_problems(NOW)
    assert any("cannot check tick runs" in p for p in problems)


def test_fresh_posting_row_not_flagged(mocker):
    _healthy_api(mocker, NOW)
    notion = MagicMock()
    notion.databases.query.return_value = {"results": [
        {"last_edited_time": (NOW - timedelta(minutes=5))
            .strftime("%Y-%m-%dT%H:%M:%S.000Z")},
    ]}
    code, msg = check(notion, "db1", now=NOW)
    assert code == 0


def test_old_stuck_row_flagged(mocker):
    _healthy_api(mocker, NOW)
    notion = MagicMock()
    notion.databases.query.return_value = {"results": [
        {"last_edited_time": (NOW - timedelta(hours=2))
            .strftime("%Y-%m-%dT%H:%M:%S.000Z")},
    ]}
    code, msg = check(notion, "db1", now=NOW)
    assert code == 1
    assert "stuck in Posting" in msg


def test_heartbeat_on_first_of_month(mocker):
    now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)  # 6:00 AM EDT
    _healthy_api(mocker, now)
    code, msg = check(_empty_notion(), "db1", now=now)
    assert code == 1  # non-zero so the Zo automation SMSes the heartbeat
    assert "heartbeat" in msg.lower()


def test_heartbeat_only_at_6am_et_on_the_first(mocker):
    # hourly watchdog: heartbeat exactly once, in the 6 AM ET run
    noon_et = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)  # 12:00 EDT
    _healthy_api(mocker, noon_et)
    code, msg = check(_empty_notion(), "db1", now=noon_et)
    assert (code, msg) == (0, "healthy")

    six_thirty_et = datetime(2026, 8, 1, 10, 30, tzinfo=timezone.utc)  # 6:30 AM EDT
    _healthy_api(mocker, six_thirty_et)
    code, msg = check(_empty_notion(), "db1", now=six_thirty_et)
    assert code == 1
    assert "heartbeat" in msg.lower()
