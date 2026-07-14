"""All reads/writes against the Post Queue Notion DB. The DB is the plug's
only state store; this module is the only place its schema is spelled out
scheduler-side (the copied adapter has its own self-contained copy by design)."""


def _rt(prop) -> str:
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def row_fields(page: dict) -> dict:
    p = page["properties"]
    return {
        "id": page["id"],
        "title": "".join(t.get("plain_text", "") for t in p["Title"]["title"]),
        "project": (p["Project"]["select"] or {}).get("name", ""),
        "asset_urls": [u for u in _rt(p["Asset URL(s)"]).splitlines() if u.strip()],
        "asset_type": (p["Asset Type"]["select"] or {}).get("name", ""),
        "caption": _rt(p["Caption"]),
        "platforms": [m["name"] for m in p["Platforms"]["multi_select"]],
        "status": (p["Status"]["select"] or {}).get("name", ""),
        "posted_links": _rt(p["Posted Links"]),
        "error": _rt(p["Error"]),
    }


def parse_posted_links(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if ": " in line:
            platform, url = line.split(": ", 1)
            out[platform.strip()] = url.strip()
    return out


def find_due_row(client, db_id: str, project: str, platform: str):
    """Oldest Ready row for project targeting platform, not yet posted there."""
    resp = client.databases.query(
        database_id=db_id,
        filter={"and": [
            {"property": "Project", "select": {"equals": project}},
            {"property": "Status", "select": {"equals": "Ready"}},
            {"property": "Platforms", "multi_select": {"contains": platform}},
        ]},
        sorts=[{"timestamp": "created_time", "direction": "ascending"}],
    )
    for page in resp["results"]:
        fields = row_fields(page)
        if platform not in parse_posted_links(fields["posted_links"]):
            return page
    return None


def _set(client, page_id: str, properties: dict):
    client.pages.update(page_id=page_id, properties=properties)


def mark_posting(client, page: dict):
    _set(client, page["id"], {"Status": {"select": {"name": "Posting"}}})


def record_result(client, page: dict, platform: str, url: str = None, error: str = None):
    """Stamp one platform's outcome and derive the row status:
    failure -> Failed; all platforms posted -> Posted; else back to Ready."""
    if url is None and error is None:
        raise ValueError("record_result needs url or error")
    # Re-fetch: the caller's snapshot may be stale (another slot's tick may have
    # stamped a link since); a stale snapshot would drop links and re-open
    # already-posted platforms.
    page = client.pages.retrieve(page_id=page["id"])
    fields = row_fields(page)
    if error is not None:
        _set(client, page["id"], {
            "Status": {"select": {"name": "Failed"}},
            # Notion caps a rich_text segment at 2000 chars.
            "Error": {"rich_text": [{"text": {"content": f"{platform}: {error}"[:2000]}}]},
        })
        return
    links = parse_posted_links(fields["posted_links"])
    links[platform] = url
    text = "\n".join(f"{k}: {v}" for k, v in links.items())
    done = set(links) >= set(fields["platforms"])
    _set(client, page["id"], {
        "Status": {"select": {"name": "Posted" if done else "Ready"}},
        "Posted Links": {"rich_text": [{"text": {"content": text}}]},
        "Error": {"rich_text": []},
    })


def find_stuck_posting(client, db_id: str) -> list:
    """Rows sitting in Posting — the tick crashed mid-flight. Caller decides age."""
    resp = client.databases.query(
        database_id=db_id,
        filter={"property": "Status", "select": {"equals": "Posting"}},
    )
    return resp["results"]
