# cross-platform-poster — Design Spec

**Date:** 2026-07-07 (revised 2026-07-13: direct platform APIs on GitHub Actions — see Pivot)
**Status:** Approved design, implementation in progress
**Repo:** `tedico/cross-platform-poster` (public)

## What / Why

A standalone "power outlet" posting service: any of Ted's content projects (the appliances)
can plug a finished asset into it, and it publishes that asset to the right social platforms
on a steady schedule. Projects never carry platform credentials or upload code; the outlet
never knows how an asset was produced.

Built because every pipeline (Useful Math, Super Psychology, Athena, KontentMaschine, future
carousel engines) ends at the same wall: "asset is done, now post it." Posting is
infrastructure, like Alexandria — one shared service, thin copied adapters, never embedded
per-project.

## Pivot (2026-07-13): Postiz → direct platform APIs

The original design ran self-hosted Postiz in Docker on Zo. Two facts killed it during
implementation, verified empirically:

1. **Zo cannot run containers at all** — its kernel blocks namespace creation
   (`unshare: Operation not permitted`), which is fatal for Docker, Podman, and every
   other runtime.
2. **Current Postiz (≥v2.12) requires a Temporal workflow stack** (4 extra containers
   incl. Elasticsearch) — a much bigger appliance than the one we designed around.

Options evaluated: Postiz on a paid VPS (~$5/mo, zero code change), hosted Postiz cloud,
native-from-source on Zo, or direct platform APIs. **Ted chose direct APIs** on
maintain-code-not-systems grounds: two small Python clients vs. a pet server running a
7-container stack; full platform API depth vs. only what Postiz exposes; and the posting
clients are a dress rehearsal for KontentMaschine's own auto-post feature. $0/mo.

What changed: `postiz_client.py` is replaced by `youtube_client.py` + `instagram_client.py`;
the scheduler tick runs on **GitHub Actions cron** (free on this public repo) instead of a
Zo automation; the watchdog checks the workflow's run status via the GitHub API (the exact
pattern useful-math's watchdog already uses). Everything else — Post Queue schema, slots,
queue client, adapter, status machine — is unchanged.

## Goals

- One central queue where every queued/posted asset across all projects is visible.
- Per-project approval gate: a project is either `auto` (rows post without review) or
  `gated` (Ted flips a status in Notion before anything goes live).
- Per-channel publish slots: bursts of production become a steady drip (e.g. one post/day
  per platform).
- No silent failures — SMS on every failure (via the Zo watchdog), watchdog on the service
  itself, monthly heartbeat proving the watchdog is alive.
- $0/mo: public-repo GitHub Actions + Zo (already owned) + Notion (already owned).

## Non-goals

- Producing or editing assets (that's the projects' job).
- Analytics/engagement tracking.
- Caption generation (arrives with the asset).
- Comment management, DMs, or anything interactive.
- Platform breadth beyond what's wired (each new platform is a deliberate new client).

## v1 scope

**Consumer:** Useful Math only.
**Platforms:** YouTube Shorts (`@Useful_Math`) + Instagram Reels (`@useful_math_`) — the
same MP4 fans out to both.
**Dependency:** finished MP4s come from Sprint 3B (Descript assembly) dropping files into a
final-video output folder. The poster is built and dry-run tested before 3B ships; the
first live post uses a manually placed MP4.

Future consumers (schema-ready, not wired): Super Psychology (IG Reels), Athena
(IG carousel — `image-set` asset type exists for this), LinkedIn, KontentMaschine.

## Architecture

```
[Useful Math]──watcher adapter──┐
[future projects]───adapters────┤→ Post Queue (Notion DB) ← Ted approves gated rows
                                          ↑↓
                     Tick (GitHub Actions cron, every 15 min)
                      ├─ youtube_client → YouTube Data API (@Useful_Math)
                      └─ instagram_client → IG API w/ Instagram Login (@useful_math_)
                                          ↑
                     Watchdog (Zo automation, hourly) — checks the workflow's
                     run status via GitHub API + stuck rows via Notion → SMS
```

Components:

1. **Post Queue** — a Notion database owned by this project. The fixed schema IS the plug
   standard. All state lives here. (Unchanged from original design.)
2. **Tick** — `src/tick.py`, run by a GitHub Actions cron every 15 minutes. Reads
   channels.yaml slots, drains at most one row per project+platform per due slot,
   dispatches to the platform client, stamps results back on the row.
3. **Platform clients** — `src/youtube_client.py` (YouTube Data API v3 resumable upload,
   OAuth refresh-token flow) and `src/instagram_client.py` (Instagram API with Instagram
   Login — `graph.instagram.com` — Reels container → poll → publish flow, long-lived
   token). Each exposes one `post(...) -> permalink`
   function; the platform registry in tick maps platform names to clients. Adding a
   platform = adding one client module + one registry entry.
4. **Adapters** — one canonical file consumers COPY (Alexandria pattern, `Used By`
   stamping). Unchanged.
5. **Watchdog** — `src/watchdog.py`, run by a Zo automation hourly (Zo runs Python fine;
   it just can't run containers). Checks: (a) the tick workflow's latest runs via the
   public GitHub API — any failed run in the last 90 minutes (drift margin), or no completed run in the last
   45 min → problem; (b) rows stuck in Posting >1h via Notion; (c) on the 1st of the
   month (6–7 AM ET run only), a heartbeat SMS proving the alarm channel works. Non-zero
   exit + printed message = the Zo automation SMSes Ted. SMS logic stays out of the
   Action — same division as useful-math's producer/watchdog pair.

## Post Queue DB schema

(Unchanged.)

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
| Date Added | created time | Drives oldest-first draining |

Status semantics unchanged: gated adapters create `Awaiting Approval` (Ted flips to
`Ready` in a "🙋 Awaiting Approval" view); auto adapters create `Ready`; one row fans out
to multiple platforms whose slots may fire at different times — after each platform
attempt the row returns to `Ready` until all platforms are stamped (`Posted`), any
failure → `Failed`; platforms already in `Posted Links` are never re-posted.

## Channel config — `channels.yaml`

(Unchanged: slots only, adapter owns the gate.) UM slots Sun/Tue/Thu 00:00 ET for both
platforms (AutoShorts cadence parity), via the optional per-platform `days:` list —
absent `days:` means daily.

**GitHub Actions cron jitter (accepted trade-off):** scheduled workflows can be delayed;
if a run lands past its 15-min cell, that day's slot is skipped and the row simply posts
at the next day's slot. For a 1/day cadence with a slowly-drained queue this is benign.
Revisit (grace-window logic) only if skips are observed in practice.

## Platform clients — contracts

**YouTube (`youtube_client.py`):** OAuth2 refresh-token flow (client id + secret +
refresh token from GH secrets); downloads the asset file (via `assets.py`), resumable
upload with `snippet.title` = row Title, `snippet.description` = Caption,
`status.privacyStatus=public`, `status.selfDeclaredMadeForKids=false`. Vertical <3 min
video is auto-classified as a Short. Returns `https://youtube.com/shorts/<videoId>`.
⚠️ Verify during implementation: the OAuth app must be in **production** status (not
testing) or refresh tokens expire after 7 days; confirm current unverified-app limits for
a single-user `youtube.upload`-scope app against Google's docs.

**Instagram (`instagram_client.py`):** Instagram API with Instagram Login
(`graph.instagram.com`) with IG_USER_ID + long-lived IG_ACCESS_TOKEN (GH secrets).
No file download — IG pulls from the public asset URL:
create media container (`media_type=REELS`, `video_url`, `caption`) → poll container
`status_code` until `FINISHED` (bounded wait) → `media_publish` → fetch permalink.
Returns the permalink. Long-lived Instagram-Login tokens last ~60 days; a scheduled
monthly GH workflow refreshes the token via the `ig_refresh_token` flow (same flow as
useful-math's `refresh_instagram_token.py` — no Meta app id/secret involved) and updates
the repo secret via a fine-grained PAT (`ADMIN_PAT`, Human item).

Both clients raise loud, descriptive exceptions; the tick's existing error path stamps
them onto the row.

## Scheduler flow (per 15-min tick)

Unchanged except dispatch: step 4 routes through the platform registry
(`youtube-shorts` → youtube_client.post, `ig-reels` → instagram_client.post) instead of
Postiz. The stuck-Posting sweep (>1h by last_edited_time), per-platform Posted Links
idempotency, crash-path summary printing, and dry-run behavior are all as built and
reviewed. The local stamp file is dropped (ephemeral runners) — tick liveness is checked
via the GitHub API instead.

## Error handling & monitoring

- **Row-level failure** → `Failed` + `Error` field (unchanged), surfaced by the hourly
  watchdog: any failed tick run in the last 90 minutes (drift margin) → SMS. Failure-to-SMS latency ≤ ~1h.
- **Service-level failure** (workflow not running at all) → watchdog's no-recent-run
  check → SMS.
- **Watchdog-level failure** → monthly heartbeat SMS on the 1st proves the channel.
- **Token expiry**: IG auto-refresh monthly via workflow; the watchdog also checks that
  workflow's runs. YouTube refresh tokens don't expire in production-status apps.

## Testing

Unchanged: full TDD suite (mocked platform APIs), `--dry-run` flag, first post per
platform supervised live before its channel runs unattended.

## Public-repo hygiene

- NO tokens/credentials committed — everything lives in GitHub Actions secrets (and the
  Notion token additionally in Zo env for the watchdog). Gitleaks hook + push protection
  active.
- Notion DB IDs, channel handles, IG user id in config are OK (not secrets).
- README follows the 8-section protocol and carries the socket contract.

## Human items (only Ted can do)

1. Google Cloud project + YouTube Data API OAuth credentials for `@Useful_Math`; run the
   one-time consent flow to mint the refresh token; set the OAuth app to **production**
   status. (SLOWEST item — start early.)
2. ~~Meta app for IG Graph API: mint a long-lived token + IG user id.~~ **DONE — nothing
   to mint**: useful-math's existing May-2026 Meta app and its live long-lived token
   (`@useful_math_`) got reused. The token is from the "Instagram API with Instagram
   Login" family (`graph.instagram.com`, refreshed via `ig_refresh_token`).
3. Create a fine-grained GitHub PAT (this repo, secrets:write) as `ADMIN_PAT` so the
   monthly workflow can rotate the IG token secret.
4. Create the Notion integration "cross-platform-poster" + share the Post Queue parent
   page with it; token into GH secrets AND Zo env.
5. Set the GitHub repo secrets/vars listed in `.env.example`.

## Decisions log

| Decision | Choice |
|---|---|
| Standalone vs embedded per-project | Standalone repo + copied adapters (Alexandria pattern) |
| Handoff contract | Central Notion Post Queue DB owned by this project |
| Approval gate | Per-project, owned by the adapter (`auto`/`gated`); UM = `auto` |
| Publish timing | Per-channel slots + optional `days:` weekday filter; UM Sun/Tue/Thu 00:00 ET; GH-cron jitter slot-skip accepted |
| v1 consumer/platforms | Useful Math → YouTube Shorts + IG Reels |
| UM integration | Watcher adapter on the 3B final-video folder; `<person-slug>.mp4` naming contract |
| Name / visibility | `cross-platform-poster`, public |
| ~~Posting engine: self-hosted Postiz on Zo~~ | **SUPERSEDED 2026-07-13** — Zo kernel blocks all containers (verified); current Postiz also requires a Temporal stack |
| Posting engine (revised) | Direct platform API clients (YouTube Data API, IG Graph API), $0/mo |
| Scheduler host (revised) | GitHub Actions cron (15-min, free public repo); Zo hosts the hourly watchdog |
| Alerting | SMS logic stays out of the Action; Zo watchdog checks run status via GitHub API (useful-math pattern) |
