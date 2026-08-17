"""Publish an Instagram CAROUSEL (2-10 images) via the Instagram API with
Instagram Login (graph.instagram.com). IG fetches every image itself from a
PUBLIC image_url — no local file, same as the Reels client.

Flow, three API rounds:
  1. one CHILD container per image (`is_carousel_item=true`, no caption)
  2. one PARENT container (`media_type=CAROUSEL`) carrying the child ids and
     the caption
  3. `media_publish` on the parent, then fetch the permalink

The token-sanitizing helpers are imported from `instagram_client` rather than
copied: tick stamps exception text into the Notion Error field, so a leak here
would write the access token into a Notion row. One implementation, one place
to audit.
"""
import time

import requests

from src.instagram_client import (
    GRAPH, InstagramError, _json_or_raise, _request,
)

# Instagram's own limits, not ours: a carousel holds 2-10 items and a caption
# is capped at 2200 characters.
MIN_ITEMS, MAX_ITEMS = 2, 10
CAPTION_LIMIT = 2200


def post(image_urls: list, caption: str, *, ig_user_id: str,
         access_token: str, poll_seconds: int = 5, max_polls: int = 24) -> str:
    """Create+publish an image carousel; return the permalink."""
    if not MIN_ITEMS <= len(image_urls) <= MAX_ITEMS:
        raise InstagramError(
            f"carousel needs {MIN_ITEMS}-{MAX_ITEMS} images, got "
            f"{len(image_urls)}")

    children = []
    for i, url in enumerate(image_urls, 1):
        label = f"create child {i}/{len(image_urls)}"
        children.append(_json_or_raise(_request(
            requests.post, f"{GRAPH}/{ig_user_id}/media",
            label=label, token=access_token,
            data={"image_url": url, "is_carousel_item": "true",
                  "access_token": access_token},
        ), label, access_token)["id"])

    parent = _json_or_raise(_request(
        requests.post, f"{GRAPH}/{ig_user_id}/media",
        label="create carousel container", token=access_token,
        data={"media_type": "CAROUSEL", "children": ",".join(children),
              "caption": caption[:CAPTION_LIMIT],
              "access_token": access_token},
    ), "create carousel container", access_token)["id"]

    # Images usually finish immediately, but a parent carousel can still be
    # IN_PROGRESS; publishing one that is not FINISHED fails the whole post.
    for i in range(max_polls):
        status = _json_or_raise(_request(
            requests.get, f"{GRAPH}/{parent}",
            label="container status", token=access_token,
            params={"fields": "status_code", "access_token": access_token},
        ), "container status", access_token)["status_code"]
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise InstagramError(
                f"carousel container {parent} -> status ERROR (IG could not "
                "fetch or process one of the image_urls)")
        if i < max_polls - 1:
            time.sleep(poll_seconds)
    else:
        raise InstagramError(
            f"carousel container {parent} not ready after {max_polls} polls")

    media = _json_or_raise(_request(
        requests.post, f"{GRAPH}/{ig_user_id}/media_publish",
        label="media_publish", token=access_token,
        data={"creation_id": parent, "access_token": access_token},
    ), "media_publish", access_token)["id"]

    # Published successfully — nothing past this point may raise, or the row
    # would go Failed while the carousel is LIVE (re-Ready => double-post).
    try:
        perm = _json_or_raise(_request(
            requests.get, f"{GRAPH}/{media}",
            label="fetch permalink", token=access_token,
            params={"fields": "permalink", "access_token": access_token},
        ), "fetch permalink", access_token)
        return perm.get("permalink") or f"ig:{media}"
    except InstagramError:
        return f"ig:{media}"  # published fine; permalink is cosmetic
