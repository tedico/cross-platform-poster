from unittest.mock import MagicMock

from src.youtube_client import post


def _wire(mocker):
    service = MagicMock()
    request = MagicMock()
    request.next_chunk.side_effect = [(None, None), (None, {"id": "vid123"})]
    service.videos.return_value.insert.return_value = request
    mocker.patch("src.youtube_client._service", return_value=service)
    mocker.patch("src.youtube_client.MediaFileUpload")
    return service


def test_post_returns_shorts_url(mocker, tmp_path):
    _wire(mocker)
    f = tmp_path / "hua.mp4"; f.write_bytes(b"x")
    url = post(f, title="Hua Luogeng", caption="cap",
               client_id="ci", client_secret="cs", refresh_token="rt")
    assert url == "https://youtube.com/shorts/vid123"


def test_post_sends_title_description_public(mocker, tmp_path):
    service = _wire(mocker)
    f = tmp_path / "hua.mp4"; f.write_bytes(b"x")
    post(f, title="T" * 150, caption="the caption",
         client_id="ci", client_secret="cs", refresh_token="rt")
    body = service.videos.return_value.insert.call_args.kwargs["body"]
    assert len(body["snippet"]["title"]) == 100          # truncated
    assert body["snippet"]["description"] == "the caption"
    assert body["status"]["privacyStatus"] == "public"
    assert body["status"]["selfDeclaredMadeForKids"] is False
