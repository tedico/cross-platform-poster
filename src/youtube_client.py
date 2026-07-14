"""Upload a video to YouTube via the Data API v3 (resumable). OAuth2
refresh-token flow — no browser, no token files; credentials come from the
caller (GH Actions secrets). The OAuth app must be in PRODUCTION status or
Google expires the refresh token after 7 days. Vertical <3 min video is
auto-classified as a Short."""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CATEGORY_EDUCATION = "27"


def _service(client_id: str, client_secret: str, refresh_token: str):
    creds = Credentials(
        None, refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def post(file_path, title: str, caption: str, *, client_id: str,
         client_secret: str, refresh_token: str) -> str:
    """Upload file_path, return the Shorts permalink."""
    body = {
        "snippet": {"title": title[:100], "description": caption[:5000],
                    "categoryId": CATEGORY_EDUCATION},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(file_path), mimetype="video/mp4",
                            resumable=True, chunksize=8 * 1024 * 1024)
    request = _service(client_id, client_secret, refresh_token).videos().insert(
        part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return f"https://youtube.com/shorts/{response['id']}"
