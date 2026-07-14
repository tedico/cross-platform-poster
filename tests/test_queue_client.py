from unittest.mock import MagicMock

import pytest

from src.queue_client import (
    find_due_row, mark_posting, record_result, parse_posted_links, row_fields,
)


def _page(page_id="p1", status="Ready", platforms=("youtube-shorts", "ig-reels"),
          posted_links="", assets="https://a/x.mp4", title="Hua Luogeng",
          caption="cap", asset_type="video"):
    return {
        "id": page_id,
        "properties": {
            "Title": {"title": [{"plain_text": title}]},
            "Project": {"select": {"name": "Useful Math"}},
            "Asset URL(s)": {"rich_text": [{"plain_text": assets}]},
            "Asset Type": {"select": {"name": asset_type}},
            "Caption": {"rich_text": [{"plain_text": caption}]},
            "Platforms": {"multi_select": [{"name": p} for p in platforms]},
            "Status": {"select": {"name": status}},
            "Posted Links": {"rich_text": [{"plain_text": posted_links}] if posted_links else []},
            "Error": {"rich_text": []},
        },
    }


def test_find_due_row_picks_oldest_ready(mocker):
    client = MagicMock()
    client.databases.query.return_value = {"results": [_page("old"), _page("new")]}
    row = find_due_row(client, "db1", "Useful Math", "youtube-shorts")
    assert row["id"] == "old"
    kwargs = client.databases.query.call_args.kwargs
    assert kwargs["sorts"] == [{"timestamp": "created_time", "direction": "ascending"}]


def test_find_due_row_skips_already_posted_platform():
    client = MagicMock()
    client.databases.query.return_value = {
        "results": [_page("done", posted_links="youtube-shorts: https://yt/1"), _page("fresh")]
    }
    row = find_due_row(client, "db1", "Useful Math", "youtube-shorts")
    assert row["id"] == "fresh"


def test_find_due_row_none_when_empty():
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    assert find_due_row(client, "db1", "Useful Math", "youtube-shorts") is None


def test_parse_posted_links():
    assert parse_posted_links("youtube-shorts: https://yt/1\nig-reels: https://ig/2") == {
        "youtube-shorts": "https://yt/1", "ig-reels": "https://ig/2"}
    assert parse_posted_links("") == {}


def test_record_result_success_all_done_marks_posted():
    client = MagicMock()
    row = _page(platforms=("youtube-shorts",))
    client.pages.retrieve.return_value = row
    record_result(client, row, "youtube-shorts", url="https://yt/1")
    props = client.pages.update.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Posted"
    assert "youtube-shorts: https://yt/1" in props["Posted Links"]["rich_text"][0]["text"]["content"]


def test_record_result_success_remaining_goes_back_to_ready():
    client = MagicMock()
    row = _page(platforms=("youtube-shorts", "ig-reels"))
    client.pages.retrieve.return_value = row
    record_result(client, row, "youtube-shorts", url="https://yt/1")
    props = client.pages.update.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Ready"


def test_record_result_failure_marks_failed_with_error():
    client = MagicMock()
    row = _page()
    client.pages.retrieve.return_value = row
    record_result(client, row, "ig-reels", error="token expired")
    props = client.pages.update.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Failed"
    assert "ig-reels" in props["Error"]["rich_text"][0]["text"]["content"]


def test_record_result_refetches_page():
    client = MagicMock()
    stale = _page(platforms=("youtube-shorts", "ig-reels"))  # snapshot has no links
    fresh = _page(platforms=("youtube-shorts", "ig-reels"),
                  posted_links="youtube-shorts: https://yt/1")
    client.pages.retrieve.return_value = fresh
    record_result(client, stale, "ig-reels", url="https://ig/2")
    props = client.pages.update.call_args.kwargs["properties"]
    content = props["Posted Links"]["rich_text"][0]["text"]["content"]
    assert "youtube-shorts: https://yt/1" in content
    assert "ig-reels: https://ig/2" in content
    assert props["Status"]["select"]["name"] == "Posted"


def test_record_result_requires_url_or_error():
    client = MagicMock()
    with pytest.raises(ValueError):
        record_result(client, _page(), "ig-reels")


def test_row_fields_extracts_plain_values():
    f = row_fields(_page())
    assert f["title"] == "Hua Luogeng"
    assert f["asset_urls"] == ["https://a/x.mp4"]
    assert f["platforms"] == ["youtube-shorts", "ig-reels"]
