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
