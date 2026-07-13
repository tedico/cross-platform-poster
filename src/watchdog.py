"""Daily health check, run by its own Zo automation (6:30 AM ET). Non-zero
exit + printed message = the automation SMSes Ted. Checks: (1) the tick's
stamp file is fresh, (2) no rows stuck in Posting, (3) on the 1st of the
month, force a heartbeat SMS proving this watchdog itself is alive."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from src.queue_client import find_stuck_posting
from src.tick import STAMP_DIR, STUCK_AGE

MAX_STAMP_AGE_SECONDS = 45 * 60  # three missed ticks


def check(notion, db_id: str, stamp_dir=STAMP_DIR, now=None) -> tuple:
    now = now or datetime.now(timezone.utc)
    problems = []
    stamp = Path(stamp_dir) / "last_tick"
    if not stamp.exists():
        problems.append("poster tick has NEVER run (no stamp file)")
    else:
        try:
            age = (now - datetime.fromisoformat(
                stamp.read_text().strip())).total_seconds()
            if age > MAX_STAMP_AGE_SECONDS:
                problems.append(
                    f"poster tick stamp is stale ({int(age // 60)} min old)")
        except (ValueError, TypeError):
            problems.append("poster tick stamp file is unreadable — inspect "
                            "~/.cross-platform-poster/last_tick")
    # find_stuck_posting returns ALL Posting rows; caller decides age. A row
    # younger than STUCK_AGE may be a live tick mid-flight — not a problem.
    stuck = [p for p in find_stuck_posting(notion, db_id)
             if now - datetime.fromisoformat(
                 p["last_edited_time"].replace("Z", "+00:00")) > STUCK_AGE]
    if stuck:
        problems.append(f"{len(stuck)} row(s) stuck in Posting")
    if problems:
        return 1, "cross-platform-poster WATCHDOG: " + "; ".join(problems)
    if now.day == 1:
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
