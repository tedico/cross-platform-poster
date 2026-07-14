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
Ted: Human items below (YouTube creds = long pole). Then: push main, open v1-build PR, merge, dispatch tick dry-run, create Post Queue DB, first supervised posts (Phase 3).

## Human
- Google Cloud project + YouTube Data API OAuth creds for @Useful_Math; run scripts/get_youtube_token.py once for the refresh token; set the OAuth app to PRODUCTION status (else refresh tokens die in 7 days). SLOWEST item — start now
- Check what survives from the May-2026 IG token work (useful-math get_instagram_token.py): existing Meta app? @useful_math_ Business/Creator + linked FB Page? Mint long-lived token + IG user id
- Create fine-grained GitHub PAT (this repo, secrets:write) as ADMIN_PAT secret — lets the monthly workflow rotate the IG token
- Create Notion integration "cross-platform-poster", share the Post Queue parent page with it; token into GH secrets AND Zo env
- Set GH repo secrets: NOTION_TOKEN, POST_QUEUE_DB_ID, YT_CLIENT_ID/SECRET/REFRESH_TOKEN, IG_USER_ID, IG_ACCESS_TOKEN, FB_APP_ID/SECRET, ADMIN_PAT, ASSET_STORE_TOKEN
- `cd ~/cross-platform-poster && git push origin main` (bootstrap commit still local — pre-commit hook blocks Claude from pushing main)
- After merge: manually dispatch Refresh IG Token once to verify the token-refresh flow matches how the IG token was minted
- Zo watchdog automation: hourly at :30 (needs repo clone + venv + .env on Zo — Claude can do the Zo setup, the automation creation needs your ok)

## Blockers
none
