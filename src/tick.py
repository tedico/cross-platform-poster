"""The scheduler tick. Deliberately dumb: config says what's due, Notion holds
all state, Postiz does all platform work. Run by a Zo automation every 15 min;
a non-zero exit + printed summary is the SMS trigger. --dry-run logs what WOULD
post and touches nothing."""
import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from src.assets import download_assets
from src.config_loader import load_channels
from src.postiz_client import (
    PLATFORM_IDENTIFIER, PostizClient, build_settings,
)
from src.queue_client import (
    find_due_row, find_stuck_posting, mark_posting, record_result, row_fields,
)
from src.slots import due_slots

STAMP_DIR = Path.home() / ".cross-platform-poster"


def _publish(notion, postiz, page, platform, dry_run) -> str:
    """Publish one row to one platform. Returns the summary line."""
    fields = row_fields(page)
    if dry_run:
        return (f"DRY-RUN would post '{fields['title']}' -> {platform} "
                f"({len(fields['asset_urls'])} asset(s))")
    mark_posting(notion, page)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            paths = download_assets(fields["asset_urls"], tmp,
                                    token=os.environ.get("ASSET_STORE_TOKEN"))
            media = [postiz.upload(p) for p in paths]
            integration = postiz.integration_ids()[PLATFORM_IDENTIFIER[platform]]
            result = postiz.create_post(
                integration_id=integration,
                content=fields["caption"],
                media_ids=[{"id": m["id"], "path": m.get("path", "")} for m in media],
                settings=build_settings(platform, title=fields["title"]),
            )
    except Exception as e:  # noqa: BLE001 — any failure must stamp the row, not crash the tick
        record_result(notion, page, platform, error=str(e)[:500])
        raise
    url = f"postiz:{result.get('id', 'unknown')}"  # permalink backfilled when Postiz exposes it
    record_result(notion, page, platform, url=url)
    return f"POSTED '{fields['title']}' -> {platform} ({url})"


def run_tick(cfg, env, notion, postiz, now, stamp_dir=STAMP_DIR, dry_run=False) -> int:
    stamp_dir = Path(stamp_dir)
    stamp_dir.mkdir(parents=True, exist_ok=True)
    failures, lines = [], []

    stuck = find_stuck_posting(notion, env["db_id"])
    for page in stuck:
        title = row_fields(page)["title"]
        if not dry_run:
            record_result(notion, page, "(stuck)",
                          error="stuck in Posting — tick crashed mid-flight; "
                                "check the platform for a dupe, then re-Ready")
        failures.append(f"STUCK row '{title}' was in Posting")

    for project, platform in due_slots(cfg, now):
        notion_project = env["project_names"].get(project, project)
        page = find_due_row(notion, env["db_id"], notion_project, platform)
        if page is None:
            continue  # empty queue: silent skip by design
        try:
            lines.append(_publish(notion, postiz, page, platform, dry_run))
        except Exception as e:  # noqa: BLE001
            failures.append(f"FAILED {project}->{platform}: {e}")

    (stamp_dir / "last_tick").write_text(now.isoformat())
    for line in lines:
        print(line)
    if failures:
        print("; ".join(failures))
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    cfg = load_channels(Path(__file__).resolve().parent.parent / "channels.yaml")
    env = {
        "db_id": os.environ["POST_QUEUE_DB_ID"],
        "project_names": {"useful-math": "Useful Math"},
    }
    notion = Client(auth=os.environ["NOTION_TOKEN"])
    postiz = PostizClient(os.environ["POSTIZ_URL"], os.environ["POSTIZ_API_KEY"])
    sys.exit(run_tick(cfg, env, notion, postiz,
                      now=datetime.now(timezone.utc), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
