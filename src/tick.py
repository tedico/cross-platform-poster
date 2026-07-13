"""The scheduler tick. Deliberately dumb: config says what's due, Notion holds
all state, the platform clients do all platform work. Run by a Zo automation
every 15 min; a non-zero exit + printed summary is the SMS trigger. --dry-run
logs what WOULD post and touches nothing."""
import argparse
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from src.assets import download_assets
from src.config_loader import load_channels
from src.instagram_client import post as ig_post
from src.queue_client import (
    find_due_row, find_stuck_posting, mark_posting, record_result, row_fields,
)
from src.slots import due_slots
from src.youtube_client import post as yt_post

STAMP_DIR = Path.home() / ".cross-platform-poster"
STUCK_AGE = timedelta(hours=1)  # a Posting row younger than this may be a live tick


def _post_youtube(fields, tmp):
    paths = download_assets(fields["asset_urls"], tmp,
                            token=os.environ.get("ASSET_STORE_TOKEN"))
    return yt_post(paths[0], fields["title"], fields["caption"],
                   client_id=os.environ["YT_CLIENT_ID"],
                   client_secret=os.environ["YT_CLIENT_SECRET"],
                   refresh_token=os.environ["YT_REFRESH_TOKEN"])


def _post_instagram(fields, tmp):
    # IG fetches the video itself — no download; asset URL must be public.
    return ig_post(fields["asset_urls"][0], fields["caption"],
                   ig_user_id=os.environ["IG_USER_ID"],
                   access_token=os.environ["IG_ACCESS_TOKEN"])


PLATFORM_POSTERS = {"youtube-shorts": _post_youtube, "ig-reels": _post_instagram}


def _publish(notion, page, platform, dry_run) -> str:
    """Publish one row to one platform. Returns the summary line."""
    if platform not in PLATFORM_POSTERS:
        # Row stays Ready; the FAILED line SMSes every tick until config is fixed.
        raise ValueError(f"platform '{platform}' is in channels.yaml "
                         f"but has no poster client")
    fields = row_fields(page)
    if dry_run:
        return (f"DRY-RUN would post '{fields['title']}' -> {platform} "
                f"({len(fields['asset_urls'])} asset(s))")
    mark_posting(notion, page)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            url = PLATFORM_POSTERS[platform](fields, tmp)
    except Exception as e:  # noqa: BLE001 — any failure must stamp the row, not crash the tick
        record_result(notion, page, platform, error=str(e)[:500])
        raise
    record_result(notion, page, platform, url=url)
    return f"POSTED '{fields['title']}' -> {platform} ({url})"


def run_tick(cfg, env, notion, now, stamp_dir=STAMP_DIR, dry_run=False) -> int:
    stamp_dir = Path(stamp_dir)
    stamp_dir.mkdir(parents=True, exist_ok=True)
    failures, lines = [], []

    try:
        stuck = find_stuck_posting(notion, env["db_id"])
        for page in stuck:
            edited = datetime.fromisoformat(
                page["last_edited_time"].replace("Z", "+00:00"))
            if now - edited < STUCK_AGE:
                continue  # probably a live tick still working this row
            title = row_fields(page)["title"]
            if not dry_run:
                record_result(
                    notion, page, "(stuck)",
                    error="stuck in Posting >1h — tick likely crashed mid-flight. "
                          "If the post EXISTS on the platform, add 'platform: url' "
                          "to Posted Links BEFORE re-Ready (else it will re-post); "
                          "if absent, just re-Ready.")
            failures.append(f"STUCK row '{title}' was in Posting")

        for project, platform in due_slots(cfg, now):
            if project not in env["project_names"]:
                failures.append(f"CONFIG: project '{project}' missing from "
                                f"project_names mapping")
                continue
            notion_project = env["project_names"][project]
            page = find_due_row(notion, env["db_id"], notion_project, platform)
            if page is None:
                continue  # empty queue: silent skip by design
            try:
                lines.append(_publish(notion, page, platform, dry_run))
            except Exception as e:  # noqa: BLE001
                failures.append(f"FAILED {project}->{platform}: {e}")
    except Exception as e:  # noqa: BLE001 — SMS contract: always print, always exit 1
        # Deliberately skips the stamp write so the freshness watchdog fires too.
        print(f"TICK CRASHED: {e}")
        return 1

    if not dry_run:  # a dry run must not vouch for the real tick's liveness
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
    sys.exit(run_tick(cfg, env, notion,
                      now=datetime.now(timezone.utc), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
