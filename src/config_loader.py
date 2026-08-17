"""Load and validate channels.yaml — which platforms each project posts to.
Scheduling lives on each row's "Publish Date & Time" (Notion), not here.
Gate (auto/gated) deliberately does NOT live here; adapters own it."""
import yaml

# Instagram's own hard cap. A project may set a LOWER editorial limit, never a
# higher one — the platform rejects the post, so a bigger number is a lie.
PLATFORM_CAPTION_CEILING = 2200
DEFAULT_CAPTION_LIMIT = PLATFORM_CAPTION_CEILING


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
        limit = pcfg.setdefault("caption_limit", DEFAULT_CAPTION_LIMIT)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ConfigError(
                f"{project}: 'caption_limit' must be a positive integer, "
                f"got {limit!r}")
        if limit > PLATFORM_CAPTION_CEILING:
            raise ConfigError(
                f"{project}: 'caption_limit' {limit} exceeds Instagram's hard "
                f"limit of {PLATFORM_CAPTION_CEILING} — the platform would "
                f"reject the post")
    return cfg
