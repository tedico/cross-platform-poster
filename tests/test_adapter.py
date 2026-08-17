import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

spec = importlib.util.spec_from_file_location(
    "post_queue_adapter", Path("adapter/post_queue_adapter.py"))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_enqueue_creates_row_with_ready_when_auto():
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    adapter.enqueue(client, "db1", project="Useful Math", title="Hua Luogeng",
                    asset_urls=["https://a/hua.mp4"], caption="cap",
                    platforms=["youtube-shorts", "ig-reels"], gate="auto")
    props = client.pages.create.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Ready"
    assert props["Asset Type"]["select"]["name"] == "video"


def test_enqueue_gated_creates_awaiting_approval():
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    adapter.enqueue(client, "db1", project="X", title="t",
                    asset_urls=["https://a/i1.png", "https://a/i2.png"],
                    caption="c", platforms=["ig-carousel"], gate="gated")
    props = client.pages.create.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Awaiting Approval"
    assert props["Asset Type"]["select"]["name"] == "image-set"


def test_enqueue_dedups_on_existing_asset_url():
    client = MagicMock()
    client.databases.query.return_value = {"results": [{"id": "existing"}]}
    out = adapter.enqueue(client, "db1", project="Useful Math", title="t",
                          asset_urls=["https://a/hua.mp4"], caption="c",
                          platforms=["youtube-shorts"], gate="auto")
    assert out is None
    client.pages.create.assert_not_called()


def test_enqueue_rejects_empty_platforms():
    client = MagicMock()
    with pytest.raises(ValueError):
        adapter.enqueue(client, "db1", project="X", title="t",
                        asset_urls=["https://a/hua.mp4"], caption="c",
                        platforms=[], gate="auto")
    client.databases.query.assert_not_called()  # guard runs before any API call


def test_enqueue_rejects_bad_gate():
    client = MagicMock()
    with pytest.raises(ValueError):
        adapter.enqueue(client, "db1", project="X", title="t",
                        asset_urls=["https://a/hua.mp4"], caption="c",
                        platforms=["youtube-shorts"], gate="manual")
    client.databases.query.assert_not_called()


def test_long_caption_survives_notions_per_object_limit():
    """Athena's captions run to ~2184 chars — IG allows 2200. A plain
    caption[:2000] slice dropped the sources block and hashtags off the end."""
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    caption = "A" * 2184
    adapter.enqueue(client, "db1", project="Athena", title="t",
            asset_urls=["https://a/1.png", "https://a/2.png"],
            caption=caption, platforms=["ig-carousel"])
    props = client.pages.create.call_args.kwargs["properties"]
    chunks = props["Caption"]["rich_text"]
    assert all(len(c["text"]["content"]) <= 2000 for c in chunks)
    assert "".join(c["text"]["content"] for c in chunks) == caption


def test_image_set_is_detected_for_a_carousel():
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    adapter.enqueue(client, "db1", project="Athena", title="t",
            asset_urls=[f"https://a/card{i}.png" for i in range(1, 8)],
            caption="c", platforms=["ig-carousel"])
    props = client.pages.create.call_args.kwargs["properties"]
    assert props["Asset Type"]["select"]["name"] == "image-set"
    assert props["Asset URL(s)"]["rich_text"][0]["text"]["content"].count(
        "\n") == 6
