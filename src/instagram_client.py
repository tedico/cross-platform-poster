"""Publish a Reel via the Instagram Graph API. IG fetches the video itself
from a PUBLIC video_url (no local file). Long-lived token (~60 days) arrives
from the caller; a scheduled workflow rotates it. The token travels in
request params — every error path sanitizes it out of messages, since tick
stamps exception text into the Notion Error field."""
import time

import requests

GRAPH = "https://graph.facebook.com/v21.0"
TIMEOUT = (10, 60)


class InstagramError(Exception):
    pass


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
    container = _json_or_raise(requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={"media_type": "REELS", "video_url": video_url,
              "caption": caption[:2200], "access_token": access_token},
        timeout=TIMEOUT), "create container", access_token)["id"]

    for _ in range(max_polls):
        status = _json_or_raise(requests.get(
            f"{GRAPH}/{container}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=TIMEOUT), "container status", access_token)["status_code"]
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise InstagramError(f"container {container} -> status ERROR "
                                 "(IG could not process the video_url)")
        time.sleep(poll_seconds)
    else:
        raise InstagramError(
            f"container {container} not ready after {max_polls} polls")

    media = _json_or_raise(requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": container, "access_token": access_token},
        timeout=TIMEOUT), "media_publish", access_token)["id"]

    perm = _json_or_raise(requests.get(
        f"{GRAPH}/{media}",
        params={"fields": "permalink", "access_token": access_token},
        timeout=TIMEOUT), "fetch permalink", access_token)
    return perm.get("permalink") or f"ig:{media}"
