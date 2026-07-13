"""Hourly health check, run by its own Zo automation. Non-zero exit + printed
message = the automation SMSes Ted. The tick runs on GitHub Actions (ephemeral
runners — no stamp file), so liveness comes from the tick workflow's run
history via the public GitHub API. Checks: (1) a completed tick run exists and
is fresh, (2) no recent failed tick runs, (3) no rows stuck in Posting,
(4) at 6 AM ET on the 1st of the month, force a heartbeat SMS proving this
watchdog itself is alive (hourly runs would otherwise heartbeat 24x)."""
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from notion_client import Client

from src.queue_client import find_stuck_posting
from src.tick import STUCK_AGE

GITHUB_REPO = "tedico/cross-platform-poster"
TICK_WORKFLOW = "tick.yml"
NO_RUN_ALARM = 45 * 60      # three missed 15-min ticks
FAILURE_WINDOW = 60 * 60    # hourly watchdog: alert once per failed run


def tick_run_problems(now, repo=GITHUB_REPO, workflow=TICK_WORKFLOW) -> list:
    """Freshness + failure problems from the workflow's recent runs (public API)."""
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs",
            params={"per_page": 20}, timeout=(10, 30))
    except requests.RequestException as e:
        return [f"GitHub API unreachable ({e}) — cannot check tick runs"]
    if r.status_code != 200:
        return [f"GitHub API -> HTTP {r.status_code} (cannot check tick runs)"]
    runs = r.json().get("workflow_runs", [])
    problems = []
    completed = [x for x in runs if x["status"] == "completed"]
    if not completed:
        problems.append("tick workflow has no completed runs")
    else:
        newest = datetime.fromisoformat(
            completed[0]["updated_at"].replace("Z", "+00:00"))
        if (now - newest).total_seconds() > NO_RUN_ALARM:
            problems.append(
                f"no completed tick run in {int((now - newest).total_seconds() // 60)} min")
    recent_failures = [
        x for x in completed
        if x["conclusion"] not in ("success", "skipped", "cancelled")
        and (now - datetime.fromisoformat(
            x["updated_at"].replace("Z", "+00:00"))).total_seconds() < FAILURE_WINDOW]
    if recent_failures:
        problems.append(
            f"{len(recent_failures)} failed tick run(s) in the last hour: "
            + recent_failures[0]["html_url"])
    return problems


def check(notion, db_id: str, now=None) -> tuple:
    now = now or datetime.now(timezone.utc)
    problems = tick_run_problems(now)
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
