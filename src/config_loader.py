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
        if not isinstance(pcfg, dict):
            raise ConfigError(f"{project}: config must be a mapping")
        platforms = pcfg.get("platforms")
        if not platforms:
            raise ConfigError(f"{project}: missing 'platforms'")
        if not isinstance(platforms, dict):
            raise ConfigError(f"{project}: 'platforms' must be a mapping")
        for platform, s in platforms.items():
            if not isinstance(s, dict):
                raise ConfigError(f"{project}/{platform}: settings must be a mapping")
            slot = s.get("slot", "")
            if not isinstance(slot, str):
                raise ConfigError(f"{project}/{platform}: bad slot '{slot}' (want HH:MM)")
            try:
                hh, mm = slot.split(":")
                hh, mm = int(hh), int(mm)
            except ValueError:
                raise ConfigError(
                    f"{project}/{platform}: bad slot '{slot}' (want HH:MM)") from None
            if not (0 <= hh <= 23) or mm not in VALID_MINUTES:
                raise ConfigError(
                    f"{project}/{platform}: slot '{slot}' must be HH:00/:15/:30/:45")
            tz = s.get("tz", "")
            try:
                ZoneInfo(tz)
            except Exception:
                raise ConfigError(
                    f"{project}/{platform}: unknown timezone '{tz}'") from None
            if s.get("cadence") not in VALID_CADENCES:
                raise ConfigError(
                    f"{project}/{platform}: cadence must be one of {sorted(VALID_CADENCES)}")
    return cfg
