"""Load and validate channels.yaml — the single place a project is defined:
its Notion "Project" value, its platforms, its caption cap, and the names of
the env vars holding its platform credentials. Adding a project is a config
change plus secrets; no code edit.

Scheduling lives on each row's "Publish Date & Time" (Notion), not here.
Gate (auto/gated) deliberately does NOT live here; adapters own it.
"""
import yaml

# Instagram's own hard cap. A project may set a LOWER editorial limit, never a
# higher one — the platform rejects the post, so a bigger number is a lie.
PLATFORM_CAPTION_CEILING = 2200
DEFAULT_CAPTION_LIMIT = PLATFORM_CAPTION_CEILING

IG_PLATFORMS = ("ig-reels", "ig-carousel")
IG_CREDENTIAL_KEYS = ("ig_user_id_env", "ig_access_token_env")


class ConfigError(Exception):
    pass


def _validate_ig_credentials(project, pcfg, claimed):
    """Every IG project NAMES its own credential env vars.

    Nothing is derived from the project name and nothing falls back to a
    shared default: the failure that guards against is publishing one brand's
    post to another brand's account, which is public and not undoable. Naming
    the vars also makes the GitHub-secrets checklist self-documenting.
    """
    if not any(p in IG_PLATFORMS for p in pcfg["platforms"]):
        return
    for key in IG_CREDENTIAL_KEYS:
        name = pcfg.get(key)
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(
                f"{project}: posts to Instagram, so '{key}' is required and "
                f"must name an env var (e.g. IG_USER_ID_{project.upper()})")
        owner = claimed.setdefault(name, project)
        if owner != project:
            raise ConfigError(
                f"{project}: '{key}' is {name}, already used by '{owner}' — "
                f"two projects sharing Instagram credentials would post one "
                f"brand's content to the other's account")


def load_channels(path) -> dict:
    with open(path) as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ConfigError("channels.yaml must be a mapping of project -> config")
    claimed, notion_names = {}, {}
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

        # The Notion "Project" select value. Explicit, never derived from the
        # slug — a casing mismatch would silently match zero queue rows.
        notion_project = pcfg.get("notion_project")
        if not isinstance(notion_project, str) or not notion_project.strip():
            raise ConfigError(
                f"{project}: 'notion_project' is required — the exact Post "
                f"Queue 'Project' value this config posts for")
        owner = notion_names.setdefault(notion_project, project)
        if owner != project:
            raise ConfigError(
                f"{project}: 'notion_project' {notion_project!r} is already "
                f"claimed by '{owner}'")

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

        _validate_ig_credentials(project, pcfg, claimed)
    return cfg


def project_names(cfg: dict) -> dict:
    """slug -> Notion 'Project' select value, straight from the config."""
    return {slug: pcfg["notion_project"] for slug, pcfg in cfg.items()}
