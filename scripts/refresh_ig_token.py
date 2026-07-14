"""Refresh the IG long-lived token (60-day expiry) and print the new one.
Run monthly by refresh-ig-token.yml, which stores it back into the repo
secret via ADMIN_PAT. Exits non-zero on any failure (watchdog notices the
failed workflow run). Simplified from useful-math's refresh_instagram_token.py."""
import os
import sys

import requests

r = requests.get("https://graph.facebook.com/v21.0/oauth/access_token",
                 params={"grant_type": "fb_exchange_token",
                         "client_id": os.environ["FB_APP_ID"],
                         "client_secret": os.environ["FB_APP_SECRET"],
                         "fb_exchange_token": os.environ["IG_ACCESS_TOKEN"]},
                 timeout=(10, 30))
if r.status_code != 200:
    tok = os.environ["IG_ACCESS_TOKEN"]
    sys.exit(f"refresh failed: HTTP {r.status_code}: "
             + r.text[:300].replace(tok, "***"))
print(r.json()["access_token"])
