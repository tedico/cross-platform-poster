"""Load and validate channels.yaml — which platforms each project posts to.
Scheduling lives on each row's "Publish Date & Time" (Notion), not here.
Gate (auto/gated) deliberately does NOT live here; adapters own it."""
import yaml


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
        if "platforms" not in pcfg:
            raise ConfigError(f"{project}: missing 'platforms'")
        platforms = pcfg["platforms"]
        if not isinstance(platforms, list) or not platforms:
            raise ConfigError(
                f"{project}: 'platforms' must be a non-empty list of platform names")
        for platform in platforms:
            if not isinstance(platform, str):
                raise ConfigError(
                    f"{project}: bad platform '{platform}' (must be a string)")
    return cfg
