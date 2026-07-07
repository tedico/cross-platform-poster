"""Thin client for the Postiz public API (v1). Postiz owns platform OAuth and
upload mechanics; we own nothing platform-specific except the per-platform
`settings` payloads in build_settings() — the ONE place to adjust after
confirming against docs.postiz.com/public-api (see plan Task 9 Step 4)."""
from pathlib import Path

import requests

GET_TIMEOUT = (10, 30)  # (connect, read)
UPLOAD_TIMEOUT = (10, 300)  # (connect, read) — video uploads are slow


class PostizError(Exception):
    pass


# Per-platform Postiz settings. Provisional until verified against the live
# instance (plan Task 9 Step 4).
def build_settings(platform: str, title: str = "") -> dict:
    if platform == "youtube-shorts":
        # YouTube auto-classifies vertical <3min video as a Short; title required.
        return {"title": title[:100]}
    if platform == "ig-reels":
        return {"post_type": "post"}  # confirm reel setting name against live docs
    raise PostizError(f"unknown platform '{platform}'")


PLATFORM_IDENTIFIER = {"youtube-shorts": "youtube", "ig-reels": "instagram"}


def _json_or_raise(r, label: str):
    try:
        return r.json()
    except ValueError:  # JSONDecodeError subclasses ValueError
        raise PostizError(f"{label} -> non-JSON response: {r.text[:300]}")


class PostizClient:
    def __init__(self, base_url: str, api_key: str):
        self.base = base_url.rstrip("/") + "/api/public/v1"
        self.headers = {"Authorization": api_key}

    def _get(self, path: str):
        r = requests.get(self.base + path, headers=self.headers, timeout=GET_TIMEOUT)
        if r.status_code != 200:
            raise PostizError(f"GET {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return _json_or_raise(r, path)

    def _post(self, path: str, body: dict):
        r = requests.post(self.base + path, headers=self.headers, json=body,
                          timeout=GET_TIMEOUT)
        if r.status_code not in (200, 201):
            raise PostizError(f"POST {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return _json_or_raise(r, path)

    def integration_ids(self) -> dict:
        """Map Postiz platform identifier ('youtube', 'instagram') -> integration id.

        If multiple channels share an identifier (e.g. two YouTube accounts),
        the last one listed wins — v1 assumes one channel per platform.
        """
        return {i["identifier"]: i["id"] for i in self._get("/integrations")}

    def upload(self, file_path) -> dict:
        p = Path(file_path)
        with p.open("rb") as fh:
            r = requests.post(self.base + "/upload", headers=self.headers,
                              files={"file": (p.name, fh)}, timeout=UPLOAD_TIMEOUT)
        if r.status_code not in (200, 201):
            raise PostizError(f"upload -> HTTP {r.status_code}: {r.text[:300]}")
        return _json_or_raise(r, "upload")

    def create_post(self, integration_id: str, content: str,
                    media_ids: list, settings: dict) -> dict:
        body = {
            "type": "now",
            "shortLink": False,
            "posts": [{
                "integration": {"id": integration_id},
                "value": [{"content": content, "image": media_ids}],
                "settings": settings,
            }],
        }
        return self._post("/posts", body)
