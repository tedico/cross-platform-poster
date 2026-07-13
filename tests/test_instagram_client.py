import pytest

from src.instagram_client import InstagramError, post


def _resp(mocker, payload, status=200):
    r = mocker.MagicMock(status_code=status)
    r.json.return_value = payload
    r.text = str(payload)
    return r


def test_post_happy_path_returns_permalink(mocker):
    posts = [_resp(mocker, {"id": "c1"}), _resp(mocker, {"id": "m1"})]
    gets = [_resp(mocker, {"status_code": "FINISHED"}),
            _resp(mocker, {"permalink": "https://www.instagram.com/reel/AB12/"})]
    mocker.patch("src.instagram_client.requests.post", side_effect=posts)
    mocker.patch("src.instagram_client.requests.get", side_effect=gets)
    mocker.patch("src.instagram_client.time.sleep")
    url = post("https://a/hua.mp4", "cap", ig_user_id="u1", access_token="tok")
    assert url == "https://www.instagram.com/reel/AB12/"


def test_post_container_error_raises(mocker):
    mocker.patch("src.instagram_client.requests.post",
                 side_effect=[_resp(mocker, {"id": "c1"})])
    mocker.patch("src.instagram_client.requests.get",
                 side_effect=[_resp(mocker, {"status_code": "ERROR"})])
    mocker.patch("src.instagram_client.time.sleep")
    with pytest.raises(InstagramError, match="ERROR"):
        post("https://a/x.mp4", "c", ig_user_id="u1", access_token="tok")


def test_post_timeout_raises_after_max_polls(mocker):
    mocker.patch("src.instagram_client.requests.post",
                 side_effect=[_resp(mocker, {"id": "c1"})])
    mocker.patch("src.instagram_client.requests.get",
                 return_value=_resp(mocker, {"status_code": "IN_PROGRESS"}))
    mocker.patch("src.instagram_client.time.sleep")
    with pytest.raises(InstagramError, match="not ready"):
        post("https://a/x.mp4", "c", ig_user_id="u1", access_token="tok",
             max_polls=3)


def test_token_never_in_connection_error(mocker):
    import requests as real_requests
    mocker.patch("src.instagram_client.requests.post",
                 side_effect=real_requests.exceptions.ConnectionError(
                     "Max retries exceeded with url: /media?access_token=SECRETTOK"))
    with pytest.raises(InstagramError) as exc:
        post("https://a/x.mp4", "c", ig_user_id="u1", access_token="SECRETTOK")
    assert "SECRETTOK" not in str(exc.value)


def test_permalink_failure_still_returns_media_id(mocker):
    import requests as real_requests
    posts = [_resp(mocker, {"id": "c1"}), _resp(mocker, {"id": "m1"})]
    gets = [_resp(mocker, {"status_code": "FINISHED"}),
            real_requests.exceptions.ConnectionError("boom")]
    mocker.patch("src.instagram_client.requests.post", side_effect=posts)
    mocker.patch("src.instagram_client.requests.get", side_effect=gets)
    mocker.patch("src.instagram_client.time.sleep")
    url = post("https://a/x.mp4", "c", ig_user_id="u1", access_token="tok")
    assert url == "ig:m1"


def test_token_never_in_error_text(mocker):
    bad = _resp(mocker, {"error": {"message": "bad request"}}, status=400)
    bad.text = "boom access_token=SECRETTOK details"
    mocker.patch("src.instagram_client.requests.post", return_value=bad)
    with pytest.raises(InstagramError) as exc:
        post("https://a/x.mp4", "c", ig_user_id="u1", access_token="SECRETTOK")
    assert "SECRETTOK" not in str(exc.value)
