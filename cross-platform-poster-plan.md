# cross-platform-poster v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the universal posting plug — a scheduler that drains a central Notion Post Queue into per-channel publish slots via self-hosted Postiz on Zo — ready for Useful Math to fan finished MP4s out to YouTube Shorts + IG Reels.

**Architecture:** Three components + one appliance: (1) a Notion **Post Queue DB** holding all state, (2) a **scheduler** (`src/tick.py`) run every 15 min by a Zo automation that publishes at most one due row per project+platform via the Postiz public API, (3) a **canonical adapter file** consumers copy (Alexandria pattern). Postiz runs as Docker on Zo and owns all platform OAuth/upload complexity. Spec: `docs/superpowers/specs/2026-07-07-cross-platform-poster-design.md` (currently `~/cross-platform-poster-spec.md`).

**Tech Stack:** Python 3.11+, `notion-client==2.3.0`, `pyyaml`, `requests`, `python-dotenv`, `pytest` + `pytest-mock` (mirrors tedico/useful-math conventions). Postiz via Docker Compose on Zo.

**Scope notes:**
- The **Useful Math watcher adapter is NOT in this plan** — it's a separate small plan in the useful-math repo (copies `adapter/post_queue_adapter.py`, adds the folder watcher). Keeps PRs per-repo (avoid-PR-cascade rule) and it can't run until Sprint 3B defines the final-video folder anyway.
- **Git discipline:** Task 1 pushes ONE bootstrap scaffold commit directly to main (an empty repo needs a base) — **flagged for Ted's approval at execution start**. Everything after lives on branch `v1-build` and lands as a single PR Ted merges (no-merge-to-main rule, code+docs bundled).
- **SMS mechanism:** no SMS code in the repo. The Zo automation wrapping each script sends the SMS when the script exits non-zero with a summary on stdout — same pattern as the useful-math watchdog. Scripts therefore must: never crash silently, print a one-line summary, exit 1 on any failure.

**File structure (final):**

```
cross-platform-poster/
├── README.md                    # 8-section protocol + "The socket contract" human guide
├── SPRINT.md                    # from build-briefing template; Human items live here
├── channels.yaml                # slots only (gate lives in adapters)
├── requirements.txt
├── .env.example                 # NOTION_TOKEN, POST_QUEUE_DB_ID, POSTIZ_URL, POSTIZ_API_KEY, ASSET_STORE_TOKEN
├── .gitignore
├── docs/superpowers/specs/2026-07-07-cross-platform-poster-design.md
├── docs/superpowers/plans/2026-07-07-v1-implementation.md   # this file
├── adapter/post_queue_adapter.py  # THE canonical copy-me file (self-contained)
├── deploy/postiz/docker-compose.yml
├── setup_notion.py              # creates the Post Queue DB
├── src/__init__.py
├── src/config_loader.py         # channels.yaml + env loading
├── src/slots.py                 # "which slots are due this tick" math
├── src/queue_client.py          # Post Queue reads/writes (notion-client)
├── src/postiz_client.py         # Postiz public API (upload, post, integrations)
├── src/assets.py                # download Asset URL(s) to temp files
├── src/tick.py                  # orchestrator + CLI (--dry-run)
├── src/watchdog.py              # daily health check + monthly heartbeat
└── tests/
    ├── test_config_loader.py
    ├── test_slots.py
    ├── test_queue_client.py
    ├── test_postiz_client.py
    ├── test_assets.py
    ├── test_tick.py
    └── test_watchdog.py
```

---

### Task 1: Repo bootstrap (scaffold only — get Ted's OK to push to main)

**Files:**
- Create: `README.md` (skeleton), `SPRINT.md`, `.gitignore`, `requirements.txt`, `.env.example`, `docs/superpowers/specs/2026-07-07-cross-platform-poster-design.md`, `docs/superpowers/plans/2026-07-07-v1-implementation.md`

- [ ] **Step 1: Confirm with Ted** that the bootstrap commit may go directly to main (everything else goes via PR). STOP if not confirmed.

- [ ] **Step 2: Create the repo and scaffold**

```bash
gh repo create tedico/cross-platform-poster --public --description "Universal social posting plug: any project drops an asset in the Post Queue; scheduled slots publish it via Postiz. Consumers copy a one-file adapter."
git clone https://github.com/tedico/cross-platform-poster.git ~/cross-platform-poster
cd ~/cross-platform-poster
mkdir -p docs/superpowers/specs docs/superpowers/plans src tests adapter deploy/postiz
cp ~/cross-platform-poster-spec.md docs/superpowers/specs/2026-07-07-cross-platform-poster-design.md
cp ~/cross-platform-poster-plan.md docs/superpowers/plans/2026-07-07-v1-implementation.md
```

- [ ] **Step 3: Write `SPRINT.md`** (build-briefing template shape):

```markdown
# Sprint Plan — cross-platform-poster

## Phases
- [ ] Phase 1 — Core engine: config, slots, queue client, Postiz client, tick orchestrator, adapter file, all TDD
- [ ] Phase 2 — Live wiring: Postiz on Zo, Post Queue DB created, Zo automations (tick + watchdog), dry-run E2E
- [ ] Phase 3 — First supervised posts: YouTube Short + IG Reel land on the real channels, then unattended
- [ ] Phase 4 — Second consumer plugs in (Super Psychology or Athena) — proves the outlet

## Current phase
Phase 1 — Core engine

## Next
Execute v1 plan Task 2 (config loader).

## Human
- Create Google Cloud project + YouTube Data API OAuth credentials for @Useful_Math (SLOWEST item — start now; app review can take days)
- Check what survives from the old IG token work (useful-math get_instagram_token.py, May 2026): existing Meta app? @useful_math_ Business/Creator + linked FB Page? Report findings
- Register the Postiz admin account once Postiz is up on Zo, then connect YouTube + Instagram (OAuth dances) [blocked until Phase 2]
- Create a Notion integration "cross-platform-poster", share the parent page for the Post Queue DB with it, put token in Zo env [needed at Phase 2 start]
- Recurring (starts after Phase 3): re-auth Instagram in Postiz ~every 60 days when SMSed

## Blockers
none
```

- [ ] **Step 4: Write `.gitignore`, `requirements.txt`, `.env.example`**

`.gitignore`:
```
.env
__pycache__/
*.pyc
.pytest_cache/
deploy/postiz/.env
```

`requirements.txt`:
```
notion-client==2.3.0
python-dotenv>=1.0.0
pyyaml>=6.0
requests>=2.31.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

`.env.example`:
```
NOTION_TOKEN=            # cross-platform-poster Notion integration token
POST_QUEUE_DB_ID=        # printed by setup_notion.py
POSTIZ_URL=              # e.g. https://postiz-ted0.zocomputer.io
POSTIZ_API_KEY=          # Postiz Settings -> Public API
ASSET_STORE_TOKEN=       # optional X-Token for downloading from um-assets
```

- [ ] **Step 5: Write skeleton `README.md`** — title + one-line what/why + "🚧 v1 under construction, see docs/superpowers/specs/". (Full 8-section README is Task 12 — README protocol says it ships in the same PR as the behavior.)

- [ ] **Step 6: Commit and push (the approved bootstrap commit), then branch**

```bash
git add -A
git commit -m "chore: bootstrap repo — spec, plan, SPRINT, scaffold (no code yet)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push origin main
git checkout -b v1-build
```

---

### Task 2: Config loader (`channels.yaml` + env)

**Files:**
- Create: `channels.yaml`, `src/__init__.py`, `src/config_loader.py`
- Test: `tests/test_config_loader.py`

- [ ] **Step 1: Write `channels.yaml`**

```yaml
# Slots ONLY. Approval gate (auto/gated) is owned by each project's copied adapter.
# Slot times quantize to :00/:15/:30/:45 (scheduler ticks every 15 minutes).
useful-math:
  platforms:
    youtube-shorts: { slot: "12:00", tz: "America/New_York", cadence: daily }
    ig-reels:       { slot: "12:00", tz: "America/New_York", cadence: daily }
```

- [ ] **Step 2: Write the failing tests**

`tests/test_config_loader.py`:
```python
import pytest
from src.config_loader import load_channels, ConfigError


def _write(tmp_path, text):
    p = tmp_path / "channels.yaml"
    p.write_text(text)
    return p


def test_loads_valid_config(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:00\", tz: \"America/New_York\", cadence: daily }\n"
    ))
    cfg = load_channels(p)
    assert cfg["useful-math"]["platforms"]["youtube-shorts"]["slot"] == "12:00"


def test_rejects_unquantized_slot(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:10\", tz: \"America/New_York\", cadence: daily }\n"
    ))
    with pytest.raises(ConfigError, match="12:10"):
        load_channels(p)


def test_rejects_bad_timezone(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:00\", tz: \"America/Nowhere\", cadence: daily }\n"
    ))
    with pytest.raises(ConfigError, match="Nowhere"):
        load_channels(p)


def test_rejects_unknown_cadence(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:00\", tz: \"America/New_York\", cadence: hourly }\n"
    ))
    with pytest.raises(ConfigError, match="cadence"):
        load_channels(p)
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `python -m pytest tests/test_config_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config_loader'`

- [ ] **Step 4: Implement `src/config_loader.py`**

```python
"""Load and validate channels.yaml — slot schedule per project+platform.
Gate (auto/gated) deliberately does NOT live here; adapters own it."""
from zoneinfo import ZoneInfo

import yaml

VALID_MINUTES = {0, 15, 30, 45}
VALID_CADENCES = {"daily"}


class ConfigError(Exception):
    pass


def load_channels(path) -> dict:
    with open(path) as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ConfigError("channels.yaml must be a mapping of project -> config")
    for project, pcfg in cfg.items():
        platforms = (pcfg or {}).get("platforms")
        if not platforms:
            raise ConfigError(f"{project}: missing 'platforms'")
        for platform, s in platforms.items():
            slot = s.get("slot", "")
            try:
                hh, mm = slot.split(":")
                hh, mm = int(hh), int(mm)
            except ValueError:
                raise ConfigError(f"{project}/{platform}: bad slot '{slot}' (want HH:MM)")
            if not (0 <= hh <= 23) or mm not in VALID_MINUTES:
                raise ConfigError(
                    f"{project}/{platform}: slot '{slot}' must be HH:00/:15/:30/:45")
            tz = s.get("tz", "")
            try:
                ZoneInfo(tz)
            except Exception:
                raise ConfigError(f"{project}/{platform}: unknown timezone '{tz}'")
            if s.get("cadence") not in VALID_CADENCES:
                raise ConfigError(
                    f"{project}/{platform}: cadence must be one of {sorted(VALID_CADENCES)}")
    return cfg
```

Also create empty `src/__init__.py` and `tests/__init__.py`.

- [ ] **Step 5: Run tests, verify they pass**

Run: `python -m pytest tests/test_config_loader.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add channels.yaml src/__init__.py src/config_loader.py tests/__init__.py tests/test_config_loader.py
git commit -m "feat: channels.yaml + validated config loader — slots quantized to 15-min grid, tz-checked

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Slot math (`src/slots.py`)

**Files:**
- Create: `src/slots.py`
- Test: `tests/test_slots.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_slots.py`:
```python
from datetime import datetime, timezone

from src.slots import due_slots

CFG = {
    "useful-math": {
        "platforms": {
            "youtube-shorts": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
            "ig-reels": {"slot": "18:30", "tz": "America/New_York", "cadence": "daily"},
        }
    }
}


def test_slot_due_at_exact_local_time():
    # 12:00 America/New_York in July == 16:00 UTC (EDT)
    now = datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "youtube-shorts")]


def test_slot_not_due_other_time():
    now = datetime(2026, 7, 8, 16, 15, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == []


def test_tick_time_quantized_down():
    # 16:07 UTC quantizes to the 16:00 tick -> 12:00 ET slot is due
    now = datetime(2026, 7, 8, 16, 7, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "youtube-shorts")]


def test_evening_slot_in_local_tz():
    # 18:30 ET == 22:30 UTC in July
    now = datetime(2026, 7, 8, 22, 30, tzinfo=timezone.utc)
    assert due_slots(CFG, now) == [("useful-math", "ig-reels")]
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/test_slots.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.slots'`

- [ ] **Step 3: Implement `src/slots.py`**

```python
"""Which project+platform slots are due at this tick?

The scheduler ticks every ~15 minutes. We quantize the tick time DOWN to the
15-minute grid and compare against each slot's HH:MM in ITS OWN timezone, so a
slot fires exactly once per day regardless of cron jitter."""
from datetime import datetime
from zoneinfo import ZoneInfo


def due_slots(cfg: dict, now: datetime) -> list[tuple[str, str]]:
    due = []
    for project, pcfg in cfg.items():
        for platform, s in pcfg["platforms"].items():
            local = now.astimezone(ZoneInfo(s["tz"]))
            quantized = local.replace(minute=(local.minute // 15) * 15,
                                      second=0, microsecond=0)
            if quantized.strftime("%H:%M") == s["slot"]:
                due.append((project, platform))
    return due
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest tests/test_slots.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/slots.py tests/test_slots.py
git commit -m "feat: slot due-math — tz-aware, quantized to 15-min grid, fires once per day per slot

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Post Queue client (`src/queue_client.py`)

**Files:**
- Create: `src/queue_client.py`
- Test: `tests/test_queue_client.py`

Post Queue schema this client speaks (created for real in Task 10 by `setup_notion.py`):
Title (title), Project (select), Asset URL(s) (rich_text, newline-separated), Asset Type (select: video|image-set), Caption (rich_text), Platforms (multi_select), Status (select: Awaiting Approval|Ready|Posting|Posted|Failed), Posted Links (rich_text, lines of `platform: url`), Error (rich_text), Date Added (created_time).

- [ ] **Step 1: Write the failing tests**

`tests/test_queue_client.py`:
```python
from unittest.mock import MagicMock

from src.queue_client import (
    find_due_row, mark_posting, record_result, parse_posted_links, row_fields,
)


def _page(page_id="p1", status="Ready", platforms=("youtube-shorts", "ig-reels"),
          posted_links="", assets="https://a/x.mp4", title="Hua Luogeng",
          caption="cap", asset_type="video"):
    return {
        "id": page_id,
        "properties": {
            "Title": {"title": [{"plain_text": title}]},
            "Project": {"select": {"name": "Useful Math"}},
            "Asset URL(s)": {"rich_text": [{"plain_text": assets}]},
            "Asset Type": {"select": {"name": asset_type}},
            "Caption": {"rich_text": [{"plain_text": caption}]},
            "Platforms": {"multi_select": [{"name": p} for p in platforms]},
            "Status": {"select": {"name": status}},
            "Posted Links": {"rich_text": [{"plain_text": posted_links}] if posted_links else []},
            "Error": {"rich_text": []},
        },
    }


def test_find_due_row_picks_oldest_ready(mocker):
    client = MagicMock()
    client.databases.query.return_value = {"results": [_page("old"), _page("new")]}
    row = find_due_row(client, "db1", "Useful Math", "youtube-shorts")
    assert row["id"] == "old"
    kwargs = client.databases.query.call_args.kwargs
    assert kwargs["sorts"] == [{"timestamp": "created_time", "direction": "ascending"}]


def test_find_due_row_skips_already_posted_platform():
    client = MagicMock()
    client.databases.query.return_value = {
        "results": [_page("done", posted_links="youtube-shorts: https://yt/1"), _page("fresh")]
    }
    row = find_due_row(client, "db1", "Useful Math", "youtube-shorts")
    assert row["id"] == "fresh"


def test_find_due_row_none_when_empty():
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    assert find_due_row(client, "db1", "Useful Math", "youtube-shorts") is None


def test_parse_posted_links():
    assert parse_posted_links("youtube-shorts: https://yt/1\nig-reels: https://ig/2") == {
        "youtube-shorts": "https://yt/1", "ig-reels": "https://ig/2"}
    assert parse_posted_links("") == {}


def test_record_result_success_all_done_marks_posted():
    client = MagicMock()
    row = _page(platforms=("youtube-shorts",))
    record_result(client, row, "youtube-shorts", url="https://yt/1")
    props = client.pages.update.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Posted"
    assert "youtube-shorts: https://yt/1" in props["Posted Links"]["rich_text"][0]["text"]["content"]


def test_record_result_success_remaining_goes_back_to_ready():
    client = MagicMock()
    row = _page(platforms=("youtube-shorts", "ig-reels"))
    record_result(client, row, "youtube-shorts", url="https://yt/1")
    props = client.pages.update.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Ready"


def test_record_result_failure_marks_failed_with_error():
    client = MagicMock()
    row = _page()
    record_result(client, row, "ig-reels", error="token expired")
    props = client.pages.update.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Failed"
    assert "ig-reels" in props["Error"]["rich_text"][0]["text"]["content"]


def test_row_fields_extracts_plain_values():
    f = row_fields(_page())
    assert f["title"] == "Hua Luogeng"
    assert f["asset_urls"] == ["https://a/x.mp4"]
    assert f["platforms"] == ["youtube-shorts", "ig-reels"]
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/test_queue_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.queue_client'`

- [ ] **Step 3: Implement `src/queue_client.py`**

```python
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
    fields = row_fields(page)
    if error is not None:
        _set(client, page["id"], {
            "Status": {"select": {"name": "Failed"}},
            "Error": {"rich_text": [{"text": {"content": f"{platform}: {error}"}}]},
        })
        return
    links = parse_posted_links(fields["posted_links"])
    links[platform] = url
    text = "\n".join(f"{k}: {v}" for k, v in links.items())
    done = set(links) >= set(fields["platforms"])
    _set(client, page["id"], {
        "Status": {"select": {"name": "Posted" if done else "Ready"}},
        "Posted Links": {"rich_text": [{"text": {"content": text}}]},
    })


def find_stuck_posting(client, db_id: str) -> list:
    """Rows sitting in Posting — the tick crashed mid-flight. Caller decides age."""
    resp = client.databases.query(
        database_id=db_id,
        filter={"property": "Status", "select": {"equals": "Posting"}},
    )
    return resp["results"]
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest tests/test_queue_client.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/queue_client.py tests/test_queue_client.py
git commit -m "feat: Post Queue client — oldest-first pick, per-platform result stamping, Ready/Posted/Failed transitions

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Postiz API client (`src/postiz_client.py`)

**Files:**
- Create: `src/postiz_client.py`
- Test: `tests/test_postiz_client.py`

⚠️ **Verify-against-docs step built in:** the Postiz public API lives under `{POSTIZ_URL}/api/public/v1` with the API key in the `Authorization` header; endpoints used: `GET /integrations`, `POST /upload` (multipart), `POST /posts`. The exact `POST /posts` payload (esp. per-platform `settings` for YouTube title/short-type and IG reel-type) MUST be confirmed against https://docs.postiz.com/public-api when the instance is live (Task 9 Step 4) — treat the payload builders below as the single place to adjust.

- [ ] **Step 1: Write the failing tests**

`tests/test_postiz_client.py`:
```python
import pytest

from src.postiz_client import PostizClient, PostizError, build_settings


def test_build_settings_youtube_shorts():
    s = build_settings("youtube-shorts", title="Hua Luogeng")
    assert s["title"] == "Hua Luogeng"


def test_build_settings_unknown_platform_raises():
    with pytest.raises(PostizError, match="unknown platform"):
        build_settings("myspace", title="x")


def test_integrations_maps_platform_to_id(mocker):
    client = PostizClient("https://pz.example", "key")
    mocker.patch.object(client, "_get", return_value=[
        {"id": "int-yt", "identifier": "youtube", "name": "Useful Math"},
        {"id": "int-ig", "identifier": "instagram", "name": "useful_math_"},
    ])
    m = client.integration_ids()
    assert m["youtube"] == "int-yt"
    assert m["instagram"] == "int-ig"


def test_create_post_hits_posts_endpoint(mocker):
    client = PostizClient("https://pz.example", "key")
    post = mocker.patch.object(client, "_post", return_value={"id": "post-1"})
    out = client.create_post(integration_id="int-yt", content="cap",
                             media_ids=[{"id": "m1"}], settings={"title": "t"})
    assert out == {"id": "post-1"}
    assert post.call_args.args[0] == "/posts"
    body = post.call_args.args[1]
    assert body["type"] == "now"
    assert body["posts"][0]["integration"]["id"] == "int-yt"


def test_upload_returns_media_descriptor(mocker):
    client = PostizClient("https://pz.example", "key")
    resp = mocker.MagicMock(status_code=200)
    resp.json.return_value = {"id": "m1", "path": "/uploads/x.mp4"}
    mocker.patch("src.postiz_client.requests.post", return_value=resp)
    out = client.upload("tests/test_postiz_client.py")  # any real file path works
    assert out["id"] == "m1"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/test_postiz_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.postiz_client'`

- [ ] **Step 3: Implement `src/postiz_client.py`**

```python
"""Thin client for the Postiz public API (v1). Postiz owns platform OAuth and
upload mechanics; we own nothing platform-specific except the per-platform
`settings` payloads in build_settings() — the ONE place to adjust after
confirming against docs.postiz.com/public-api (see plan Task 9 Step 4)."""
from pathlib import Path

import requests

TIMEOUT = 300  # video uploads are slow


class PostizError(Exception):
    pass


# Post Queue platform name -> (Postiz integration identifier, settings builder)
def build_settings(platform: str, title: str = "") -> dict:
    if platform == "youtube-shorts":
        # YouTube auto-classifies vertical <3min video as a Short; title required.
        return {"title": title[:100]}
    if platform == "ig-reels":
        return {"post_type": "post"}  # confirm reel setting name against live docs
    raise PostizError(f"unknown platform '{platform}'")


PLATFORM_IDENTIFIER = {"youtube-shorts": "youtube", "ig-reels": "instagram"}


class PostizClient:
    def __init__(self, base_url: str, api_key: str):
        self.base = base_url.rstrip("/") + "/api/public/v1"
        self.headers = {"Authorization": api_key}

    def _get(self, path: str):
        r = requests.get(self.base + path, headers=self.headers, timeout=TIMEOUT)
        if r.status_code != 200:
            raise PostizError(f"GET {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def _post(self, path: str, body: dict):
        r = requests.post(self.base + path, headers=self.headers, json=body,
                          timeout=TIMEOUT)
        if r.status_code not in (200, 201):
            raise PostizError(f"POST {path} -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def integration_ids(self) -> dict:
        """Map Postiz platform identifier ('youtube', 'instagram') -> integration id."""
        return {i["identifier"]: i["id"] for i in self._get("/integrations")}

    def upload(self, file_path) -> dict:
        p = Path(file_path)
        with p.open("rb") as fh:
            r = requests.post(self.base + "/upload", headers=self.headers,
                              files={"file": (p.name, fh)}, timeout=TIMEOUT)
        if r.status_code not in (200, 201):
            raise PostizError(f"upload -> HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

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
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest tests/test_postiz_client.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/postiz_client.py tests/test_postiz_client.py
git commit -m "feat: Postiz public-API client — integrations, upload, create-post; per-platform settings isolated in build_settings

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Asset downloader (`src/assets.py`)

**Files:**
- Create: `src/assets.py`
- Test: `tests/test_assets.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_assets.py`:
```python
import pytest

from src.assets import download_assets, AssetError


def test_downloads_to_tmp_with_filename(mocker, tmp_path):
    resp = mocker.MagicMock(status_code=200)
    resp.iter_content.return_value = [b"vid"]
    mocker.patch("src.assets.requests.get", return_value=resp)
    paths = download_assets(["https://a.example/store/hua-luogeng.mp4"],
                            tmp_path, token="t")
    assert paths[0].name == "hua-luogeng.mp4"
    assert paths[0].read_bytes() == b"vid"


def test_sends_token_header(mocker, tmp_path):
    resp = mocker.MagicMock(status_code=200)
    resp.iter_content.return_value = [b"x"]
    get = mocker.patch("src.assets.requests.get", return_value=resp)
    download_assets(["https://a/x.mp4"], tmp_path, token="sekret")
    assert get.call_args.kwargs["headers"] == {"X-Token": "sekret"}


def test_http_error_raises(mocker, tmp_path):
    resp = mocker.MagicMock(status_code=404)
    mocker.patch("src.assets.requests.get", return_value=resp)
    with pytest.raises(AssetError, match="404"):
        download_assets(["https://a/x.mp4"], tmp_path, token=None)
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/test_assets.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/assets.py`**

```python
"""Download a queue row's Asset URL(s) to local temp files so Postiz can
ingest them. um-assets style stores take an optional X-Token header."""
from pathlib import Path
from urllib.parse import urlparse

import requests


class AssetError(Exception):
    pass


def download_assets(urls: list, dest_dir, token: str = None) -> list:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    headers = {"X-Token": token} if token else {}
    paths = []
    for url in urls:
        name = Path(urlparse(url).path).name or "asset.bin"
        r = requests.get(url, headers=headers, stream=True, timeout=300)
        if r.status_code != 200:
            raise AssetError(f"GET {url} -> HTTP {r.status_code}")
        out = dest_dir / name
        with out.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
        paths.append(out)
    return paths
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest tests/test_assets.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/assets.py tests/test_assets.py
git commit -m "feat: asset downloader — streams Asset URL(s) to temp, X-Token support for um-assets-style stores

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Tick orchestrator (`src/tick.py`) — the scheduler

**Files:**
- Create: `src/tick.py`
- Test: `tests/test_tick.py`

Behavior contract (from spec): per due slot, at most ONE row; `Posting` → publish → `record_result`; any failure marks the row and makes the tick exit non-zero with a printed summary (the Zo automation turns that into the SMS); a last-tick stamp file is always written for the watchdog; `--dry-run` does everything but upload/post.

- [ ] **Step 1: Write the failing tests**

`tests/test_tick.py`:
```python
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.tick import run_tick

CFG = {"useful-math": {"platforms": {
    "youtube-shorts": {"slot": "12:00", "tz": "America/New_York", "cadence": "daily"},
}}}
NOW = datetime(2026, 7, 8, 16, 0, tzinfo=timezone.utc)  # 12:00 EDT
ENV = {"project_names": {"useful-math": "Useful Math"}}


def _row(platforms=("youtube-shorts",)):
    return {
        "id": "p1",
        "properties": {
            "Title": {"title": [{"plain_text": "Hua Luogeng"}]},
            "Project": {"select": {"name": "Useful Math"}},
            "Asset URL(s)": {"rich_text": [{"plain_text": "https://a/hua.mp4"}]},
            "Asset Type": {"select": {"name": "video"}},
            "Caption": {"rich_text": [{"plain_text": "the caption"}]},
            "Platforms": {"multi_select": [{"name": p} for p in platforms]},
            "Status": {"select": {"name": "Ready"}},
            "Posted Links": {"rich_text": []},
            "Error": {"rich_text": []},
        },
    }


def _wire(mocker, row):
    mocker.patch("src.tick.find_due_row", return_value=row)
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    mocker.patch("src.tick.download_assets", return_value=["/tmp/hua.mp4"])
    mark = mocker.patch("src.tick.mark_posting")
    record = mocker.patch("src.tick.record_result")
    postiz = MagicMock()
    postiz.integration_ids.return_value = {"youtube": "int-yt", "instagram": "int-ig"}
    postiz.upload.return_value = {"id": "m1", "path": "/up/hua.mp4"}
    postiz.create_post.return_value = {"id": "post-1"}
    return mark, record, postiz


def test_happy_path_posts_and_records(mocker, tmp_path):
    mark, record, postiz = _wire(mocker, _row())
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=postiz, now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 0
    mark.assert_called_once()
    postiz.create_post.assert_called_once()
    assert record.call_args.kwargs.get("url") or record.call_args.args


def test_empty_queue_is_silent_success(mocker, tmp_path):
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=MagicMock(), now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 0


def test_postiz_failure_records_error_and_exits_nonzero(mocker, tmp_path):
    mark, record, postiz = _wire(mocker, _row())
    postiz.create_post.side_effect = Exception("boom")
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=postiz, now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 1
    assert record.call_args.kwargs["error"]


def test_dry_run_never_touches_postiz_or_status(mocker, tmp_path):
    mark, record, postiz = _wire(mocker, _row())
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=postiz, now=NOW,
                    stamp_dir=tmp_path, dry_run=True)
    assert code == 0
    postiz.upload.assert_not_called()
    postiz.create_post.assert_not_called()
    mark.assert_not_called()
    record.assert_not_called()


def test_writes_last_tick_stamp(mocker, tmp_path):
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[])
    run_tick(CFG, ENV, notion=MagicMock(), postiz=MagicMock(), now=NOW,
             stamp_dir=tmp_path, dry_run=False)
    assert (tmp_path / "last_tick").exists()


def test_stuck_posting_row_exits_nonzero(mocker, tmp_path):
    mocker.patch("src.tick.find_due_row", return_value=None)
    mocker.patch("src.tick.find_stuck_posting", return_value=[_row()])
    mocker.patch("src.tick.record_result")
    code = run_tick(CFG, ENV, notion=MagicMock(), postiz=MagicMock(), now=NOW,
                    stamp_dir=tmp_path, dry_run=False)
    assert code == 1
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/test_tick.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/tick.py`**

```python
"""The scheduler tick. Deliberately dumb: config says what's due, Notion holds
all state, Postiz does all platform work. Run by a Zo automation every 15 min;
a non-zero exit + printed summary is the SMS trigger. --dry-run logs what WOULD
post and touches nothing."""
import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from src.assets import download_assets
from src.config_loader import load_channels
from src.postiz_client import (
    PLATFORM_IDENTIFIER, PostizClient, build_settings,
)
from src.queue_client import (
    find_due_row, find_stuck_posting, mark_posting, record_result, row_fields,
)

STAMP_DIR = Path.home() / ".cross-platform-poster"


def _publish(notion, postiz, page, platform, dry_run) -> str:
    """Publish one row to one platform. Returns the summary line."""
    fields = row_fields(page)
    if dry_run:
        return (f"DRY-RUN would post '{fields['title']}' -> {platform} "
                f"({len(fields['asset_urls'])} asset(s))")
    mark_posting(notion, page)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            paths = download_assets(fields["asset_urls"], tmp,
                                    token=os.environ.get("ASSET_STORE_TOKEN"))
            media = [postiz.upload(p) for p in paths]
            integration = postiz.integration_ids()[PLATFORM_IDENTIFIER[platform]]
            result = postiz.create_post(
                integration_id=integration,
                content=fields["caption"],
                media_ids=[{"id": m["id"], "path": m.get("path", "")} for m in media],
                settings=build_settings(platform, title=fields["title"]),
            )
    except Exception as e:  # noqa: BLE001 — any failure must stamp the row, not crash the tick
        record_result(notion, page, platform, error=str(e)[:500])
        raise
    url = f"postiz:{result.get('id', 'unknown')}"  # permalink backfilled when Postiz exposes it
    record_result(notion, page, platform, url=url)
    return f"POSTED '{fields['title']}' -> {platform} ({url})"


def run_tick(cfg, env, notion, postiz, now, stamp_dir=STAMP_DIR, dry_run=False) -> int:
    from src.slots import due_slots
    stamp_dir = Path(stamp_dir)
    stamp_dir.mkdir(parents=True, exist_ok=True)
    failures, lines = [], []

    stuck = find_stuck_posting(notion, env.get("db_id", ""))
    for page in stuck:
        title = row_fields(page)["title"]
        if not dry_run:
            record_result(notion, page, "(stuck)",
                          error="stuck in Posting — tick crashed mid-flight; "
                                "check the platform for a dupe, then re-Ready")
        failures.append(f"STUCK row '{title}' was in Posting")

    for project, platform in due_slots(cfg, now):
        notion_project = env["project_names"].get(project, project)
        page = find_due_row(notion, env.get("db_id", ""), notion_project, platform)
        if page is None:
            continue  # empty queue: silent skip by design
        try:
            lines.append(_publish(notion, postiz, page, platform, dry_run))
        except Exception as e:  # noqa: BLE001
            failures.append(f"FAILED {project}->{platform}: {e}")

    (stamp_dir / "last_tick").write_text(now.isoformat())
    for line in lines:
        print(line)
    if failures:
        print("; ".join(failures))
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    cfg = load_channels(Path(__file__).resolve().parent.parent / "channels.yaml")
    env = {
        "db_id": os.environ["POST_QUEUE_DB_ID"],
        "project_names": {"useful-math": "Useful Math"},
    }
    notion = Client(auth=os.environ["NOTION_TOKEN"])
    postiz = PostizClient(os.environ["POSTIZ_URL"], os.environ["POSTIZ_API_KEY"])
    sys.exit(run_tick(cfg, env, notion, postiz,
                      now=datetime.now(timezone.utc), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest tests/test_tick.py -v`
Expected: 6 passed

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -v`
Expected: all tests pass (config 4, slots 4, queue 8, postiz 5, assets 3, tick 6 = 30)

- [ ] **Step 6: Commit**

```bash
git add src/tick.py tests/test_tick.py
git commit -m "feat: tick orchestrator — due slots -> publish one row/platform, stuck-Posting sweep, dry-run, stamp file, non-zero exit = SMS

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Canonical adapter (`adapter/post_queue_adapter.py`) + watchdog (`src/watchdog.py`)

**Files:**
- Create: `adapter/post_queue_adapter.py`, `src/watchdog.py`
- Test: `tests/test_adapter.py`, `tests/test_watchdog.py`

- [ ] **Step 1: Write the failing adapter tests**

`tests/test_adapter.py`:
```python
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

spec = importlib.util.spec_from_file_location(
    "post_queue_adapter", Path("adapter/post_queue_adapter.py"))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_enqueue_creates_row_with_ready_when_auto():
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    adapter.enqueue(client, "db1", project="Useful Math", title="Hua Luogeng",
                    asset_urls=["https://a/hua.mp4"], caption="cap",
                    platforms=["youtube-shorts", "ig-reels"], gate="auto")
    props = client.pages.create.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Ready"
    assert props["Asset Type"]["select"]["name"] == "video"


def test_enqueue_gated_creates_awaiting_approval():
    client = MagicMock()
    client.databases.query.return_value = {"results": []}
    adapter.enqueue(client, "db1", project="X", title="t",
                    asset_urls=["https://a/i1.png", "https://a/i2.png"],
                    caption="c", platforms=["ig-carousel"], gate="gated")
    props = client.pages.create.call_args.kwargs["properties"]
    assert props["Status"]["select"]["name"] == "Awaiting Approval"
    assert props["Asset Type"]["select"]["name"] == "image-set"


def test_enqueue_dedups_on_existing_asset_url():
    client = MagicMock()
    client.databases.query.return_value = {"results": [{"id": "existing"}]}
    out = adapter.enqueue(client, "db1", project="Useful Math", title="t",
                          asset_urls=["https://a/hua.mp4"], caption="c",
                          platforms=["youtube-shorts"], gate="auto")
    assert out is None
    client.pages.create.assert_not_called()
```

- [ ] **Step 2: Write the failing watchdog tests**

`tests/test_watchdog.py`:
```python
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.watchdog import check


def test_fresh_stamp_no_stuck_rows_passes(tmp_path):
    now = datetime.now(timezone.utc)
    (tmp_path / "last_tick").write_text(now.isoformat())
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 0


def test_stale_stamp_fails(tmp_path):
    now = datetime.now(timezone.utc)
    (tmp_path / "last_tick").write_text((now - timedelta(hours=3)).isoformat())
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 1
    assert "stale" in msg


def test_missing_stamp_fails(tmp_path):
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path,
                      now=datetime.now(timezone.utc))
    assert code == 1


def test_heartbeat_on_first_of_month(tmp_path):
    now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    (tmp_path / "last_tick").write_text(now.isoformat())
    notion = MagicMock()
    notion.databases.query.return_value = {"results": []}
    code, msg = check(notion, "db1", stamp_dir=tmp_path, now=now)
    assert code == 1  # non-zero so the Zo automation SMSes the heartbeat
    assert "heartbeat" in msg.lower()
```

- [ ] **Step 3: Run both, verify they fail**

Run: `python -m pytest tests/test_adapter.py tests/test_watchdog.py -v`
Expected: FAIL (module not found / file missing)

- [ ] **Step 4: Implement `adapter/post_queue_adapter.py`**

```python
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
```

- [ ] **Step 5: Implement `src/watchdog.py`**

```python
"""Daily health check, run by its own Zo automation (6:30 AM ET). Non-zero
exit + printed message = the automation SMSes Ted. Checks: (1) the tick's
stamp file is fresh, (2) no rows stuck in Posting, (3) on the 1st of the
month, force a heartbeat SMS proving this watchdog itself is alive."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from src.queue_client import find_stuck_posting
from src.tick import STAMP_DIR

MAX_STAMP_AGE_SECONDS = 45 * 60  # three missed ticks


def check(notion, db_id: str, stamp_dir=STAMP_DIR, now=None) -> tuple:
    now = now or datetime.now(timezone.utc)
    problems = []
    stamp = Path(stamp_dir) / "last_tick"
    if not stamp.exists():
        problems.append("poster tick has NEVER run (no stamp file)")
    else:
        age = (now - datetime.fromisoformat(stamp.read_text().strip())).total_seconds()
        if age > MAX_STAMP_AGE_SECONDS:
            problems.append(f"poster tick stamp is stale ({int(age // 60)} min old)")
    stuck = find_stuck_posting(notion, db_id)
    if stuck:
        problems.append(f"{len(stuck)} row(s) stuck in Posting")
    if problems:
        return 1, "cross-platform-poster WATCHDOG: " + "; ".join(problems)
    if now.day == 1:
        return 1, ("cross-platform-poster watchdog heartbeat: all healthy. "
                   "(Monthly proof-of-life — no action needed.)")
    return 0, "healthy"


def main():
    load_dotenv()
    notion = Client(auth=os.environ["NOTION_TOKEN"])
    code, msg = check(notion, os.environ["POST_QUEUE_DB_ID"])
    print(msg)
    sys.exit(code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run all tests, verify they pass**

Run: `python -m pytest -v`
Expected: 37 passed

- [ ] **Step 7: Commit**

```bash
git add adapter/post_queue_adapter.py src/watchdog.py tests/test_adapter.py tests/test_watchdog.py
git commit -m "feat: canonical copy-me adapter (enqueue + dedup + gate) and watchdog (stale-tick/stuck-row/monthly heartbeat)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Postiz on Zo (deploy config + live bring-up)

**Files:**
- Create: `deploy/postiz/docker-compose.yml`

- [ ] **Step 1: Write `deploy/postiz/docker-compose.yml`**

```yaml
# Postiz self-hosted on Zo. Secrets come from deploy/postiz/.env (gitignored):
#   POSTIZ_JWT_SECRET, POSTIZ_PG_PASSWORD, POSTIZ_PUBLIC_URL,
#   YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET
services:
  postiz:
    image: ghcr.io/gitroomhq/postiz-app:latest
    restart: always
    environment:
      MAIN_URL: ${POSTIZ_PUBLIC_URL}
      FRONTEND_URL: ${POSTIZ_PUBLIC_URL}
      NEXT_PUBLIC_BACKEND_URL: ${POSTIZ_PUBLIC_URL}/api
      JWT_SECRET: ${POSTIZ_JWT_SECRET}
      DATABASE_URL: postgresql://postiz:${POSTIZ_PG_PASSWORD}@postiz-postgres:5432/postiz
      REDIS_URL: redis://postiz-redis:6379
      BACKEND_INTERNAL_URL: http://localhost:3000
      IS_GENERAL: "true"
      DISABLE_REGISTRATION: "false"   # flip to "true" right after Ted registers
      STORAGE_PROVIDER: local
      UPLOAD_DIRECTORY: /uploads
      NEXT_PUBLIC_UPLOAD_DIRECTORY: /uploads
      YOUTUBE_CLIENT_ID: ${YOUTUBE_CLIENT_ID}
      YOUTUBE_CLIENT_SECRET: ${YOUTUBE_CLIENT_SECRET}
      FACEBOOK_APP_ID: ${FACEBOOK_APP_ID}
      FACEBOOK_APP_SECRET: ${FACEBOOK_APP_SECRET}
    volumes:
      - postiz-config:/config
      - postiz-uploads:/uploads
    ports:
      - "5000:5000"
    depends_on:
      postiz-postgres:
        condition: service_healthy
      postiz-redis:
        condition: service_healthy
  postiz-postgres:
    image: postgres:17-alpine
    restart: always
    environment:
      POSTGRES_PASSWORD: ${POSTIZ_PG_PASSWORD}
      POSTGRES_USER: postiz
      POSTGRES_DB: postiz
    volumes:
      - postiz-db:/var/lib/postgresql/data
    healthcheck:
      test: pg_isready -U postiz -d postiz
      interval: 10s
      timeout: 3s
      retries: 3
  postiz-redis:
    image: redis:7.2-alpine
    restart: always
    healthcheck:
      test: redis-cli ping
      interval: 10s
      timeout: 3s
      retries: 3
    volumes:
      - postiz-redis-data:/data
volumes:
  postiz-db:
  postiz-redis-data:
  postiz-config:
  postiz-uploads:
```

⚠️ Before first `docker compose up`, diff this file against the current compose in https://docs.postiz.com/installation/docker-compose — Postiz env vars drift between releases. Pin `image:` to the latest release tag found there instead of `latest`.

- [ ] **Step 2: Commit the compose file**

```bash
git add deploy/postiz/docker-compose.yml
git commit -m "feat: Postiz docker-compose for Zo — secrets via gitignored .env, registration flipped off post-signup

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: Bring Postiz up on Zo** (live actions via zo tools, not commits)

1. Clone the repo on Zo: `git clone https://github.com/tedico/cross-platform-poster.git ~/cross-platform-poster` (Zo bash).
2. Create `~/cross-platform-poster/deploy/postiz/.env` on Zo with generated `POSTIZ_JWT_SECRET` (e.g. `openssl rand -hex 32`), `POSTIZ_PG_PASSWORD`, and `POSTIZ_PUBLIC_URL` left blank for now; platform creds blank until Ted's Human items land.
3. Register the service with Zo (`register_user_service` / `proxy_local_service`) to get the public HTTPS URL (e.g. `https://postiz-ted0.zocomputer.io`), write it into `.env` as `POSTIZ_PUBLIC_URL`.
4. `docker compose up -d` in `~/cross-platform-poster/deploy/postiz` (Zo bash). Verify: `curl -sf $POSTIZ_PUBLIC_URL` returns the Postiz login page.
5. **Ted (Human):** register the admin account at the URL. Then set `DISABLE_REGISTRATION: "true"` and `docker compose up -d` again.
6. **Ted (Human):** Settings → Public API → generate the API key → into Zo env as `POSTIZ_API_KEY`.

- [ ] **Step 4: Confirm the public-API payload shapes** — open https://docs.postiz.com/public-api against the running version: verify `/upload` response fields, `/posts` body shape, YouTube settings (title/short) and Instagram settings (reel type). Fix `src/postiz_client.py::build_settings` + `create_post` if they differ, update the tests to match, run `python -m pytest`, and commit any corrections as `fix: align postiz client with live public-api schema`.

---

### Task 10: `setup_notion.py` — create the Post Queue DB

**Files:**
- Create: `setup_notion.py`

- [ ] **Step 1: Implement `setup_notion.py`**

```python
"""One-time: create the Post Queue database. Usage:
    python setup_notion.py <parent-page-url-or-id>
Prints the new DB id — put it in .env as POST_QUEUE_DB_ID (local + Zo).
Requires NOTION_TOKEN in env, and the parent page shared with the integration."""
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
            "Posted Links": {"rich_text": {}},
            "Error": {"rich_text": {}},
        },
    )
    print(f"Post Queue created: {db['id']}")
    print(f"URL: {db.get('url', '(open in Notion)')}")
    print("Put this in .env (local AND Zo): POST_QUEUE_DB_ID=" + db["id"])
    print("Manual Notion step for Ted: add a filtered view "
          "'🙋 Awaiting Approval' (Status = Awaiting Approval).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add setup_notion.py
git commit -m "feat: setup_notion.py creates the Post Queue DB (the plug's socket schema) and prints the env wiring

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: Run it for real** (after Ted's Human item #4 — integration created + parent page shared):

Run: `python setup_notion.py <parent-page-url>`
Expected: prints DB id. Set `POST_QUEUE_DB_ID` in `.env` locally and on Zo. Ask Ted to add the "🙋 Awaiting Approval" view.

---

### Task 11: Zo automations (tick + watchdog)

No repo files — live Zo configuration via zo tools. Prereqs: Tasks 9–10 done, repo cloned on Zo, `.env` on Zo filled (NOTION_TOKEN, POST_QUEUE_DB_ID, POSTIZ_URL, POSTIZ_API_KEY, ASSET_STORE_TOKEN).

- [ ] **Step 1: Install deps on Zo**: `cd ~/cross-platform-poster && pip install -r requirements.txt` (Zo bash).

- [ ] **Step 2: Create the tick automation** (Zo `create_automation`): every 15 minutes, run `cd ~/cross-platform-poster && python -m src.tick`; instruction: "If the command exits non-zero, SMS Ted: 'cross-platform-poster: <last line of output>'. If exit 0, do nothing."

- [ ] **Step 3: Create the watchdog automation** (Zo `create_automation`): daily 6:30 AM ET, run `cd ~/cross-platform-poster && python -m src.watchdog`; instruction: "If the command exits non-zero, SMS Ted the printed message. If exit 0, do nothing." (The monthly heartbeat rides the same non-zero path by design.)

- [ ] **Step 4: Verify** — trigger the tick automation once manually; confirm exit 0 with empty queue, `~/.cross-platform-poster/last_tick` exists on Zo. Trigger watchdog manually; confirm "healthy" and exit 0 (unless it's the 1st).

---

### Task 12: Full README (incl. **The socket contract** — Ted's human guide) + SPRINT update

**Files:**
- Modify: `README.md`, `SPRINT.md`

- [ ] **Step 1: Write the full 8-section README** (README protocol). Sections: What/Why · Constraints · Setup · Usage · How it works · Configuration · Troubleshooting · Legend. Must include, verbatim as a top-level section:

```markdown
## The socket contract 🔌 (read this, human)

This is the instruction guide for plugging ANYTHING into the poster.

**For a producing project (the appliance):**
1. Copy `adapter/post_queue_adapter.py` into your repo. Never import it across
   repos. Add your repo to **Used By** below.
2. When an asset is finished, call
   `enqueue(client, db_id, project=..., title=..., asset_urls=[...], caption=..., platforms=[...], gate="auto"|"gated")`.
3. Asset URLs must be downloadable by the scheduler (um-assets store URLs work;
   set `ASSET_STORE_TOKEN` if the store needs its X-Token header).
4. Add your project's slots to `channels.yaml` (PR to this repo).

**The Useful Math 3B contract (binding on Descript assembly work):**
- Finished videos land in the final-video output folder (location set in
  Sprint 3B) named **`<person-slug>.mp4`** — the slug must match the Video
  Production row so the watcher can pull title + caption.
- A new MP4 with no matching VP row is never posted; it SMSes Ted instead.

**Ted's setup checklist (one-time per platform):**
- [ ] Google Cloud project + YouTube Data API OAuth creds → Postiz env
- [ ] Meta app (check what survives from useful-math's May-2026 IG token work)
      + @useful_math_ as Business/Creator linked to a FB Page → Postiz env
- [ ] Connect both accounts inside Postiz (Settings → Add Channel)
- [ ] Notion integration + share Post Queue parent page + POST_QUEUE_DB_ID in env
- [ ] Recurring: when SMSed, re-auth Instagram in Postiz (~every 60 days)

**Used By:**
- (none yet — useful-math lands with Sprint 3B's watcher)
```

- [ ] **Step 2: Update `SPRINT.md`** — Phase 1 checked off when true, `Next:` set to the current frontier, `Human:` pruned to what's still open.

- [ ] **Step 3: Commit**

```bash
git add README.md SPRINT.md
git commit -m "docs: full 8-section README with the socket contract (human guide + 3B naming contract); SPRINT current

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: E2E dry-run + PR

- [ ] **Step 1: Enqueue a test row** (local, uses the real DB):

```bash
python - <<'EOF'
import os
from dotenv import load_dotenv
from notion_client import Client
import importlib.util
spec = importlib.util.spec_from_file_location("a", "adapter/post_queue_adapter.py")
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
load_dotenv()
client = Client(auth=os.environ["NOTION_TOKEN"])
a.enqueue(client, os.environ["POST_QUEUE_DB_ID"], project="Useful Math",
          title="E2E dry-run test", asset_urls=["https://example.com/test.mp4"],
          caption="test caption #usefulmath", platforms=["youtube-shorts"], gate="auto")
print("test row created")
EOF
```

- [ ] **Step 2: Dry-run the tick at a fake due time** — temporarily set the youtube-shorts slot in a scratch copy of channels.yaml to the current quarter-hour, then:

Run: `python -m src.tick --dry-run`
Expected: prints `DRY-RUN would post 'E2E dry-run test' -> youtube-shorts (1 asset(s))`, exit 0, row untouched (still Ready).

- [ ] **Step 3: Clean up** — archive the test row in Notion (or leave for the first live test with a real MP4).

- [ ] **Step 4: Open the PR** (never merge — Ted merges):

```bash
git push -u origin v1-build
gh pr create --title "v1: the posting plug — queue client, tick scheduler, Postiz client, adapter, watchdog, deploy" --body "$(cat <<'EOF'
Implements the approved spec (docs/superpowers/specs/2026-07-07-cross-platform-poster-design.md).

- 37 unit tests green; E2E dry-run verified against the real Post Queue
- Postiz live on Zo; tick + watchdog automations created (15-min / daily 6:30 ET)
- README carries the socket contract incl. the 3B `<person-slug>.mp4` naming rule
- Where it leaves the project: Phase 2 done pending Ted's platform credentials (SPRINT Human list); first supervised post is Phase 3

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 5: Session end per protocol** — SPRINT.md `Next:`/`Human:` current (in the PR), Build Journal entry in Notion, remind Ted of open Human items.

---

### Task 14 (Phase 3, after Ted's Human items — separate session)

Not detailed here by design (blocked on external credentials): first supervised live post per platform — real MP4 in the queue, watch the slot fire, verify the Short on @Useful_Math and the Reel on @useful_math_, backfill real permalinks into `Posted Links` format if Postiz returns them, then let it run unattended. Follow-up plan in useful-math repo: the 3B watcher adapter.

---

## Self-review notes

- **Spec coverage:** schema ✓ (T4/T10), slots ✓ (T2/T3), scheduler flow incl. stuck-Posting + partial-platform retry ✓ (T4/T7), adapter + gate + dedup ✓ (T8), Postiz appliance ✓ (T5/T9), error handling/SMS-via-Zo ✓ (T7/T11), watchdog + heartbeat ✓ (T8/T11), dry-run + supervised rollout ✓ (T13/T14), README socket contract + 3B naming ✓ (T12), Human items ✓ (T1/T12), public-repo hygiene ✓ (secrets only in gitignored .env / Zo env).
- **Known deliberate deferral:** Postiz `/posts` and settings payloads are marked verify-against-live-docs (T9 S4) rather than asserted — isolated in `build_settings`/`create_post` so corrections are one commit.
- **Out of this plan:** the useful-math watcher adapter (own plan, own repo, blocked on 3B folder), real permalink extraction from Postiz responses (T14 checks what the API returns).

---

# PIVOT ADDENDUM (2026-07-13) — direct platform APIs on GitHub Actions

**Why:** Zo cannot run containers (kernel blocks namespaces — verified empirically) and
current Postiz additionally requires a Temporal stack. Ted chose direct platform APIs at
$0/mo over a ~$5/mo VPS. See the spec's Pivot section for the full decision record.

**Supersedes:** Task 9 Steps 3–4 (Postiz bring-up — never executed), Task 11 (Zo
automations for the tick), and the Postiz client itself. Tasks 1–8 (executed, reviewed)
and Task 9 Steps 1–2 (compose file, committed) are historical record; the compose file is
REMOVED in Task 9C below. Task 10 (setup_notion) is unchanged. Tasks 12–13 proceed with
the amendments noted at the end.

**New execution order:** 9A (YouTube client) → 9B (Instagram client) → 9C (rewire tick,
remove Postiz artifacts) → 10 (setup_notion, unchanged) → 11′ (GH workflows + watchdog
rework + Zo automation) → 12 (README, amended) → 13 (E2E + PR, amended).

**requirements.txt additions (Task 9A):** `google-api-python-client>=2.100.0`,
`google-auth>=2.23.0`, `google-auth-oauthlib>=1.1.0` (oauthlib is only for the one-time
local token-mint script).

---

### Task 9A: YouTube client (`src/youtube_client.py`) + token-mint script

**Files:**
- Create: `src/youtube_client.py`, `scripts/get_youtube_token.py`
- Modify: `requirements.txt`
- Test: `tests/test_youtube_client.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_youtube_client.py`:

```python
from unittest.mock import MagicMock

from src.youtube_client import post


def _wire(mocker):
    service = MagicMock()
    request = MagicMock()
    request.next_chunk.side_effect = [(None, None), (None, {"id": "vid123"})]
    service.videos.return_value.insert.return_value = request
    mocker.patch("src.youtube_client._service", return_value=service)
    mocker.patch("src.youtube_client.MediaFileUpload")
    return service


def test_post_returns_shorts_url(mocker, tmp_path):
    _wire(mocker)
    f = tmp_path / "hua.mp4"; f.write_bytes(b"x")
    url = post(f, title="Hua Luogeng", caption="cap",
               client_id="ci", client_secret="cs", refresh_token="rt")
    assert url == "https://youtube.com/shorts/vid123"


def test_post_sends_title_description_public(mocker, tmp_path):
    service = _wire(mocker)
    f = tmp_path / "hua.mp4"; f.write_bytes(b"x")
    post(f, title="T" * 150, caption="the caption",
         client_id="ci", client_secret="cs", refresh_token="rt")
    body = service.videos.return_value.insert.call_args.kwargs["body"]
    assert len(body["snippet"]["title"]) == 100          # truncated
    assert body["snippet"]["description"] == "the caption"
    assert body["status"]["privacyStatus"] == "public"
    assert body["status"]["selfDeclaredMadeForKids"] is False
```

- [ ] **Step 2: Run, verify FAIL** (ModuleNotFoundError), after `.venv/bin/pip install`
      of the three new requirements.

- [ ] **Step 3: Implement `src/youtube_client.py`:**

```python
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
```

- [ ] **Step 4: Write `scripts/get_youtube_token.py`** (Ted runs ONCE locally to mint the
      refresh token; not imported by anything):

```python
"""One-time, LOCAL: mint the YouTube refresh token. Usage:
    .venv/bin/python scripts/get_youtube_token.py <client_id> <client_secret>
Opens a browser for consent on the @Useful_Math Google account, prints the
refresh token to paste into the YT_REFRESH_TOKEN GitHub secret. Requires the
OAuth app's redirect config to allow localhost (Desktop-app credentials do)."""
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
```

- [ ] **Step 5: Add the three google deps to requirements.txt, run full suite** (expect
      53 + 2 = 55 passed; the 6 postiz tests still exist at this point).

- [ ] **Step 6: Commit** — `feat: YouTube client — resumable upload via refresh-token flow + one-time token-mint script` (+ trailer).

---

### Task 9B: Instagram client (`src/instagram_client.py`)

**Files:**
- Create: `src/instagram_client.py`
- Test: `tests/test_instagram_client.py`

IG Graph API Reels flow: create container (media_type=REELS, video_url, caption) → poll
`status_code` until FINISHED (bounded) → media_publish → fetch permalink. IG downloads
the video itself from `video_url` — the asset URL must be publicly fetchable. The access
token travels in request params; NEVER let it leak into exception text (it would land in
the Notion Error field) — sanitize.

- [ ] **Step 1: Write the failing tests** — `tests/test_instagram_client.py`:

```python
import pytest

from src.instagram_client import InstagramError, post


def _resp(mocker, payload, status=200):
    r = mocker.MagicMock(status_code=status)
    r.json.return_value = payload
    r.text = str(payload)
    return r


def test_post_happy_path_returns_permalink(mocker):
    posts = [_resp(mocker, {"id": "c1"}), _resp(mocker, {"id": "m1"})]
    gets = [_resp(mocker, {"status_code": "FINISHED"}),
            _resp(mocker, {"permalink": "https://www.instagram.com/reel/AB12/"})]
    mocker.patch("src.instagram_client.requests.post", side_effect=posts)
    mocker.patch("src.instagram_client.requests.get", side_effect=gets)
    mocker.patch("src.instagram_client.time.sleep")
    url = post("https://a/hua.mp4", "cap", ig_user_id="u1", access_token="tok")
    assert url == "https://www.instagram.com/reel/AB12/"


def test_post_container_error_raises(mocker):
    mocker.patch("src.instagram_client.requests.post",
                 side_effect=[_resp(mocker, {"id": "c1"})])
    mocker.patch("src.instagram_client.requests.get",
                 side_effect=[_resp(mocker, {"status_code": "ERROR"})])
    mocker.patch("src.instagram_client.time.sleep")
    with pytest.raises(InstagramError, match="ERROR"):
        post("https://a/x.mp4", "c", ig_user_id="u1", access_token="tok")


def test_post_timeout_raises_after_max_polls(mocker):
    mocker.patch("src.instagram_client.requests.post",
                 side_effect=[_resp(mocker, {"id": "c1"})])
    mocker.patch("src.instagram_client.requests.get",
                 return_value=_resp(mocker, {"status_code": "IN_PROGRESS"}))
    mocker.patch("src.instagram_client.time.sleep")
    with pytest.raises(InstagramError, match="not ready"):
        post("https://a/x.mp4", "c", ig_user_id="u1", access_token="tok",
             max_polls=3)


def test_token_never_in_error_text(mocker):
    bad = _resp(mocker, {"error": {"message": "bad request"}}, status=400)
    bad.text = "boom access_token=SECRETTOK details"
    mocker.patch("src.instagram_client.requests.post", return_value=bad)
    with pytest.raises(InstagramError) as exc:
        post("https://a/x.mp4", "c", ig_user_id="u1", access_token="SECRETTOK")
    assert "SECRETTOK" not in str(exc.value)
```

- [ ] **Step 2: Run, verify FAIL.**

- [ ] **Step 3: Implement `src/instagram_client.py`:**

```python
"""Publish a Reel via the Instagram Graph API. IG fetches the video itself
from a PUBLIC video_url (no local file). Long-lived token (~60 days) arrives
from the caller; a scheduled workflow rotates it. The token travels in
request params — every error path sanitizes it out of messages, since tick
stamps exception text into the Notion Error field."""
import time

import requests

GRAPH = "https://graph.facebook.com/v21.0"
TIMEOUT = (10, 60)


class InstagramError(Exception):
    pass


def _json_or_raise(r, label: str, token: str) -> dict:
    if r.status_code != 200:
        raise InstagramError(
            f"{label} -> HTTP {r.status_code}: "
            + r.text[:300].replace(token, "***"))
    try:
        return r.json()
    except ValueError:
        raise InstagramError(
            f"{label} -> non-JSON response: "
            + r.text[:300].replace(token, "***")) from None


def post(video_url: str, caption: str, *, ig_user_id: str, access_token: str,
         poll_seconds: int = 15, max_polls: int = 40) -> str:
    """Create+publish a Reel from a public video URL; return the permalink."""
    container = _json_or_raise(requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={"media_type": "REELS", "video_url": video_url,
              "caption": caption[:2200], "access_token": access_token},
        timeout=TIMEOUT), "create container", access_token)["id"]

    for _ in range(max_polls):
        status = _json_or_raise(requests.get(
            f"{GRAPH}/{container}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=TIMEOUT), "container status", access_token)["status_code"]
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise InstagramError(f"container {container} -> status ERROR "
                                 "(IG could not process the video_url)")
        time.sleep(poll_seconds)
    else:
        raise InstagramError(
            f"container {container} not ready after {max_polls} polls")

    media = _json_or_raise(requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": container, "access_token": access_token},
        timeout=TIMEOUT), "media_publish", access_token)["id"]

    perm = _json_or_raise(requests.get(
        f"{GRAPH}/{media}",
        params={"fields": "permalink", "access_token": access_token},
        timeout=TIMEOUT), "fetch permalink", access_token)
    return perm.get("permalink") or f"ig:{media}"
```

- [ ] **Step 4: Run, verify 4 passed; full suite expect 59.**

- [ ] **Step 5: Commit** — `feat: Instagram client — Reels container/poll/publish flow, token-sanitized errors` (+ trailer).

---

### Task 9C: Rewire tick to the platform registry; remove Postiz artifacts

**Files:**
- Modify: `src/tick.py`, `tests/test_tick.py`, `.env.example`
- Delete: `src/postiz_client.py`, `tests/test_postiz_client.py`, `deploy/postiz/` (compose + .env.example)

- [ ] **Step 1: Rewire `src/tick.py`.** Replace the postiz imports and `_publish` body:

```python
from src.instagram_client import post as ig_post
from src.youtube_client import post as yt_post


def _post_youtube(fields, tmp):
    paths = download_assets(fields["asset_urls"], tmp,
                            token=os.environ.get("ASSET_STORE_TOKEN"))
    return yt_post(paths[0], fields["title"], fields["caption"],
                   client_id=os.environ["YT_CLIENT_ID"],
                   client_secret=os.environ["YT_CLIENT_SECRET"],
                   refresh_token=os.environ["YT_REFRESH_TOKEN"])


def _post_instagram(fields, tmp):
    # IG fetches the video itself — no download; asset URL must be public.
    return ig_post(fields["asset_urls"][0], fields["caption"],
                   ig_user_id=os.environ["IG_USER_ID"],
                   access_token=os.environ["IG_ACCESS_TOKEN"])


PLATFORM_POSTERS = {"youtube-shorts": _post_youtube, "ig-reels": _post_instagram}
```

`_publish` becomes: unknown-platform check against `PLATFORM_POSTERS` (same fail-fast
semantics as before, ValueError is fine now that PostizError is gone); dry-run early
return unchanged; then `mark_posting` → `with tempfile.TemporaryDirectory() as tmp: url =
PLATFORM_POSTERS[platform](fields, tmp)` inside the same try/except-stamp-reraise;
`record_result(url=url)` — REAL permalinks now, no `postiz:` placeholder. `run_tick` and
`main()` lose the postiz parameter entirely (update signature and all tests; `main()` no
longer constructs a PostizClient and drops POSTIZ_URL/POSTIZ_API_KEY).

- [ ] **Step 2: Update `tests/test_tick.py`:** drop the postiz mock from `_wire` (patch
`src.tick.yt_post` / `src.tick.ig_post` instead, returning permalink strings), drop the
`postiz=` arg everywhere, keep every behavioral assertion (happy path now asserts
`record_result` got the permalink; dry-run asserts neither poster was called; the
same-row-two-platforms integration test patches both posters). Add
`test_unknown_platform_fails_before_marking` (platform "linkedin" in cfg → exit 1,
mark_posting not called).

- [ ] **Step 3: Update `.env.example`:** remove POSTIZ_URL/POSTIZ_API_KEY; add
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, `IG_USER_ID`, `IG_ACCESS_TOKEN`
(comment: set as GitHub Actions secrets; NOTION_TOKEN also in Zo env for the watchdog).

- [ ] **Step 4: `git rm src/postiz_client.py tests/test_postiz_client.py deploy/postiz -r`**

- [ ] **Step 5: Run full suite** (expect 59 − 6 postiz + 1 new = 54 passed).

- [ ] **Step 6: Commit** — `refactor: tick posts via direct platform clients; drop Postiz (Zo can't run containers; see spec Pivot)` (+ trailer).

---

### Task 11′: GitHub Actions workflows + watchdog rework + Zo automation

**Files:**
- Create: `.github/workflows/tick.yml`, `.github/workflows/refresh-ig-token.yml`, `scripts/refresh_ig_token.py`
- Modify: `src/watchdog.py`, `tests/test_watchdog.py`, `src/tick.py` (remove stamp logic), `tests/test_tick.py`

- [ ] **Step 1: `.github/workflows/tick.yml`:**

```yaml
# The poster's heartbeat. Failure alerting is the Zo watchdog's job (it reads
# this workflow's run status via the GitHub API) — SMS logic stays out of the
# Action, same division as useful-math's producer/watchdog pair.
name: Post Queue Tick
on:
  schedule:
    - cron: '*/15 * * * *'
  workflow_dispatch:
    inputs:
      dry_run:
        description: 'Dry run (log what would post, touch nothing)'
        type: boolean
        default: false
concurrency:
  group: tick
  cancel-in-progress: false
jobs:
  tick:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - name: Run tick
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          POST_QUEUE_DB_ID: ${{ secrets.POST_QUEUE_DB_ID }}
          YT_CLIENT_ID: ${{ secrets.YT_CLIENT_ID }}
          YT_CLIENT_SECRET: ${{ secrets.YT_CLIENT_SECRET }}
          YT_REFRESH_TOKEN: ${{ secrets.YT_REFRESH_TOKEN }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          ASSET_STORE_TOKEN: ${{ secrets.ASSET_STORE_TOKEN }}
        run: python -m src.tick ${{ inputs.dry_run && '--dry-run' || '' }}
```

- [ ] **Step 2: `scripts/refresh_ig_token.py`** (adapted from useful-math's
`refresh_instagram_token.py` — read that file first and reuse its endpoint usage):

```python
"""Refresh the IG long-lived token (60-day expiry) and print the new one.
Run monthly by refresh-ig-token.yml, which stores it back into the repo
secret via ADMIN_PAT. Exits non-zero on any failure (watchdog notices the
failed workflow run)."""
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
```

- [ ] **Step 3: `.github/workflows/refresh-ig-token.yml`:**

```yaml
name: Refresh IG Token
on:
  schedule:
    - cron: '0 9 5 * *'   # 5th of each month — well inside the 60-day window
  workflow_dispatch: {}
jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install requests
      - name: Refresh and rotate the secret
        env:
          FB_APP_ID: ${{ secrets.FB_APP_ID }}
          FB_APP_SECRET: ${{ secrets.FB_APP_SECRET }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          GH_TOKEN: ${{ secrets.ADMIN_PAT }}
        run: |
          NEW_TOKEN=$(python scripts/refresh_ig_token.py)
          gh secret set IG_ACCESS_TOKEN --body "$NEW_TOKEN" --repo ${{ github.repository }}
```

- [ ] **Step 4: Rework `src/watchdog.py`.** Replace the stamp-file freshness check with a
GitHub API check (public repo — no token needed); keep the stuck-rows check (unchanged)
and rework the heartbeat gate for hourly runs:

```python
GITHUB_REPO = "tedico/cross-platform-poster"
TICK_WORKFLOW = "tick.yml"
NO_RUN_ALARM = 45 * 60      # three missed 15-min ticks
FAILURE_WINDOW = 60 * 60    # hourly watchdog: alert once per failed run


def tick_run_problems(now, repo=GITHUB_REPO, workflow=TICK_WORKFLOW) -> list:
    """Freshness + failure problems from the workflow's recent runs."""
    r = requests.get(
        f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs",
        params={"per_page": 20}, timeout=(10, 30))
    if r.status_code != 200:
        return [f"GitHub API -> HTTP {r.status_code} (cannot check tick runs)"]
    runs = r.json().get("workflow_runs", [])
    problems = []
    completed = [x for x in runs if x["status"] == "completed"]
    if not completed:
        problems.append("tick workflow has no completed runs")
    else:
        newest = datetime.fromisoformat(
            completed[0]["updated_at"].replace("Z", "+00:00"))
        if (now - newest).total_seconds() > NO_RUN_ALARM:
            problems.append(
                f"no completed tick run in {int((now - newest).total_seconds() // 60)} min")
    recent_failures = [
        x for x in completed
        if x["conclusion"] not in ("success", "skipped", "cancelled")
        and (now - datetime.fromisoformat(
            x["updated_at"].replace("Z", "+00:00"))).total_seconds() < FAILURE_WINDOW]
    if recent_failures:
        problems.append(
            f"{len(recent_failures)} failed tick run(s) in the last hour: "
            + recent_failures[0]["html_url"])
    return problems
```

`check(notion, db_id, now=None)` becomes: `problems = tick_run_problems(now) +
<stuck-rows check as-is>`; heartbeat fires only when `now.day == 1` AND the run is in the
6 AM ET hour (`now.astimezone(ZoneInfo("America/New_York")).hour == 6`) — the watchdog
now runs hourly and must not heartbeat 24×. Drop the stamp/STAMP_DIR import and stamp
tests; also remove the stamp logic from `src/tick.py` (STAMP_DIR, stamp_dir param, the
write) and its two test assertions — GH API is now the liveness source.

- [ ] **Step 5: Update tests.** test_watchdog.py: mock `requests.get` for
tick_run_problems (fresh successful run → healthy; 2h-old newest run → "no completed
tick run"; failed run 10 min ago → "failed tick run"; GitHub API 500 → problem line);
heartbeat test pins day==1 + 6 AM ET + healthy → (1, heartbeat); day==1 at noon ET →
(0, healthy). Keep stuck-row tests as-is. test_tick.py: remove stamp assertions.

- [ ] **Step 6: Run full suite; commit** — `feat: GH Actions tick + monthly IG token rotation; watchdog reads workflow runs via GitHub API (stamp file retired)` (+ trailer).

- [ ] **Step 7 (live, coordinator):** Zo automation "cross-platform-poster watchdog":
hourly, runs `cd ~/cross-platform-poster && .venv/bin/python -m src.watchdog` (repo
cloned on Zo, venv + requirements installed, NOTION_TOKEN + POST_QUEUE_DB_ID in
~/cross-platform-poster/.env); instruction: SMS Ted the printed message iff exit
non-zero. NOTE: workflows only run on the default branch — the tick cron goes live when
the PR merges to main; until then use workflow_dispatch on the branch for testing.

---

### Amendments to Tasks 12–13

- **Task 12 (README):** env-var table now lists the GH secrets (YT_*, IG_*, FB_APP_*,
  ADMIN_PAT, NOTION_TOKEN, POST_QUEUE_DB_ID, ASSET_STORE_TOKEN); "How it works" describes
  GH Actions tick + Zo watchdog split; Ted's checklist gains: mint YouTube refresh token
  via scripts/get_youtube_token.py, set OAuth app to production, create ADMIN_PAT; drop
  every Postiz mention. Socket contract section unchanged EXCEPT: note asset URLs must be
  PUBLIC (IG fetches them directly).
- **Task 13 (E2E + PR):** dry-run via `gh workflow run tick.yml -f dry_run=true --ref
  v1-build` once secrets exist (or locally as before with a .env). PR body updated for
  the pivot. Supervised first-post task (14) unchanged in spirit.

