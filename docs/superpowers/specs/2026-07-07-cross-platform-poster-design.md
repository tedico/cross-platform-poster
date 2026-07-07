# cross-platform-poster — Design Spec

**Date:** 2026-07-07
**Status:** Approved design, pre-implementation
**Repo:** `tedico/cross-platform-poster` (public, to be created at implementation start)

## What / Why

A standalone "power outlet" posting service: any of Ted's content projects (the appliances)
can plug a finished asset into it, and it publishes that asset to the right social platforms
on a steady schedule. Projects never carry platform credentials or upload code; the outlet
never knows how an asset was produced.

Built because every pipeline (Useful Math, Super Psychology, Athena, KontentMaschine, future
carousel engines) ends at the same wall: "asset is done, now post it." Posting is
infrastructure, like Alexandria — one shared service, thin copied adapters, never embedded
per-project.

## Goals

- One central queue where every queued/posted asset across all projects is visible.
- Per-project approval gate: a project is either `auto` (rows post without review) or
  `gated` (Ted flips a status in Notion before anything goes live).
- Per-channel publish slots: bursts of production become a steady drip (e.g. one post/day
  per platform).
- Adding a platform is config + a Postiz connection, not new upload code.
- No silent failures — SMS on every failure, watchdog on the service itself.

## Non-goals

- Producing or editing assets (that's the projects' job).
- Analytics/engagement tracking (Postiz has some; not part of v1).
- Caption generation (arrives with the asset; producers already generate title/desc).
- Comment management, DMs, or anything interactive.

## v1 scope

**Consumer:** Useful Math only.
**Platforms:** YouTube Shorts (`@Useful_Math`) + Instagram Reels (`@useful_math_`) — the
same MP4 fans out to both, matching how the channels are run today (identical videos on
both platforms).
**Dependency:** finished MP4s come from Sprint 3B (Descript assembly) dropping files into a
final-video output folder. The poster can be built and dry-run tested before 3B ships; the
first live post uses a manually placed MP4.

Future consumers (schema-ready, not wired in v1): Super Psychology (IG Reels — 3 finished
MP4s already staged), Athena (IG carousel — `image-set` asset type exists in the schema for
this), LinkedIn/IG carousel engines, KontentMaschine.

## Architecture

```
[Useful Math]──watcher adapter──┐
[future projects]───adapters────┤→ Post Queue (Notion DB) → Scheduler (Zo automation, 15-min tick)
                                         ↑ Ted approves                 │
                                           gated rows                   ▼
                                                          Postiz (Docker on Zo) → YouTube / Instagram
                                                                         │
                                              results stamped back on the queue row (permalink / error)
```

Three components, one external appliance:

1. **Post Queue** — a Notion database owned by this project. The fixed schema IS the plug
   standard. All state lives here.
2. **Scheduler** — a small Zo automation (~200–300 lines). Deliberately dumb: reads config,
   reads the queue, talks to Postiz, stamps results.
3. **Adapters** — one canonical file in this repo that consumer projects COPY (Alexandria
   pattern, `Used By` stamping; engines-never-shared rule applies — no cross-repo imports).
4. **Postiz** (external appliance) — self-hosted via Docker on Zo. Owns platform OAuth,
   token refresh, YouTube upload, Instagram's container/publish flow. Never forked or
   modified; accessed only via its public API. AGPL-3.0 (fine — we consume its API, don't
   redistribute).

## Post Queue DB schema

| Field | Type | Notes |
|---|---|---|
| Title | title | Post title / first caption line |
| Project | select | `Useful Math`, later: `Super Psychology`, `Athena`, … |
| Asset URL(s) | text | One or more URLs the scheduler can download (newline-separated; um-assets store for UM) |
| Asset Type | select | `video`, `image-set` |
| Caption | text | Platform-ready caption incl. hashtags |
| Platforms | multi-select | `youtube-shorts`, `ig-reels`, `ig-carousel`, `linkedin`, … |
| Status | select | `Awaiting Approval` → `Ready` → `Posting` → `Posted` / `Failed` |
| Posted Links | text | Permalinks per platform, stamped by scheduler |
| Error | text | Failure detail, stamped by scheduler |
| Date Added | created time | Drives oldest-first draining |

Status semantics:
- `gated` projects' adapters create rows as `Awaiting Approval`; Ted flips to `Ready` in a
  "🙋 Awaiting Approval" Notion view (same human-gate pattern as Story Development's eval).
- `auto` projects' adapters create rows as `Ready` directly.
- One row can target multiple platforms, and their slots may fire at different times.
  Per-platform results are tracked inside `Posted Links` / `Error` (e.g.
  `youtube-shorts: <url>` / `ig-reels: FAILED — <reason>`). After each platform attempt:
  remaining platforms pending → row goes back to `Ready` (so later slots pick it up);
  all succeeded → `Posted`; any failed → `Failed`. Platforms already in `Posted Links`
  are never re-posted, so re-readying a failed row retries only what's left.

## Channel config — `channels.yaml`

Lives in the repo (changes rarely, only Ted edits it). Not a Notion DB.

```yaml
useful-math:
  platforms:
    youtube-shorts: { slot: "12:00", tz: "America/New_York", cadence: daily }
    ig-reels:       { slot: "12:00", tz: "America/New_York", cadence: daily }
```

`channels.yaml` owns ONLY slots. The approval gate (`auto` vs `gated`) is owned by each
project's copied adapter config — the gate matters only at row-creation time, and single
ownership avoids the two sources drifting. Useful Math = `auto` (Design-for-Automation:
UM never waits on Ted).

Slot behavior:
- Slots quantize to :00/:15/:30/:45 (scheduler ticks every 15 min).
- At a due slot, the scheduler publishes exactly ONE row per project+platform: the oldest
  `Ready` row targeting that platform. Empty queue → slot skips silently (not an error).
- Default UM slot 12:00 ET daily; tune freely in config later.

## Scheduler flow (per 15-min tick)

1. Load `channels.yaml`; find slots due this tick.
2. For each due project+platform: query Post Queue for the oldest `Ready` row targeting
   that platform and not already carrying it in `Posted Links`.
3. Set row `Posting`. Download asset(s) from Asset URL(s) to temp.
4. Call Postiz API: create post (file upload + caption + target integration + immediate
   publish). Poll until Postiz reports success/failure.
5. Success → append permalink to `Posted Links`; all platforms done → `Posted`, otherwise
   back to `Ready` for the remaining platforms' slots. Failure → `Failed` + `Error` + SMS.
6. A row `Posting` for > 1 hour (crashed mid-flight) is treated as failed: SMS + `Failed`,
   never auto-retried (Ted resets to `Ready` after checking the platform for a dupe).

Idempotency: platforms already listed in `Posted Links` are skipped, so re-readying a
partially-failed row retries only the failed platform.

## Useful Math watcher adapter (v1's one adapter)

A small Useful Math-side scheduled job (copied adapter + watcher wrapper, lives in the
useful-math repo per the copy-don't-import rule):

- Checks the final-video output folder (location decided in Sprint 3B; adapter takes it as
  config) on a schedule.
- Any NEW `.mp4` → look up its Video Production row for title/caption. **Filename
  convention (part of the 3B contract): `<person-slug>.mp4`**, matched against the VP row.
- Calls `enqueue()` → creates the queue row (`Ready`, since UM is `auto`), targeting
  `youtube-shorts` + `ig-reels`.
- Dedup: before enqueueing, query the Post Queue for an existing row with the same asset
  URL; skip if present. Works whether the file arrived from automated Descript assembly or
  Ted manually exporting from Descript.
- A new MP4 with NO matching VP row → SMS Ted, do not enqueue (never post uncaptioned).

Canonical adapter API (the file consumers copy):

```python
enqueue(project, title, asset_urls, caption, platforms)  # → creates the Notion row
```

The adapter reads the project's gate mode (`auto` → `Ready`, `gated` → `Awaiting
Approval`) from its own copied config — the adapter is the sole owner of the gate setting.

## Error handling & monitoring

Per the no-silent-failures standard:

- **Row-level failure** → `Failed` + `Error` field + SMS via Zo.
- **Service-level failure** (scheduler didn't tick, Postiz unreachable, Notion API down) →
  daily watchdog ("did the scheduler run in the last 24h? any stuck `Posting` rows?") that
  SMSes on anomaly, plus a monthly heartbeat SMS proving the watchdog itself is alive
  (same pattern as the useful-math watchdog).
- **Token expiry** (IG tokens ~60 days) surfaces as a row failure with a "reconnect
  account in Postiz" SMS — a known recurring Human chore.

## Testing

- Unit tests (mocked Notion + Postiz): slot math incl. timezone, oldest-first selection,
  status transitions, per-platform partial-failure/retry logic, config parsing, adapter
  enqueue + dedup, filename→VP-row matching.
- `--dry-run` flag: full flow except the final Postiz publish call (logs what WOULD post).
- Rollout gate: first post per platform is supervised live (Ted watches it land on the
  actual channel) before that channel's slot runs unattended.

## Public-repo hygiene

Repo is public. Rules:
- NO tokens/credentials ever committed — Notion integration token, Postiz API key, and all
  platform credentials live in Zo env vars + inside Postiz. (Global gitleaks hook + GitHub
  push protection already guard this.)
- Notion DB IDs and channel handles in config are OK (not secrets; useless without the
  integration token).
- README follows the 8-section protocol; SPRINT.md from build-briefing template.

## Human items (only Ted can do)

1. Create a Google Cloud project + YouTube Data API OAuth credentials for `@Useful_Math`
   (slowest external dependency — start early; API quota/approval can take time).
2. Create a Meta app; ensure `@useful_math_` is a Business/Creator account linked to a
   Facebook Page (Instagram API requirement).
3. Stand up Postiz on Zo happens in implementation, but CONNECTING both accounts inside
   Postiz (OAuth dances) is Ted's.
4. Create the Notion integration for the poster + share the Post Queue DB with it.
5. Recurring: re-auth Instagram in Postiz when tokens expire (~60 days, SMS-prompted).

## Decisions log

| Decision | Choice |
|---|---|
| Standalone vs embedded per-project | Standalone repo + copied adapters (Alexandria pattern) |
| Posting engine | Self-hosted Postiz on Zo (approach A) — not direct platform APIs, not embedded |
| Handoff contract | Central Notion Post Queue DB owned by this project |
| Approval gate | Per-project setting (`auto` / `gated`); Useful Math = `auto` |
| Publish timing | Per-channel scheduled slots; default UM 12:00 ET daily |
| v1 consumer/platforms | Useful Math → YouTube Shorts + IG Reels |
| UM integration | Watcher adapter on the 3B final-video folder (works for automated AND manual Descript exports) |
| Name / visibility | `cross-platform-poster`, public |
