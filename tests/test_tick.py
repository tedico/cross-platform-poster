import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.tick import run_tick

CFG = {"useful-math": {"platforms": {
    "youtube-shorts": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
}}}
NOW = datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)  # 12:00 EDT
ENV = {"db_id": "db1", "project_names": {"useful-math": "Useful Math"}}
POSTER_ENV = {
    "YT_CLIENT_ID": "cid", "YT_CLIENT_SECRET": "csec", "YT_REFRESH_TOKEN": "rtok",
    "IG_USER_ID": "17840000", "IG_ACCESS_TOKEN": "igtok",
}


def _row(platforms=("youtube-shorts",)):
    return {
        "id": "p1",
        "last_edited_time": "2026-07-08T14:00:00.000Z",  # 2h before NOW -> stuck-sweepable
        "properties": {
            "Title": {"title": [{"plain_text": "Hua Luogeng"}]},
            "Project": {"select": {"name": "Useful Math"}},
            "Asset URL(s)": {"rich_text": [{"plain_text": "https://a/hua.mp4"}]},
            "Asset Type": {"select": {"name": "video"}},
            "Caption": {"rich_text": [{"plain_text": "the caption"}]},
            "Platforms": {"multi_select": [{"name": p} for p in platforms]},
            "Status": {"select": {"name": "Ready"}},
            "Posted Links": {"rich_text": []},
            "Error": {"rich_text": []},
        },
    }


def _wire(mocker, row):
    mocker.patch("src.tick.find_due_row", return_value=row)
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    mocker.patch("src.tick.download_assets", return_value=["/tmp/hua.mp4"])
    mocker.patch.dict(os.environ, POSTER_ENV)
    mark = mocker.patch("src.tick.mark_posting")
    record = mocker.patch("src.tick.record_result")
    yt = mocker.patch("src.tick.yt_post",
                      return_value="https://youtube.com/shorts/vid1")
    ig = mocker.patch("src.tick.ig_post",
                      return_value="https://www.instagram.com/reel/AB/")
    return mark, record, yt, ig


def test_happy_path_posts_and_records(mocker, tmp_path):
    mark, record, yt, ig = _wire(mocker, _row())
    code = run_tick(CFG, ENV, notion=MagicMock(), now=NOW, dry_run=False)
    assert code == 0
    mark.assert_called_once()
    yt.assert_called_once()
    assert record.call_args.kwargs["url"] == "https://youtube.com/shorts/vid1"


def test_empty_queue_is_silent_success(mocker, tmp_path):
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    code = run_tick(CFG, ENV, notion=MagicMock(), now=NOW, dry_run=False)
    assert code == 0


def test_poster_failure_records_error_and_exits_nonzero(mocker, tmp_path):
    mark, record, yt, ig = _wire(mocker, _row())
    yt.side_effect = Exception("boom")
    code = run_tick(CFG, ENV, notion=MagicMock(), now=NOW, dry_run=False)
    assert code == 1
    assert record.call_args.kwargs["error"]


def test_dry_run_never_touches_platforms_or_status(mocker, tmp_path):
    mark, record, yt, ig = _wire(mocker, _row())
    code = run_tick(CFG, ENV, notion=MagicMock(), now=NOW, dry_run=True)
    assert code == 0
    yt.assert_not_called()
    ig.assert_not_called()
    mark.assert_not_called()
    record.assert_not_called()


def test_force_posts_outside_slot_time(mocker, tmp_path):
    """--force ignores slot times: at 03:07 UTC (nowhere near the 12:00 EDT
    slot) the oldest Ready row still posts."""
    mark, record, yt, ig = _wire(mocker, _row())
    off_slot = datetime(2026, 7, 8, 3, 7, tzinfo=timezone.utc)
    code = run_tick(CFG, ENV, notion=MagicMock(), now=off_slot,
                    dry_run=False, force=True)
    assert code == 0
    yt.assert_called_once()
    assert record.call_args.kwargs["url"] == "https://youtube.com/shorts/vid1"


def test_force_with_dry_run_touches_nothing(mocker, tmp_path):
    """force + dry-run composes: previews what WOULD post now, touches nothing."""
    mark, record, yt, ig = _wire(mocker, _row())
    off_slot = datetime(2026, 7, 8, 3, 7, tzinfo=timezone.utc)
    code = run_tick(CFG, ENV, notion=MagicMock(), now=off_slot,
                    dry_run=True, force=True)
    assert code == 0
    yt.assert_not_called()
    ig.assert_not_called()
    mark.assert_not_called()
    record.assert_not_called()


def test_stuck_posting_row_exits_nonzero(mocker, tmp_path):
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[_row()])
    record = mocker.patch("src.tick.record_result")
    code = run_tick(CFG, ENV, notion=MagicMock(), now=NOW, dry_run=False)
    assert code == 1
    record.assert_called_once()


def test_fresh_posting_row_not_swept(mocker, tmp_path):
    row = _row()
    row["last_edited_time"] = "2026-07-08T15:50:00.000Z"  # 10 min before NOW
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[row])
    record = mocker.patch("src.tick.record_result")
    code = run_tick(CFG, ENV, notion=MagicMock(), now=NOW, dry_run=False)
    assert code == 0
    record.assert_not_called()


def test_missing_env_secret_fails_before_marking(mocker, tmp_path, capsys):
    """GH Actions maps an unset secret to an empty string; either way the tick
    must fail BEFORE mark_posting so the row stays Ready."""
    mocker.patch("src.tick.find_due_row", return_value=_row())
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    mocker.patch("src.tick.download_assets", return_value=["/tmp/hua.mp4"])
    mocker.patch.dict(os.environ, {}, clear=True)  # no YT_* secrets at all
    mark = mocker.patch("src.tick.mark_posting")
    record = mocker.patch("src.tick.record_result")
    yt = mocker.patch("src.tick.yt_post")
    code = run_tick(CFG, ENV, notion=MagicMock(), now=NOW, dry_run=False)
    assert code == 1
    mark.assert_not_called()
    record.assert_not_called()
    yt.assert_not_called()
    assert "missing or empty env secret" in capsys.readouterr().out


def test_notion_outage_prints_crash_line(mocker, tmp_path, capsys):
    mocker.patch("src.tick.find_stuck_posting",
                 side_effect=RuntimeError("notion 503"))
    code = run_tick(CFG, ENV, notion=MagicMock(), now=NOW, dry_run=False)
    assert code == 1
    assert "TICK CRASHED" in capsys.readouterr().out


def test_unknown_platform_fails_before_marking(mocker, tmp_path, capsys):
    """A platform in channels.yaml with no poster client: FAILED line + exit 1,
    but the row is untouched (stays Ready) — no mark_posting, no record_result."""
    cfg = {"useful-math": {"platforms": {
        "linkedin": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
    }}}
    mocker.patch("src.tick.find_due_row", return_value=_row(platforms=("linkedin",)))
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    mark = mocker.patch("src.tick.mark_posting")
    record = mocker.patch("src.tick.record_result")
    code = run_tick(cfg, ENV, notion=MagicMock(), now=NOW, dry_run=False)
    assert code == 1
    mark.assert_not_called()
    record.assert_not_called()
    assert "no poster client" in capsys.readouterr().out


def _fake_notion(page):
    """Stateful Notion double over a one-row page store. Translates written
    {"text": {"content": ...}} rich_text back to plain_text on read, like real
    Notion round-trips do."""
    def _readable(prop):
        if isinstance(prop, dict) and "rich_text" in prop:
            return {"rich_text": [
                {"plain_text": t["text"]["content"]} if "text" in t else t
                for t in prop["rich_text"]
            ]}
        return prop

    def query(database_id=None, filter=None, sorts=None, **_):
        status = page["properties"]["Status"]["select"]["name"]
        conds = filter.get("and", [filter])
        for cond in conds:
            if cond.get("property") == "Status" \
                    and cond["select"]["equals"] != status:
                return {"results": []}
        return {"results": [page]}

    def update(page_id=None, properties=None, **_):
        for name, value in properties.items():
            page["properties"][name] = _readable(value)

    notion = MagicMock()
    notion.databases.query.side_effect = query
    notion.pages.retrieve.side_effect = lambda page_id=None, **_: page
    notion.pages.update.side_effect = update
    return notion


def test_same_row_two_platforms_one_tick(mocker, tmp_path):
    """Flagship sequence: one Ready row targeting yt+ig, both slots due in the
    same tick -> two posts, links accumulate, row lands on Posted. Exercises the
    REAL queue_client (nothing from it is patched)."""
    cfg = {"useful-math": {"platforms": {
        "youtube-shorts": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
        "ig-reels": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
    }}}
    page = _row(platforms=("youtube-shorts", "ig-reels"))
    notion = _fake_notion(page)
    mocker.patch("src.tick.download_assets", return_value=["/tmp/hua.mp4"])
    mocker.patch.dict(os.environ, POSTER_ENV)
    yt = mocker.patch("src.tick.yt_post",
                      return_value="https://youtube.com/shorts/vid1")
    ig = mocker.patch("src.tick.ig_post",
                      return_value="https://www.instagram.com/reel/AB/")

    code = run_tick(cfg, ENV, notion=notion, now=NOW, dry_run=False)

    assert code == 0
    yt.assert_called_once()
    ig.assert_called_once()
    assert page["properties"]["Status"]["select"]["name"] == "Posted"
    links = "".join(t.get("plain_text", "")
                    for t in page["properties"]["Posted Links"]["rich_text"])
    assert "youtube-shorts: https://youtube.com/shorts/vid1" in links
    assert "ig-reels: https://www.instagram.com/reel/AB/" in links


def test_partial_failure_preserves_posted_link_and_retries_only_failed(mocker, tmp_path):
    """The double-post protection as one flow: yt posts, ig fails -> row Failed
    but the yt link is preserved; Ted re-Readies; the next tick retries ONLY ig
    (yt link in Posted Links = never re-posted). Real queue_client throughout."""
    cfg = {"useful-math": {"platforms": {
        "youtube-shorts": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
        "ig-reels": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
    }}}
    page = _row(platforms=("youtube-shorts", "ig-reels"))
    notion = _fake_notion(page)
    mocker.patch("src.tick.download_assets", return_value=["/tmp/hua.mp4"])
    mocker.patch.dict(os.environ, POSTER_ENV)
    yt = mocker.patch("src.tick.yt_post",
                      return_value="https://youtube.com/shorts/vid1")
    ig = mocker.patch("src.tick.ig_post", side_effect=Exception("ig down"))

    code = run_tick(cfg, ENV, notion=notion, now=NOW, dry_run=False)

    assert code == 1
    assert page["properties"]["Status"]["select"]["name"] == "Failed"
    links = "".join(t.get("plain_text", "")
                    for t in page["properties"]["Posted Links"]["rich_text"])
    assert "youtube-shorts: https://youtube.com/shorts/vid1" in links

    # Ted's recovery: fix IG, flip the row back to Ready, wait for the next tick.
    page["properties"]["Status"] = {"select": {"name": "Ready"}}
    ig.side_effect = None
    ig.return_value = "https://www.instagram.com/reel/AB/"

    code = run_tick(cfg, ENV, notion=notion, now=NOW, dry_run=False)

    assert code == 0
    assert page["properties"]["Status"]["select"]["name"] == "Posted"
    links = "".join(t.get("plain_text", "")
                    for t in page["properties"]["Posted Links"]["rich_text"])
    assert "youtube-shorts: https://youtube.com/shorts/vid1" in links
    assert "ig-reels: https://www.instagram.com/reel/AB/" in links
    yt.assert_called_once()  # across BOTH ticks — no YT double-post
    assert ig.call_count == 2
