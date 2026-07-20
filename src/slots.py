"""Which project+platform slots are due at this tick?

The scheduler ticks every ~15 minutes. We quantize the tick time DOWN to the
15-minute grid and compare against each slot's HH:MM in ITS OWN timezone, so a
slot fires exactly once per day regardless of cron jitter. An optional 'days'
list restricts a slot to those weekdays, evaluated in the slot's own timezone —
a midnight-ET Sunday slot is Sunday IN ET, regardless of the UTC date."""
from datetime import datetime
from zoneinfo import ZoneInfo


def due_slots(cfg: dict, now: datetime) -> list[tuple[str, str]]:
    if now.tzinfo is None:
        raise ValueError("due_slots requires an aware datetime")
    due = []
    for project, pcfg in cfg.items():
        for platform, s in pcfg["platforms"].items():
            local = now.astimezone(ZoneInfo(s["tz"]))
            quantized = local.replace(minute=(local.minute // 15) * 15,
                                      second=0, microsecond=0)
            if quantized.strftime("%H:%M") != s["slot"]:
                continue
            if "days" in s and local.strftime("%a").lower() not in s["days"]:
                continue
            due.append((project, platform))
    return due
