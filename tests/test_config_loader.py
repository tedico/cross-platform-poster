import pytest
from src.config_loader import load_channels, ConfigError


def _write(tmp_path, text):
    p = tmp_path / "channels.yaml"
    p.write_text(text)
    return p


def test_loads_valid_config(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms: [youtube-shorts, ig-reels]\n"
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
