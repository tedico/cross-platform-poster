"""cross-platform-poster adapter — COPY this file into your project.
Do NOT import it across repos (engines-never-shared). After copying, add your
project to the 'Used By' list in the cross-platform-poster README.

The whole contract: call enqueue() when an asset is finished. gate='auto'
rows are immediately eligible; gate='gated' rows wait for Ted to flip
Awaiting Approval -> Ready in the Post Queue. Either way a row posts when
its Publish Date & Time arrives (undated rows park until manually forced).

Requires: notion-client. Env: NOTION_TOKEN, POST_QUEUE_DB_ID.
Used By: (stamped in the cross-platform-poster README)
"""


NOTION_TEXT_LIMIT = 2000  # per rich_text object, not per property


def _text_objects(text: str) -> list:
    """Split into <=2000-char objects; Notion rejects a longer single one.

    This used to be `caption[:2000]`, which silently truncated. Instagram
    allows 2200, and Athena's carousel captions run to ~2184 — so a straight
    slice cut the sources block and hashtags off the end of the longest ones,
    which is exactly the content that must never be trimmed.
    """
    return [
        {"text": {"content": text[i:i + NOTION_TEXT_LIMIT]}}
        for i in range(0, len(text), NOTION_TEXT_LIMIT)
    ] or [{"text": {"content": ""}}]


def enqueue(client, db_id: str, *, project: str, title: str, asset_urls: list,
            caption: str, platforms: list, gate: str = "gated",
            publish_at: str = None):
    """Create a Post Queue row. Returns the new page, or None if deduped.
    publish_at: optional ISO datetime; the poster publishes at the first run
    at/after it. Without it the row parks until manually forced."""
    if not asset_urls:
        raise ValueError("enqueue: asset_urls must be a non-empty list")
    if not platforms:
        raise ValueError("enqueue: platforms must be a non-empty list "
                         "(a row with no platforms would never post)")
    if gate not in ("auto", "gated"):
        raise ValueError(f"enqueue: gate must be 'auto' or 'gated', got '{gate}'")
    existing = client.databases.query(
        database_id=db_id,
        filter={"property": "Asset URL(s)",
                "rich_text": {"contains": asset_urls[0]}},
    )
    if existing["results"]:
        return None  # already enqueued — dedup by first asset URL
    asset_type = "video" if asset_urls[0].lower().endswith(
        (".mp4", ".mov", ".webm")) else "image-set"
    status = "Ready" if gate == "auto" else "Awaiting Approval"
    properties = {
        "Title": {"title": [{"text": {"content": title}}]},
        "Project": {"select": {"name": project}},
        "Asset URL(s)": {"rich_text": [{"text": {"content": "\n".join(asset_urls)}}]},
        "Asset Type": {"select": {"name": asset_type}},
        "Caption": {"rich_text": _text_objects(caption)},
        "Platforms": {"multi_select": [{"name": p} for p in platforms]},
        "Status": {"select": {"name": status}},
    }
    if publish_at is not None:
        properties["Publish Date & Time"] = {"date": {"start": publish_at}}
    return client.pages.create(parent={"database_id": db_id}, properties=properties)
