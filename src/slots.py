"""Which project+platform slots are due at this tick?

We request a */15 cron, but GitHub Actions delivers scheduled runs roughly
hourly regardless — so a slot is due when the tick's LOCAL HOUR (in the slot's
own timezone) equals the slot's hour. The slot's minute is advisory only:
config still accepts ':00/:15/:30/:45' for backward compat, but the slot fires
on the first run within its hour. Combined with find_due_row's posted-platform
idempotency the same ROW can't double-post; two runs inside one hour could post
two DIFFERENT Ready rows back-to-back (accepted: observed GH cadence is
>=54 min between runs, and the queue drains oldest-first either way). An
optional 'days' list restricts a slot to those weekdays, evaluated in the
slot's own timezone — a midnight-ET Sunday slot is Sunday IN ET, regardless of
the UTC date."""
from datetime import datetime
from zoneinfo import ZoneInfo


def due_slots(cfg: dict, now: datetime) -> list[tuple[str, str]]:
    if now.tzinfo is None:
        raise ValueError("due_slots requires an aware datetime")
    due = []
    for project, pcfg in cfg.items():
        for platform, s in pcfg["platforms"].items():
            local = now.astimezone(ZoneInfo(s["tz"]))
            slot_hour = int(s["slot"][:2])  # canonical zero-padded "HH:MM"
            if local.hour != slot_hour:
                continue
            if "days" in s and local.strftime("%a").lower() not in s["days"]:
                continue
            due.append((project, platform))
    return due
