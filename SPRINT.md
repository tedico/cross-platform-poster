# Sprint Plan — cross-platform-poster

## Phases
- [x] Phase 1 — Core engine: config, slots, queue client, tick orchestrator, adapter file, all TDD (done 2026-07-13; 53 tests)
- [x] Phase 2 — Platform clients + GH workflows + watchdog rework (code done 2026-07-13, 60 tests); live wiring pending Human items
- [ ] Phase 3 — First supervised posts: YouTube Short + IG Reel land on the real channels, then unattended
- [ ] Phase 4 — Second consumer plugs in (Super Psychology or Athena) — proves the outlet

## Current phase
Phase 2 — Platform clients + live wiring

**PIVOT 2026-07-13:** Postiz dropped — Zo's kernel blocks all containers (verified), and
current Postiz needs a Temporal stack. New engine: direct YouTube Data API + IG Graph API
clients; tick runs on GitHub Actions cron ($0/mo); watchdog on Zo reads the workflow's
run status via GitHub API (useful-math pattern). Spec + plan updated (see Pivot sections).

## Next
Merge day-of-week-slots PR (Sun/Tue/Thu 00:00 ET schedule — AutoShorts cadence parity). Ted: Human items below (YouTube creds = long pole). Then: dispatch tick dry-run, create Post Queue DB, first supervised posts (Phase 3).

## Human
- Google Cloud project + YouTube Data API OAuth creds for @Useful_Math; run scripts/get_youtube_token.py once for the refresh token; set the OAuth app to PRODUCTION status (else refresh tokens die in 7 days). SLOWEST item — start now
- ~~IG credentials~~ DONE: useful-math's May-2026 Meta app + live long-lived token reused (Instagram-Login family, graph.instagram.com); IG_USER_ID + IG_ACCESS_TOKEN secrets are set — nothing to mint
- Create fine-grained GitHub PAT (this repo, secrets:write) as ADMIN_PAT secret — lets the monthly workflow rotate the IG token
- Create Notion integration "cross-platform-poster", share the Post Queue parent page with it; token into GH secrets AND Zo env
- Set remaining GH repo secrets: NOTION_TOKEN, POST_QUEUE_DB_ID, YT_CLIENT_ID/SECRET/REFRESH_TOKEN, ADMIN_PAT, ASSET_STORE_TOKEN (IG_USER_ID + IG_ACCESS_TOKEN already set)
- `cd ~/cross-platform-poster && git push origin main` (bootstrap commit still local — pre-commit hook blocks Claude from pushing main)
- After merge: manually dispatch Refresh IG Token once to confirm the ig_refresh_token rotation end-to-end (script matches useful-math's proven monthly flow)
- Zo watchdog automation: hourly at :30 (needs repo clone + venv + .env on Zo — Claude can do the Zo setup, the automation creation needs your ok)

## Blockers
none
