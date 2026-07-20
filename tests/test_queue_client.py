from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.queue_client import (
    find_due_dated_row, find_due_row, mark_posting, record_result,
    parse_posted_links, row_fields,
)


def _page(page_id="p1", status="Ready", platforms=("youtube-shorts", "ig-reels"),
          posted_links="", assets="https://a/x.mp4", title="Hua Luogeng",
          caption="cap", asset_type="video", publish_at=None):
    page = {
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
    # Only rows created after the schema change carry the property at all —
    # the default page mimics a pre-schema-change row (property missing).
    if publish_at is not None:
        page["properties"]["Publish Date & Time"] = {"date": {"start": publish_at}}
    return page


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


def test_row_fields_missing_publish_property_is_none():
    """Rows created before the schema change lack the property entirely."""
    page = _page()
    assert "Publish Date & Time" not in page["properties"]  # guard the premise
    assert row_fields(page)["publish_at"] is None


def test_row_fields_cleared_publish_date_is_none():
    page = _page()
    page["properties"]["Publish Date & Time"] = {"date": None}  # date cleared
    assert row_fields(page)["publish_at"] is None


def test_row_fields_publish_at_present():
    f = row_fields(_page(publish_at="2026-07-22T23:59:00.000-04:00"))
    assert f["publish_at"] == "2026-07-22T23:59:00.000-04:00"


def test_find_due_row_filters_out_dated_rows():
    """--force must never drain a dated row — server-side is_empty."""
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    find_due_row(client, "db1", "Useful Math", "youtube-shorts")
    conds = client.databases.query.call_args.kwargs["filter"]["and"]
    assert {"property": "Publish Date & Time", "date": {"is_empty": True}} in conds


NOW = datetime(2026, 7, 23, 4, 30, tzinfo=timezone.utc)


def test_find_due_dated_row_returns_overdue_row():
    client = MagicMock()
    client.databases.query.return_value = {
        "results": [_page("d1", publish_at="2026-07-22T23:59:00.000-04:00")]}
    row = find_due_dated_row(client, "db1", "Useful Math", "youtube-shorts", NOW)
    assert row["id"] == "d1"
    kwargs = client.databases.query.call_args.kwargs
    assert kwargs["sorts"] == [
        {"property": "Publish Date & Time", "direction": "ascending"}]
    conds = kwargs["filter"]["and"]
    assert {"property": "Publish Date & Time",
            "date": {"on_or_before": NOW.isoformat()}} in conds


def test_find_due_dated_row_skips_future_row_client_side():
    """Even if Notion's murky floating-time filter returns a future row, the
    client-side check must reject it."""
    client = MagicMock()
    client.databases.query.return_value = {
        "results": [_page("fut", publish_at="2026-07-24T12:00:00.000-04:00")]}
    assert find_due_dated_row(client, "db1", "Useful Math",
                              "youtube-shorts", NOW) is None


def test_find_due_dated_row_respects_posted_links():
    client = MagicMock()
    client.databases.query.return_value = {"results": [
        _page("done", publish_at="2026-07-21T12:00:00.000-04:00",
              posted_links="youtube-shorts: https://yt/1"),
        _page("fresh", publish_at="2026-07-22T12:00:00.000-04:00"),
    ]}
    row = find_due_dated_row(client, "db1", "Useful Math", "youtube-shorts", NOW)
    assert row["id"] == "fresh"


def test_floating_publish_at_is_interpreted_as_eastern():
    """A floating (offset-less) datetime means America/New_York: 23:59 EDT is
    03:59 UTC next day — overdue at 04:30Z, not yet at 03:30Z."""
    client = MagicMock()
    client.databases.query.return_value = {
        "results": [_page("f1", publish_at="2026-07-22T23:59:00")]}
    overdue = datetime(2026, 7, 23, 4, 30, tzinfo=timezone.utc)
    not_yet = datetime(2026, 7, 23, 3, 30, tzinfo=timezone.utc)
    assert find_due_dated_row(client, "db1", "Useful Math",
                              "youtube-shorts", overdue)["id"] == "f1"
    assert find_due_dated_row(client, "db1", "Useful Math",
                              "youtube-shorts", not_yet) is None
