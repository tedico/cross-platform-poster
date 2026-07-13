"""Publish a Reel via the Instagram Graph API. IG fetches the video itself
from a PUBLIC video_url (no local file). Long-lived token (~60 days) arrives
from the caller; a scheduled workflow rotates it. The token travels in
request params — every error path sanitizes it out of messages, since tick
stamps exception text into the Notion Error field. That includes
requests-level exceptions (ConnectionError etc.), which embed the full
request URL — token and all — in their message."""
import time

import requests

GRAPH = "https://graph.facebook.com/v21.0"
TIMEOUT = (10, 60)


class InstagramError(Exception):
    pass


def _request(method, url, *, label: str, token: str, **kwargs):
    try:
        return method(url, timeout=TIMEOUT, **kwargs)
    except requests.RequestException as e:
        raise InstagramError(
            f"{label} -> {str(e).replace(token, '***')}") from None


def _json_or_raise(r, label: str, token: str) -> dict:
    if r.status_code != 200:
        raise InstagramError(
            f"{label} -> HTTP {r.status_code}: "
            + r.text[:300].replace(token, "***"))
    try:
        return r.json()
    except ValueError:
        raise InstagramError(
            f"{label} -> non-JSON response: "
            + r.text[:300].replace(token, "***")) from None


def post(video_url: str, caption: str, *, ig_user_id: str, access_token: str,
         poll_seconds: int = 15, max_polls: int = 40) -> str:
    """Create+publish a Reel from a public video URL; return the permalink."""
    container = _json_or_raise(_request(
        requests.post, f"{GRAPH}/{ig_user_id}/media",
        label="create container", token=access_token,
        data={"media_type": "REELS", "video_url": video_url,
              "caption": caption[:2200], "access_token": access_token},
    ), "create container", access_token)["id"]

    for i in range(max_polls):
        status = _json_or_raise(_request(
            requests.get, f"{GRAPH}/{container}",
            label="container status", token=access_token,
            params={"fields": "status_code", "access_token": access_token},
        ), "container status", access_token)["status_code"]
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise InstagramError(f"container {container} -> status ERROR "
                                 "(IG could not process the video_url)")
        if i < max_polls - 1:
            time.sleep(poll_seconds)
    else:
        raise InstagramError(
            f"container {container} not ready after {max_polls} polls")

    media = _json_or_raise(_request(
        requests.post, f"{GRAPH}/{ig_user_id}/media_publish",
        label="media_publish", token=access_token,
        data={"creation_id": container, "access_token": access_token},
    ), "media_publish", access_token)["id"]

    # Published successfully — nothing past this point may raise, or the row
    # would go Failed while the Reel is LIVE (re-Ready => double-post).
    try:
        perm = _json_or_raise(_request(
            requests.get, f"{GRAPH}/{media}",
            label="fetch permalink", token=access_token,
            params={"fields": "permalink", "access_token": access_token},
        ), "fetch permalink", access_token)
        return perm.get("permalink") or f"ig:{media}"
    except InstagramError:
        return f"ig:{media}"  # published fine; permalink is cosmetic
