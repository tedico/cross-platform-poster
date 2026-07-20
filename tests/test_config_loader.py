import pytest
from src.config_loader import load_channels, ConfigError


def _write(tmp_path, text):
    p = tmp_path / "channels.yaml"
    p.write_text(text)
    return p


def test_loads_valid_config(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:00\", tz: \"America/New_York\", cadence: daily }\n"
    ))
    cfg = load_channels(p)
    assert cfg["useful-math"]["platforms"]["youtube-shorts"]["slot"] == "12:00"


def test_rejects_unquantized_slot(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:10\", tz: \"America/New_York\", cadence: daily }\n"
    ))
    with pytest.raises(ConfigError, match="12:10"):
        load_channels(p)


def test_rejects_bad_timezone(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:00\", tz: \"America/Nowhere\", cadence: daily }\n"
    ))
    with pytest.raises(ConfigError, match="Nowhere"):
        load_channels(p)


def test_rejects_unquoted_slot_yaml_sexagesimal(tmp_path):
    # YAML 1.1 parses unquoted 12:00 as the integer 720
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: 12:00, tz: \"America/New_York\", cadence: daily }\n"
    ))
    with pytest.raises(ConfigError, match="slot"):
        load_channels(p)


def test_rejects_non_zero_padded_slot(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"9:00\", tz: \"America/New_York\", cadence: daily }\n"
    ))
    with pytest.raises(ConfigError, match="zero-padded"):
        load_channels(p)


def test_rejects_unknown_cadence(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"12:00\", tz: \"America/New_York\", cadence: hourly }\n"
    ))
    with pytest.raises(ConfigError, match="cadence"):
        load_channels(p)


def test_accepts_valid_days_list(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"00:00\", tz: \"America/New_York\", cadence: daily, days: [sun, tue, thu] }\n"
    ))
    cfg = load_channels(p)
    assert cfg["useful-math"]["platforms"]["youtube-shorts"]["days"] == ["sun", "tue", "thu"]


def test_rejects_bad_day_name(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"00:00\", tz: \"America/New_York\", cadence: daily, days: [monday] }\n"
    ))
    with pytest.raises(ConfigError, match="bad day 'monday'"):
        load_channels(p)


def test_rejects_empty_days_list(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"00:00\", tz: \"America/New_York\", cadence: daily, days: [] }\n"
    ))
    with pytest.raises(ConfigError, match="non-empty"):
        load_channels(p)


def test_rejects_duplicate_days(tmp_path):
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"00:00\", tz: \"America/New_York\", cadence: daily, days: [sun, sun] }\n"
    ))
    with pytest.raises(ConfigError, match="duplicate"):
        load_channels(p)


def test_rejects_non_string_day_yaml_boolean(tmp_path):
    # YAML 1.1 parses bare `on` as the boolean True — must fail loud, not slip through
    p = _write(tmp_path, (
        "useful-math:\n"
        "  platforms:\n"
        "    youtube-shorts: { slot: \"00:00\", tz: \"America/New_York\", cadence: daily, days: [on] }\n"
    ))
    with pytest.raises(ConfigError, match="bad day 'True'"):
        load_channels(p)
