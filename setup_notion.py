"""One-time: create the Post Queue database. Usage:
    python setup_notion.py <parent-page-url-or-id>
Prints the new DB id — put it in .env (Zo) and the POST_QUEUE_DB_ID GitHub
secret. Requires NOTION_TOKEN in env, and the parent page shared with the
integration."""
import os
import re
import sys

from dotenv import load_dotenv
from notion_client import Client

STATUS = ["Awaiting Approval", "Ready", "Posting", "Posted", "Failed"]
PLATFORMS = ["youtube-shorts", "ig-reels", "ig-carousel", "linkedin"]
PROJECTS = ["Useful Math", "Super Psychology", "Athena"]


def page_id_from_url(url_or_id: str) -> str:
    m = re.search(r"([0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12})",
                  url_or_id, re.IGNORECASE)
    if not m:
        sys.exit(f"Could not extract a page id from: {url_or_id}")
    return m.group(1)


def main():
    load_dotenv()
    parent = page_id_from_url(sys.argv[1])
    client = Client(auth=os.environ["NOTION_TOKEN"])
    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent},
        title=[{"text": {"content": "Post Queue"}}],
        properties={
            "Title": {"title": {}},
            "Project": {"select": {"options": [{"name": p} for p in PROJECTS]}},
            "Asset URL(s)": {"rich_text": {}},
            "Asset Type": {"select": {"options": [{"name": "video"}, {"name": "image-set"}]}},
            "Caption": {"rich_text": {}},
            "Platforms": {"multi_select": {"options": [{"name": p} for p in PLATFORMS]}},
            "Status": {"select": {"options": [{"name": s} for s in STATUS]}},
            "Publish Date & Time": {"date": {}},
            "Posted Links": {"rich_text": {}},
            "Error": {"rich_text": {}},
        },
    )
    print(f"Post Queue created: {db['id']}")
    print(f"URL: {db.get('url', '(open in Notion)')}")
    print("Set POST_QUEUE_DB_ID to this id in: .env on Zo AND the GitHub repo secret.")
    print("Manual Notion step for Ted: add a filtered view "
          "'🙋 Awaiting Approval' (Status = Awaiting Approval).")


if __name__ == "__main__":
    main()
