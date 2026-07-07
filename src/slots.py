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
