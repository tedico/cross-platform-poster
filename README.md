# cross-platform-poster

## What / Why

A universal posting plug — a power outlet for content. Any of Ted's projects (the
appliances) plugs a finished asset into the **Post Queue** (a Notion database); scheduled
slots then publish it via direct YouTube / Instagram API clients running on a GitHub
Actions cron. Consumers never touch platform credentials or upload code — they copy one
adapter file and call `enqueue()`.

Why it exists: every content pipeline (Useful Math, Super Psychology, Athena,
KontentMaschine, future carousel engines) ends at the same wall — "asset is done, now
post it." Posting is shared infrastructure, like Alexandria: one service, thin copied
adapters, never embedded per-project.

History note: v1 was originally designed around self-hosted Postiz on Zo; it was pivoted
to direct API clients because Zo's kernel cannot run containers — the full record is in
the Pivot section of `docs/superpowers/specs/2026-07-07-cross-platform-poster-design.md`.

## Constraints

- **$0/mo stack**: GitHub Actions cron on this public repo + Notion + a Zo automation for
  the watchdog. No servers, no containers.
- **Scheduled workflows run only on the default branch.** Nothing posts (and the watchdog
  alarms "no completed tick run") until the code is merged to `main`.
- **GitHub cron jitter can skip a day's slot** — if a scheduled run lands past its 15-min
  cell, that slot is missed. Accepted trade-off: the row simply posts at the next day's
  slot.
- **Asset URLs must be PUBLICLY fetchable.** Instagram's API downloads the video itself
  from the URL in the row — a private URL fails the container step every time.
- **IG long-lived tokens expire after ~60 days.** The `Refresh IG Token` workflow rotates
  the `IG_ACCESS_TOKEN` secret monthly (5th of each month) so it never lapses.
- **The YouTube OAuth app must be in PRODUCTION status**, or Google expires the refresh
  token after 7 days and every upload dies with `invalid_grant`.
- **`ig-carousel` exists in the Post Queue schema but has NO poster client yet.** Do not
  tag rows with it: a multi-platform row including `ig-carousel` returns to `Ready` after
  its other platforms post and sits there forever (a row is only `Posted` once every
  tagged platform has a permalink).

## Setup

Ted's one-time checklist, in order. First, bootstrap the local venv:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

1. **YouTube credentials** (slowest item — start first). Create a Google Cloud project,
   enable the YouTube Data API v3, create **Desktop app** OAuth credentials. Mint the
   refresh token locally (opens a browser; consent as `@Useful_Math`):

   ```bash
   .venv/bin/python scripts/get_youtube_token.py <client_id> <client_secret>
   ```

   Then set the OAuth app to **production** status (testing-status refresh tokens die in
   7 days).
2. **Instagram credentials.** DONE — useful-math's May-2026 Meta app and its live
   long-lived token (`@useful_math_`) got reused. The token is from the **"Instagram API
   with Instagram Login"** family: it authenticates against `graph.instagram.com` and
   refreshes via the `ig_refresh_token` flow (no Meta app id/secret needed at runtime).
3. **Notion.** Create an integration named "cross-platform-poster", share a parent page
   with it, then create the Post Queue DB:

   ```bash
   .venv/bin/python setup_notion.py <parent-page-url>
   ```

   It prints `POST_QUEUE_DB_ID`. Add the "🙋 Awaiting Approval" filtered view
   (Status = Awaiting Approval) manually in Notion.
4. **GitHub repo secrets** (Settings → Secrets and variables → Actions): `NOTION_TOKEN`,
   `POST_QUEUE_DB_ID`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`,
   `IG_USER_ID`, `IG_ACCESS_TOKEN`, `ASSET_STORE_TOKEN`
   (optional — see Configuration).
5. **ADMIN_PAT secret**: a fine-grained GitHub PAT scoped to this repo with secrets
   read+write, so the monthly workflow can rotate `IG_ACCESS_TOKEN`.
6. **After merge to main**: manually dispatch the "Post Queue Tick" workflow once with
   `dry_run=true` and check its log. Then set up the hourly Zo automation for the
   watchdog — pick a mid-hour minute like `:30`, NOT `:59` (the monthly heartbeat gate
   needs a run inside the 6 AM ET hour). Prereqs on Zo: this repo cloned at
   `~/cross-platform-poster` with a `.env` containing `NOTION_TOKEN` and
   `POST_QUEUE_DB_ID`; the automation runs `python -m src.watchdog` and SMSes Ted on
   non-zero exit.
7. **Verify the token-refresh flow**: manually dispatch "Refresh IG Token" once. The
   script uses the `ig_refresh_token` flow against `graph.instagram.com` — the same flow
   useful-math's `refresh_instagram_token.py` has run monthly against this exact token
   family.

## Usage

How a row flows:

1. A producing project's copied adapter calls `enqueue(...)` when an asset is finished.
   `gate="auto"` rows land as `Ready`; `gate="gated"` rows land as `Awaiting Approval`.
2. Gated rows wait in the "🙋 Awaiting Approval" view until Ted flips Status to `Ready`.
3. At the next due slot for that project+platform (see `channels.yaml`), the tick posts
   the oldest eligible `Ready` row to that platform.
4. **Posted Links** collects one `platform: url` line per successful platform; when every
   tagged platform has a link, the row becomes `Posted`.

Manual operations:

- **Dry run**: dispatch the "Post Queue Tick" workflow with `dry_run=true` — logs what
  WOULD post, touches nothing.
- **Retry a Failed row**: read its **Error** field first, fix the cause, then flip Status
  back to `Ready`. Platforms already in Posted Links are never re-posted.
- **Row stuck in Posting** (tick crashed mid-flight; the >1h sweep marks it `Failed` with
  a recovery note): check whether the post actually EXISTS on the platform. If it does,
  add a `platform: url` line to **Posted Links** BEFORE re-Ready-ing — otherwise the tick
  will post it again. If it doesn't exist, just re-Ready.

## The socket contract 🔌 (read this, human)

This is the instruction guide for plugging ANYTHING into the poster.

**For a producing project (the appliance):**
1. Copy `adapter/post_queue_adapter.py` into your repo. Never import it across
   repos. Add your repo to **Used By** below.
2. When an asset is finished, call
   `enqueue(client, db_id, project=..., title=..., asset_urls=[...], caption=..., platforms=[...], gate="auto"|"gated")`.
3. Asset URLs must be PUBLICLY downloadable (Instagram fetches them directly;
   YouTube's client downloads then uploads — set `ASSET_STORE_TOKEN` only if
   your store needs its X-Token header for the YouTube path).
4. Add your project's slots to `channels.yaml` and its Notion name to
   `project_names` in `src/tick.py` `main()` (PR to this repo).

**The Useful Math 3B contract (binding on Descript assembly work):**
- Finished videos land in the final-video output folder (location set in
  Sprint 3B) named **`<person-slug>.mp4`** — the slug must match the Video
  Production row so the watcher can pull title + caption.
- A new MP4 with no matching VP row is never posted; it SMSes Ted instead.

**Used By:**
- (none yet — useful-math lands with Sprint 3B's watcher)

## How it works

**Post Queue schema** (the plug standard — all state lives here):

| Field | Type | Notes |
|---|---|---|
| Title | title | Post title / first caption line |
| Project | select | `Useful Math`, later: `Super Psychology`, `Athena`, … |
| Asset URL(s) | text | One or more URLs (newline-separated; um-assets store for UM). **Must be publicly fetchable** — IG's API pulls the video from this URL directly |
| Asset Type | select | `video`, `image-set` |
| Caption | text | Platform-ready caption incl. hashtags |
| Platforms | multi-select | `youtube-shorts`, `ig-reels`, `ig-carousel`, `linkedin`, … |
| Status | select | `Awaiting Approval` → `Ready` → `Posting` → `Posted` / `Failed` |
| Posted Links | text | Permalinks per platform (`platform: url` lines), stamped by the tick |
| Error | text | Failure detail, stamped by the tick |
| (created time) | built-in | Drives oldest-first draining — Notion's automatic timestamp, no column needed |

**Tick** (`src/tick.py`, GitHub Actions cron every 15 min): quantizes the tick time down
to the 15-minute grid and compares it against each slot in that slot's own timezone, so a
slot fires exactly once per day regardless of cron jitter. For each due project+platform
it takes the oldest `Ready` row tagged with that platform and not yet in its Posted
Links, fails fast if any required secret is missing or empty (GH Actions maps unset
secrets to empty strings — the row is left `Ready`), marks the row `Posting`, dispatches
to the platform client, and stamps the result: success writes the permalink into Posted
Links per platform (the row returns to `Ready` until ALL tagged platforms are done, then
`Posted`); any failure writes `Failed` + the Error field. It also sweeps rows sitting in
`Posting` for over an hour (a crashed tick) into `Failed` with a recovery note. A
non-zero exit + printed summary is what the watchdog turns into an SMS.

**Platform clients** — each exposes one `post(...) -> permalink` function; adding a
platform = one client module + one registry entry in `src/tick.py`.
`src/youtube_client.py` downloads the first asset (via `src/assets.py`, optional X-Token
header) and does a resumable YouTube Data API v3 upload with the OAuth refresh-token flow
— no browser, no token files; a vertical <3 min video auto-classifies as a Short.
`src/instagram_client.py` never downloads: it creates a Reels container from the public
asset URL, polls `status_code` until `FINISHED` (bounded), then publishes and fetches the
permalink; every error path sanitizes the access token out of exception text (the tick
stamps exceptions into the Notion Error field), and nothing after a successful publish
may raise (else a LIVE Reel's row would go `Failed` and re-post on re-Ready).

**Watchdog** (`src/watchdog.py`, hourly Zo automation): GitHub Actions runners are
ephemeral, so liveness comes from run history via the public GitHub API (retried once on
API blips). It alarms on: no completed tick run in 45 min (three missed ticks), any
failed tick run in the last 90 min, the monthly IG-token-refresh workflow failing or
stale >35 days (once it has ever run), and rows stuck in `Posting` >1h. At 6 AM ET on the
1st of the month it force-exits non-zero with a heartbeat message — a monthly SMS proving
the alarm channel itself works. Non-zero exit + printed message = the Zo automation SMSes
Ted; SMS logic stays out of the GitHub Action.

**Status machine:**

```
                enqueue(gate="gated")            enqueue(gate="auto")
                        │                                │
                        ▼                                ▼
              Awaiting Approval ──Ted flips──────────▶ Ready ◀────────────┐
                                                         │                │
                                                    due slot              │ more platforms
                                                         ▼                │ still untagged
                                                      Posting ────────────┤
                                                         │                │
                              ┌──────────────────────────┼────────────┐   │
                              ▼                          ▼            │   │
                     error / stuck >1h        all platforms stamped   │   │
                              │                          │            └───┘
                              ▼                          ▼
                           Failed ──fix + re-Ready──▶ Ready
```

## Configuration

**`channels.yaml`** — slots ONLY; the approval gate lives in each project's copied
adapter call, never here:

```yaml
useful-math:
  platforms:
    youtube-shorts: { slot: "12:00", tz: "America/New_York", cadence: daily }
    ig-reels:       { slot: "12:00", tz: "America/New_York", cadence: daily }
```

Slots must be zero-padded `HH:MM`, quantized to `:00/:15/:30/:45`, with a valid IANA
timezone; `cadence` currently only accepts `daily`. `src/config_loader.py` rejects
anything else at startup.

**Environment variables / secrets** (`.env.example` mirrors this, with one exception:
`ADMIN_PAT` is workflow-only — consumed by `gh` in `refresh-ig-token.yml`, never by
Python — so it's a GH secret only and not in `.env.example`):

| Variable | Lives in | Purpose |
|---|---|---|
| `NOTION_TOKEN` | GH secret + Zo `.env` | cross-platform-poster Notion integration token |
| `POST_QUEUE_DB_ID` | GH secret + Zo `.env` | Post Queue DB id (printed by `setup_notion.py`) |
| `YT_CLIENT_ID` | GH secret | Google Cloud OAuth (Desktop app) client id |
| `YT_CLIENT_SECRET` | GH secret | Google Cloud OAuth client secret |
| `YT_REFRESH_TOKEN` | GH secret | minted once via `scripts/get_youtube_token.py` |
| `IG_USER_ID` | GH secret | Instagram Business account id |
| `IG_ACCESS_TOKEN` | GH secret | Instagram-Login long-lived token; rotated monthly by `refresh-ig-token.yml` |
| `ASSET_STORE_TOKEN` | GH secret (optional) | X-Token header for downloading from um-assets (YouTube path only) |
| `ADMIN_PAT` | GH secret | fine-grained PAT (this repo, secrets read+write) so the refresh workflow can rotate `IG_ACCESS_TOKEN` |

**Fail-fast behavior**: before touching a row, the tick checks the platform's required
secrets (`REQUIRED_ENV` in `src/tick.py`) and raises if any is missing or EMPTY — GH
Actions maps an unset secret to an empty string, which would otherwise fail cryptically
mid-upload and burn the queue row. The row stays `Ready`; the printed `FAILED` line
fires once per due slot (daily per platform) until the secret is set.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `FAILED ...: missing or empty env secret(s): ...` at each due slot | GH repo secret unset (Actions maps unset → empty string) | Set the listed secrets in Settings → Secrets; row is still `Ready`, no action on it needed |
| Row `Failed`, Error shows an IG message with `***` in it | Token sanitized out of an IG API error: asset URL not publicly fetchable, invalid/expired token, or IG couldn't process the video | Verify the asset URL opens in a private browser window; check token validity; re-Ready after fixing |
| Row stuck in `Posting` | Tick crashed mid-flight; the >1h sweep will mark it `Failed` with a recovery note | If the post EXISTS on the platform, add `platform: url` to Posted Links BEFORE re-Ready (else it re-posts); if absent, just re-Ready |
| SMS: `N failed tick run(s) in the last 90 min: <run-url>` | A tick run exited non-zero | Open the run URL, read the last `FAILED`/`TICK CRASHED` line, then match it against the other rows in this table |
| SMS: `no completed tick run in N min` | Scheduled workflows only run on the default branch; or GitHub auto-disabled the schedule after 60 days without repo activity | Merge to `main`; or re-enable BOTH workflows (tick AND refresh) under Actions → select workflow → Enable |
| Heartbeat SMS on the 1st of the month | Monthly proof-of-life that the watchdog + SMS channel work | No action needed |
| YouTube upload fails with `invalid_grant` | Refresh token expired — OAuth app not in production status (testing tokens die in 7 days) | Set the app to production, re-run `scripts/get_youtube_token.py`, update `YT_REFRESH_TOKEN` |
| `Refresh IG Token` dispatch fails with HTTP 400 | Token is not from the Instagram-Login family (`ig_refresh_token` flow), or it expired past the 60-day window | Mint a fresh Instagram-Login long-lived token (see useful-math's May-2026 token work) and update `IG_ACCESS_TOKEN` |

## Legend

**Status values**: `Awaiting Approval` (gated, waiting for Ted) → `Ready` (eligible at
the next due slot) → `Posting` (a tick is working it) → `Posted` (all platforms stamped)
/ `Failed` (see Error field).

**Platform slugs**: `youtube-shorts`, `ig-reels` (live) · `ig-carousel`, `linkedin`
(schema only — no client yet, do not tag).

**File map**:

- `src/tick.py` — the scheduler tick: due slots → due rows → platform clients → stamp results (`python -m src.tick [--dry-run]`)
- `src/slots.py` — which project+platform slots are due at this quantized 15-min tick
- `src/config_loader.py` — load + validate `channels.yaml`
- `src/queue_client.py` — all reads/writes against the Post Queue Notion DB (scheduler-side schema)
- `src/assets.py` — download asset URLs to temp files (optional X-Token header)
- `src/youtube_client.py` — YouTube Data API v3 resumable upload, refresh-token flow
- `src/instagram_client.py` — Instagram API (Instagram Login, `graph.instagram.com`) Reels container → poll → publish, token-sanitized errors
- `src/watchdog.py` — hourly health check on Zo: workflow runs via GitHub API + stuck rows + monthly heartbeat
- `adapter/post_queue_adapter.py` — the one file consumers COPY; `enqueue()` with dedup + gate
- `scripts/get_youtube_token.py` — one-time local mint of the YouTube refresh token
- `scripts/refresh_ig_token.py` — refresh the IG long-lived token via `ig_refresh_token` (run by the monthly workflow)
- `setup_notion.py` — one-time creation of the Post Queue DB (prints `POST_QUEUE_DB_ID`)
- `.github/workflows/tick.yml` — "Post Queue Tick": 15-min cron + manual dispatch with `dry_run`
- `.github/workflows/refresh-ig-token.yml` — "Refresh IG Token": monthly (5th, 09:00 UTC), rotates the secret via `ADMIN_PAT`
- `channels.yaml` — publish slots per project+platform (slots only — gate lives in the adapter)
- `.env.example` — annotated list of every secret/env var
