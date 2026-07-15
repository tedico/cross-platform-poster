"""Refresh the IG long-lived token (Instagram-Login family, ~60-day expiry)
and print the new one. Run monthly by refresh-ig-token.yml, which stores it
back into the repo secret via ADMIN_PAT. Exits non-zero on failure (the
watchdog monitors this workflow's runs). Same flow as useful-math's
refresh_instagram_token.py — the token family's canonical refresh."""
import os
import sys

import requests

tok = os.environ["IG_ACCESS_TOKEN"]
r = requests.get("https://graph.instagram.com/refresh_access_token",
                 params={"grant_type": "ig_refresh_token", "access_token": tok},
                 timeout=(10, 30))
body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
if r.status_code != 200 or "access_token" not in body:
    sys.exit(f"refresh failed: HTTP {r.status_code}: "
             + r.text[:300].replace(tok, "***"))
print(body["access_token"])
