import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

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
