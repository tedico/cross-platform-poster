from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.tick import run_tick

CFG = {"useful-math": {"platforms": {
    "youtube-shorts": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
}}}
NOW = datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)  # 12:00 EDT
ENV = {"db_id": "db1", "project_names": {"useful-math": "Useful Math"}}


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
    mark = mocker.patch("src.tick.mark_posting")
    record = mocker.patch("src.tick.record_result")
    postiz = MagicMock()
    postiz.integration_ids.return_value = {"youtube": "int-yt", "instagram": "int-ig"}
    postiz.upload.return_value = {"id": "m1", "path": "/up/hua.mp4"}
    postiz.create_post.return_value = {"id": "post-1"}
    return mark, record, postiz


def test_happy_path_posts_and_records(mocker, tmp_path):
    mark, record, postiz = _wire(mocker, _row())
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=postiz, now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 0
    mark.assert_called_once()
    postiz.create_post.assert_called_once()
    assert record.call_args.kwargs["url"]


def test_empty_queue_is_silent_success(mocker, tmp_path):
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=MagicMock(), now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 0


def test_postiz_failure_records_error_and_exits_nonzero(mocker, tmp_path):
    mark, record, postiz = _wire(mocker, _row())
    postiz.create_post.side_effect = Exception("boom")
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=postiz, now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 1
    assert record.call_args.kwargs["error"]


def test_dry_run_never_touches_postiz_or_status(mocker, tmp_path):
    mark, record, postiz = _wire(mocker, _row())
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=postiz, now=NOW,
                    stamp_dir=tmp_path, dry_run=True)
    assert code == 0
    postiz.upload.assert_not_called()
    postiz.create_post.assert_not_called()
    mark.assert_not_called()
    record.assert_not_called()
    assert not (tmp_path / "last_tick").exists()  # dry run must not vouch for liveness


def test_writes_last_tick_stamp(mocker, tmp_path):
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    run_tick(CFG, ENV, notion=MagicMock(), postiz=MagicMock(), now=NOW,
             stamp_dir=tmp_path, dry_run=False)
    assert (tmp_path / "last_tick").exists()


def test_stuck_posting_row_exits_nonzero(mocker, tmp_path):
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[_row()])
    record = mocker.patch("src.tick.record_result")
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=MagicMock(), now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 1
    record.assert_called_once()


def test_fresh_posting_row_not_swept(mocker, tmp_path):
    row = _row()
    row["last_edited_time"] = "2026-07-08T15:50:00.000Z"  # 10 min before NOW
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[row])
    record = mocker.patch("src.tick.record_result")
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=MagicMock(), now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 0
    record.assert_not_called()


def test_notion_outage_prints_crash_line(mocker, tmp_path, capsys):
    mocker.patch("src.tick.find_stuck_posting",
                 side_effect=RuntimeError("notion 503"))
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=MagicMock(), now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 1
    assert "TICK CRASHED" in capsys.readouterr().out
    assert not (tmp_path / "last_tick").exists()  # watchdog must fire too


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
    postiz = MagicMock()
    postiz.integration_ids.return_value = {"youtube": "int-yt", "instagram": "int-ig"}
    postiz.upload.return_value = {"id": "m1", "path": "/up/hua.mp4"}
    postiz.create_post.return_value = {"id": "post-1"}

    code = run_tick(cfg, ENV, notion=notion, postiz=postiz, now=NOW,
                    stamp_dir=tmp_path, dry_run=False)

    assert code == 0
    assert postiz.create_post.call_count == 2
    assert page["properties"]["Status"]["select"]["name"] == "Posted"
    links = "".join(t.get("plain_text", "")
                    for t in page["properties"]["Posted Links"]["rich_text"])
    assert "youtube-shorts:" in links
    assert "ig-reels:" in links
