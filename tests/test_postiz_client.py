import pytest

from src.postiz_client import PostizClient, PostizError, build_settings


def test_build_settings_youtube_shorts():
    s = build_settings("youtube-shorts", title="Hua Luogeng")
    assert s["title"] == "Hua Luogeng"


def test_build_settings_unknown_platform_raises():
    with pytest.raises(PostizError, match="unknown platform"):
        build_settings("myspace", title="x")


def test_integrations_maps_platform_to_id(mocker):
    client = PostizClient("https://pz.example", "key")
    mocker.patch.object(client, "_get", return_value=[
        {"id": "int-yt", "identifier": "youtube", "name": "Useful Math"},
        {"id": "int-ig", "identifier": "instagram", "name": "useful_math_"},
    ])
    m = client.integration_ids()
    assert m["youtube"] == "int-yt"
    assert m["instagram"] == "int-ig"


def test_create_post_hits_posts_endpoint(mocker):
    client = PostizClient("https://pz.example", "key")
    post = mocker.patch.object(client, "_post", return_value={"id": "post-1"})
    out = client.create_post(integration_id="int-yt", content="cap",
                             media_ids=[{"id": "m1"}], settings={"title": "t"})
    assert out == {"id": "post-1"}
    assert post.call_args.args[0] == "/posts"
    body = post.call_args.args[1]
    assert body["type"] == "now"
    assert body["posts"][0]["integration"]["id"] == "int-yt"


def test_upload_returns_media_descriptor(mocker):
    client = PostizClient("https://pz.example", "key")
    resp = mocker.MagicMock(status_code=200)
    resp.json.return_value = {"id": "m1", "path": "/uploads/x.mp4"}
    mocker.patch("src.postiz_client.requests.post", return_value=resp)
    out = client.upload("tests/test_postiz_client.py")  # any real file path works
    assert out["id"] == "m1"
