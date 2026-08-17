import pytest
import requests

from src.instagram_carousel_client import post
from src.instagram_client import InstagramError

SEVEN = [f"https://a/card{i}.png" for i in range(1, 8)]


def _resp(mocker, payload, status=200):
    r = mocker.MagicMock(status_code=status)
    r.json.return_value = payload
    r.text = str(payload)
    return r


def _happy(mocker, n=7):
    """n child containers, then the parent, then media_publish."""
    posts = [_resp(mocker, {"id": f"c{i}"}) for i in range(n)]
    posts += [_resp(mocker, {"id": "parent"}), _resp(mocker, {"id": "m1"})]
    gets = [_resp(mocker, {"status_code": "FINISHED"}),
            _resp(mocker, {"permalink": "https://www.instagram.com/p/AB12/"})]
    p = mocker.patch("src.instagram_carousel_client.requests.post",
                     side_effect=posts)
    g = mocker.patch("src.instagram_carousel_client.requests.get",
                     side_effect=gets)
    mocker.patch("src.instagram_carousel_client.time.sleep")
    return p, g


def test_post_happy_path_returns_permalink(mocker):
    _happy(mocker)
    url = post(SEVEN, "cap", ig_user_id="u1", access_token="tok")
    assert url == "https://www.instagram.com/p/AB12/"


def test_every_card_becomes_a_child_container_in_order(mocker):
    p, _ = _happy(mocker)
    post(SEVEN, "cap", ig_user_id="u1", access_token="tok")
    child_calls = p.call_args_list[:7]
    assert [c.kwargs["data"]["image_url"] for c in child_calls] == SEVEN
    assert all(c.kwargs["data"]["is_carousel_item"] == "true"
               for c in child_calls)
    # A child must NOT carry the caption — only the parent does.
    assert all("caption" not in c.kwargs["data"] for c in child_calls)


def test_parent_carries_children_in_order_and_the_caption(mocker):
    p, _ = _happy(mocker)
    post(SEVEN, "the caption", ig_user_id="u1", access_token="tok")
    parent = p.call_args_list[7].kwargs["data"]
    assert parent["media_type"] == "CAROUSEL"
    assert parent["children"] == "c0,c1,c2,c3,c4,c5,c6"
    assert parent["caption"] == "the caption"


def test_publish_uses_the_parent_container(mocker):
    p, _ = _happy(mocker)
    post(SEVEN, "cap", ig_user_id="u1", access_token="tok")
    assert p.call_args_list[8].kwargs["data"]["creation_id"] == "parent"


def test_caption_is_trimmed_to_instagrams_hard_limit(mocker):
    """2200 is IG's limit — a longer caption is rejected, not truncated."""
    p, _ = _happy(mocker)
    post(SEVEN, "x" * 3000, ig_user_id="u1", access_token="tok")
    assert len(p.call_args_list[7].kwargs["data"]["caption"]) == 2200


@pytest.mark.parametrize("n", [0, 1, 11])
def test_refuses_a_carousel_instagram_would_reject(mocker, n):
    """Fail before any API call rather than burn containers on a bad set."""
    p = mocker.patch("src.instagram_carousel_client.requests.post")
    with pytest.raises(InstagramError, match="2-10 images"):
        post([f"https://a/{i}.png" for i in range(n)], "c",
             ig_user_id="u1", access_token="tok")
    assert p.call_count == 0


def test_container_error_raises(mocker):
    mocker.patch("src.instagram_carousel_client.requests.post",
                 side_effect=[_resp(mocker, {"id": f"c{i}"}) for i in range(7)]
                 + [_resp(mocker, {"id": "parent"})])
    mocker.patch("src.instagram_carousel_client.requests.get",
                 side_effect=[_resp(mocker, {"status_code": "ERROR"})])
    mocker.patch("src.instagram_carousel_client.time.sleep")
    with pytest.raises(InstagramError, match="status ERROR"):
        post(SEVEN, "c", ig_user_id="u1", access_token="tok")


def test_timeout_raises_after_max_polls(mocker):
    mocker.patch("src.instagram_carousel_client.requests.post",
                 side_effect=[_resp(mocker, {"id": f"c{i}"}) for i in range(7)]
                 + [_resp(mocker, {"id": "parent"})])
    mocker.patch("src.instagram_carousel_client.requests.get",
                 return_value=_resp(mocker, {"status_code": "IN_PROGRESS"}))
    mocker.patch("src.instagram_carousel_client.time.sleep")
    with pytest.raises(InstagramError, match="not ready"):
        post(SEVEN, "c", ig_user_id="u1", access_token="tok", max_polls=2)


def test_a_live_post_never_fails_the_row_on_permalink_error(mocker):
    """Past media_publish the carousel is LIVE; raising would re-Ready the row
    and double-post it on the next tick."""
    mocker.patch("src.instagram_carousel_client.requests.post",
                 side_effect=[_resp(mocker, {"id": f"c{i}"}) for i in range(7)]
                 + [_resp(mocker, {"id": "parent"}),
                    _resp(mocker, {"id": "m1"})])
    mocker.patch("src.instagram_carousel_client.requests.get",
                 side_effect=[_resp(mocker, {"status_code": "FINISHED"}),
                              _resp(mocker, {"error": "boom"}, status=500)])
    mocker.patch("src.instagram_carousel_client.time.sleep")
    assert post(SEVEN, "c", ig_user_id="u1",
                access_token="tok") == "ig:m1"


def test_token_never_leaks_into_an_error(mocker):
    """tick stamps exception text into Notion — a leak would persist there."""
    mocker.patch("src.instagram_carousel_client.requests.post",
                 side_effect=requests.ConnectionError(
                     "failed for url: https://graph.instagram.com/"
                     "v21.0/u1/media?access_token=SUPERSECRET"))
    with pytest.raises(InstagramError) as e:
        post(SEVEN, "c", ig_user_id="u1", access_token="SUPERSECRET")
    assert "SUPERSECRET" not in str(e.value)
    assert "***" in str(e.value)
