"""Hourly health check, run by its own Zo automation. Non-zero exit + printed
message = the automation SMSes Ted. The tick runs on GitHub Actions (ephemeral
runners — no stamp file), so liveness comes from workflow run history via the
public GitHub API. Checks: (1) a completed tick run exists and is fresh,
(2) no recent failed tick runs, (3) the monthly IG token-refresh workflow is
neither failing nor stale, (4) no rows stuck in Posting, (5) at 6 AM ET on the
1st of the month, force a heartbeat SMS proving this watchdog itself is alive
(hourly runs would otherwise heartbeat 24x)."""
import os
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from notion_client import Client

from src.queue_client import find_stuck_posting
from src.tick import STUCK_AGE

GITHUB_REPO = "tedico/cross-platform-poster"
TICK_WORKFLOW = "tick.yml"
# The cron says */15, but GitHub throttles scheduled workflows hard under
# congestion — observed overnight gaps up to ~2h46 between completed ticks
# (2026-07-23) with every run green. Alarm only past the worst observed lag;
# the queue drains 1 post/day/platform, so hours of tick delay cost nothing.
NO_RUN_ALARM = 240 * 60
# hourly cadence + drift margin; a duplicate SMS about a real failure beats a missed one
FAILURE_WINDOW = 90 * 60


def workflow_run_problems(now, repo=GITHUB_REPO, workflow=TICK_WORKFLOW,
                          label="tick", no_run_alarm=NO_RUN_ALARM,
                          failure_window=FAILURE_WINDOW,
                          flag_no_runs=True) -> list:
    """Freshness + failure problems from a workflow's recent runs (public API).
    Retries once on API blips before alarming."""
    err = None
    for attempt in (1, 2):
        try:
            r = requests.get(
                f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs",
                params={"per_page": 20}, timeout=(10, 30))
            err = (None if r.status_code == 200
                   else f"GitHub API -> HTTP {r.status_code}")
        except requests.RequestException as e:
            err = f"GitHub API unreachable ({e})"
        if err is None:
            break
        if attempt == 1:
            time.sleep(30)  # one retry before alarming — API blips are transient
    if err is not None:
        return [f"{err} (cannot check {label} runs)"]
    runs = r.json().get("workflow_runs", [])
    problems = []
    completed = [x for x in runs if x["status"] == "completed"]
    if not completed:
        if flag_no_runs:
            problems.append(f"{label} workflow has no completed runs")
    elif no_run_alarm is not None:
        newest = datetime.fromisoformat(
            completed[0]["updated_at"].replace("Z", "+00:00"))
        if (now - newest).total_seconds() > no_run_alarm:
            problems.append(
                f"no completed {label} run in "
                f"{int((now - newest).total_seconds() // 60)} min")
    recent_failures = [
        x for x in completed
        if x["conclusion"] not in ("success", "skipped", "cancelled")
        and (now - datetime.fromisoformat(
            x["updated_at"].replace("Z", "+00:00"))).total_seconds() < failure_window]
    if recent_failures:
        problems.append(
            f"{len(recent_failures)} failed {label} run(s) in the last "
            f"{failure_window // 60} min: " + recent_failures[0]["html_url"])
    return problems


def check(notion, db_id: str, now=None) -> tuple:
    now = now or datetime.now(timezone.utc)
    problems = workflow_run_problems(
        now, label="tick", no_run_alarm=NO_RUN_ALARM,
        failure_window=FAILURE_WINDOW, flag_no_runs=True)
    # Monthly token rotation: zero completed runs pre-first-run is legitimate,
    # hence flag_no_runs=False. Once it HAS run, staleness >35 days means GitHub
    # auto-disabled the schedule or the PAT died — either silently kills IG
    # posting ~25 days later, so it must alarm here.
    problems += workflow_run_problems(
        now, workflow="refresh-ig-token.yml", label="ig-token-refresh",
        no_run_alarm=35 * 24 * 3600,   # monthly cadence; stale >35 days = auto-disabled or dead PAT
        failure_window=2 * 3600, flag_no_runs=False)
    # find_stuck_posting returns ALL Posting rows; caller decides age. A row
    # younger than STUCK_AGE may be a live tick mid-flight — not a problem.
    stuck = [p for p in find_stuck_posting(notion, db_id)
             if now - datetime.fromisoformat(
                 p["last_edited_time"].replace("Z", "+00:00")) > STUCK_AGE]
    if stuck:
        problems.append(f"{len(stuck)} row(s) stuck in Posting")
    if problems:
        return 1, "cross-platform-poster WATCHDOG: " + "; ".join(problems)
    if now.day == 1 and now.astimezone(ZoneInfo("America/New_York")).hour == 6:
        return 1, ("cross-platform-poster watchdog heartbeat: all healthy. "
                   "(Monthly proof-of-life — no action needed.)")
    return 0, "healthy"


def main():
    load_dotenv()
    notion = Client(auth=os.environ["NOTION_TOKEN"])
    code, msg = check(notion, os.environ["POST_QUEUE_DB_ID"])
    print(msg)
    sys.exit(code)


if __name__ == "__main__":
    main()
