import pytest

from src.postiz_client import PostizClient, PostizError, build_settings


def test_build_settings_youtube_shorts():
    s = build_settings("youtube-shorts", title="Hua Luogeng")
    assert s["title"] == "Hua Luogeng"


def test_build_settings_ig_reels():
    assert build_settings("ig-reels") == {"post_type": "post"}


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
    assert body == {
        "type": "now",
        "shortLink": False,
        "posts": [{
            "integration": {"id": "int-yt"},
            "value": [{"content": "cap", "image": [{"id": "m1"}]}],
            "settings": {"title": "t"},
        }],
    }


def test_upload_returns_media_descriptor(mocker, tmp_path):
    client = PostizClient("https://pz.example", "key")
    resp = mocker.MagicMock(status_code=200)
    resp.json.return_value = {"id": "m1", "path": "/uploads/x.mp4"}
    post = mocker.patch("src.postiz_client.requests.post", return_value=resp)
    video = tmp_path / "x.mp4"
    video.write_bytes(b"fake video bytes")
    out = client.upload(str(video))
    assert out["id"] == "m1"
    assert post.call_args.args[0].endswith("/upload")
    assert "file" in post.call_args.kwargs["files"]
