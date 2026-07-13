"""cross-platform-poster adapter — COPY this file into your project.
Do NOT import it across repos (engines-never-shared). After copying, add your
project to the 'Used By' list in the cross-platform-poster README.

The whole contract: call enqueue() when an asset is finished. gate='auto'
rows post at the next slot; gate='gated' rows wait for Ted to flip
Awaiting Approval -> Ready in the Post Queue.

Requires: notion-client. Env: NOTION_TOKEN, POST_QUEUE_DB_ID.
Used By: (stamped in the cross-platform-poster README)
"""


def enqueue(client, db_id: str, *, project: str, title: str, asset_urls: list,
            caption: str, platforms: list, gate: str = "gated"):
    """Create a Post Queue row. Returns the new page, or None if deduped."""
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
    return client.pages.create(
        parent={"database_id": db_id},
        properties={
            "Title": {"title": [{"text": {"content": title}}]},
            "Project": {"select": {"name": project}},
            "Asset URL(s)": {"rich_text": [{"text": {"content": "\n".join(asset_urls)}}]},
            "Asset Type": {"select": {"name": asset_type}},
            "Caption": {"rich_text": [{"text": {"content": caption[:2000]}}]},
            "Platforms": {"multi_select": [{"name": p} for p in platforms]},
            "Status": {"select": {"name": status}},
        },
    )
