import pytest
from src.config_loader import ConfigError, load_channels, project_names


def _write(tmp_path, text):
    p = tmp_path / "channels.yaml"
    p.write_text(text)
    return p


def test_loads_valid_config(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        '  notion_project: "Useful Math"\n'
        "  platforms: [youtube-shorts, ig-reels]\n"
        "  ig_user_id_env: IG_USER_ID\n"
        "  ig_access_token_env: IG_ACCESS_TOKEN\n"
    ))
    cfg = load_channels(p)
    assert cfg["useful-math"]["platforms"] == ["youtube-shorts", "ig-reels"]


def test_rejects_non_mapping_top_level(tmp_path):
    p = _write(tmp_path, "- useful-math\n")
    with pytest.raises(ConfigError, match="mapping of project"):
        load_channels(p)


def test_rejects_missing_platforms(tmp_path):
    p = _write(tmp_path, "useful-math: {}\n")
    with pytest.raises(ConfigError, match="missing 'platforms'"):
        load_channels(p)


def test_rejects_empty_platforms(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms: []\n"
    ))
    with pytest.raises(ConfigError, match="non-empty list"):
        load_channels(p)


def test_rejects_non_list_platforms_old_slot_schema(tmp_path):
    # The pre-2026-07-20 slot schema (platforms as a mapping) must fail loud.
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:00\", tz: \"America/New_York\", cadence: daily }\n"
    ))
    with pytest.raises(ConfigError, match="non-empty list"):
        load_channels(p)


def test_rejects_non_string_platform(tmp_path):
    # YAML 1.1 parses bare `on` as the boolean True — must fail loud.
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms: [youtube-shorts, on]\n"
    ))
    with pytest.raises(ConfigError, match="bad platform 'True'"):
        load_channels(p)


# --- caption_limit ----------------------------------------------------------

def _write(tmp_path, body):
    p = tmp_path / "channels.yaml"
    p.write_text(body)
    return p


def test_caption_limit_defaults_to_instagrams_ceiling(tmp_path):
    cfg = load_channels(_write(tmp_path, "athena:\n  notion_project: Athena\n  platforms: [youtube-shorts]\n"))
    assert cfg["athena"]["caption_limit"] == 2200


def test_caption_limit_is_read_per_project(tmp_path):
    cfg = load_channels(_write(tmp_path,
        "useful-math:\n  notion_project: UM\n  platforms: [youtube-shorts]\n  caption_limit: 2000\n"
        "athena:\n  notion_project: Athena\n  platforms: [youtube-shorts]\n  caption_limit: 2200\n"))
    assert cfg["useful-math"]["caption_limit"] == 2000
    assert cfg["athena"]["caption_limit"] == 2200


def test_caption_limit_above_instagrams_hard_cap_is_rejected(tmp_path):
    """A limit over 2200 is a lie — the platform rejects the post."""
    with pytest.raises(ConfigError, match="2200"):
        load_channels(_write(tmp_path,
            "athena:\n  notion_project: Athena\n  platforms: [youtube-shorts]\n  caption_limit: 5000\n"))


@pytest.mark.parametrize("bad", ["'2000'", "0", "-1", "true", "2.5"])
def test_caption_limit_must_be_a_positive_int(tmp_path, bad):
    with pytest.raises(ConfigError, match="positive integer"):
        load_channels(_write(tmp_path,
            f"athena:\n  notion_project: Athena\n  platforms: [youtube-shorts]\n  caption_limit: {bad}\n"))


# --- per-project identity and credentials ----------------------------------

IG_OK = ("athena:\n"
         "  notion_project: Athena\n"
         "  platforms: [ig-carousel]\n"
         "  ig_user_id_env: IG_USER_ID_ATHENA\n"
         "  ig_access_token_env: IG_ACCESS_TOKEN_ATHENA\n")


def test_notion_project_is_required(tmp_path):
    """Derived-from-slug casing would silently match zero queue rows."""
    with pytest.raises(ConfigError, match="notion_project"):
        load_channels(_write(tmp_path,
                             "athena:\n  platforms: [youtube-shorts]\n"))


def test_project_names_maps_slug_to_notion_value(tmp_path):
    cfg = load_channels(_write(tmp_path, IG_OK))
    assert project_names(cfg) == {"athena": "Athena"}


def test_ig_project_must_name_its_credential_env_vars(tmp_path):
    with pytest.raises(ConfigError, match="ig_user_id_env"):
        load_channels(_write(tmp_path,
            "athena:\n  notion_project: Athena\n  platforms: [ig-carousel]\n"))


def test_non_ig_project_needs_no_ig_credentials(tmp_path):
    cfg = load_channels(_write(tmp_path,
        "um:\n  notion_project: UM\n  platforms: [youtube-shorts]\n"))
    assert cfg["um"]["platforms"] == ["youtube-shorts"]


def test_two_projects_may_not_share_instagram_credentials(tmp_path):
    """The whole hazard in one rule: shared creds = cross-brand posting."""
    with pytest.raises(ConfigError, match="already used by"):
        load_channels(_write(tmp_path, IG_OK +
            "other:\n"
            "  notion_project: Other\n"
            "  platforms: [ig-reels]\n"
            "  ig_user_id_env: IG_USER_ID_ATHENA\n"
            "  ig_access_token_env: IG_ACCESS_TOKEN_OTHER\n"))


def test_two_projects_may_not_claim_the_same_notion_project(tmp_path):
    with pytest.raises(ConfigError, match="already claimed"):
        load_channels(_write(tmp_path,
            "a:\n  notion_project: Athena\n  platforms: [youtube-shorts]\n"
            "b:\n  notion_project: Athena\n  platforms: [youtube-shorts]\n"))


def test_the_real_channels_yaml_is_valid():
    """Guards the file that actually ships."""
    cfg = load_channels("channels.yaml")
    assert set(cfg) == {"useful-math", "athena"}
    assert cfg["athena"]["ig_user_id_env"] == "IG_USER_ID_ATHENA"
    assert cfg["useful-math"]["ig_user_id_env"] == "IG_USER_ID"
