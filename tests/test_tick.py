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
