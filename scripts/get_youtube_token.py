"""One-time, LOCAL: mint the YouTube refresh token. Usage:
    .venv/bin/python scripts/get_youtube_token.py <client_id> <client_secret>
Opens a browser for consent on the @Useful_Math Google account, prints the
refresh token to paste into the YT_REFRESH_TOKEN GitHub secret. Requires
Desktop-app OAuth credentials (their redirect config allows localhost)."""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

client_id, client_secret = sys.argv[1], sys.argv[2]
flow = InstalledAppFlow.from_client_config(
    {"installed": {"client_id": client_id, "client_secret": client_secret,
                   "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                   "token_uri": "https://oauth2.googleapis.com/token"}},
    scopes=SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nYT_REFRESH_TOKEN =", creds.refresh_token)
