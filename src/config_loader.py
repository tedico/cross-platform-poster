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
