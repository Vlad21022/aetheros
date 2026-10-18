"""Settings come from the environment, an uncommitted .env and a local TOML file."""

from pathlib import Path

import pytest

from aether_hub import config

EXAMPLE = Path(__file__).parent.parent / "aether.example.toml"
HA = {"AETHER_HA_URL": "http://ha.local:8123", "AETHER_HA_TOKEN": "secret-token"}


def write(directory: Path, name: str, text: str) -> None:
    (directory / name).write_text(text, encoding="utf-8")


def test_no_home_assistant_means_demo(tmp_path):
    settings = config.load({}, tmp_path)
    assert settings.home_assistant is None


def test_dotenv_is_loaded(tmp_path):
    write(tmp_path, ".env", '# comment\n\nexport AETHER_HA_URL="http://ha.local:8123"\nAETHER_HA_TOKEN = abc=def\n')
    write(tmp_path, "aether.toml", "")
    settings = config.load({}, tmp_path)
    assert settings.home_assistant.url == "http://ha.local:8123"
    assert settings.home_assistant.token.get_secret_value() == "abc=def"


def test_environment_wins_over_dotenv(tmp_path):
    write(tmp_path, ".env", "AETHER_HA_URL=http://from-file:8123\nAETHER_HA_TOKEN=from-file\n")
    write(tmp_path, "aether.toml", "")
    settings = config.load({"AETHER_HA_TOKEN": "from-env"}, tmp_path)
    assert settings.home_assistant.url == "http://from-file:8123"
    assert settings.home_assistant.token.get_secret_value() == "from-env"


def test_bad_dotenv_line_names_the_line(tmp_path):
    write(tmp_path, ".env", "AETHER_HA_URL=http://ha.local:8123\nnot a setting\n")
    with pytest.raises(config.ConfigError, match=r"\.env:2"):
        config.load({}, tmp_path)


def test_token_never_shows_in_repr(tmp_path):
    write(tmp_path, "aether.toml", "")
    settings = config.load(HA, tmp_path)
    assert "secret-token" not in repr(settings)
    assert "secret-token" not in str(settings.home_assistant)
    assert "secret-token" not in settings.model_dump_json()


@pytest.mark.parametrize("present", ["AETHER_HA_URL", "AETHER_HA_TOKEN"])
def test_url_and_token_go_together(tmp_path, present):
    with pytest.raises(config.ConfigError, match="is not set"):
        config.load({present: HA[present]}, tmp_path)


def test_url_must_be_a_url(tmp_path):
    with pytest.raises(config.ConfigError, match="AETHER_HA_URL"):
        config.load({**HA, "AETHER_HA_URL": "ha.local"}, tmp_path)


def test_missing_entities_file_says_what_to_do(tmp_path):
    with pytest.raises(config.ConfigError, match="aether.example.toml"):
        config.load(HA, tmp_path)


def test_entities_file_path_can_be_set(tmp_path):
    write(tmp_path, "home.toml", '[sections]\nweather = "weather.home"\n')
    settings = config.load({**HA, "AETHER_CONFIG": "home.toml"}, tmp_path)
    assert settings.entities.sections.weather == "weather.home"


def test_invalid_toml_is_a_clear_error(tmp_path):
    write(tmp_path, "aether.toml", "[home\n")
    with pytest.raises(config.ConfigError, match="aether.toml"):
        config.load(HA, tmp_path)


@pytest.mark.parametrize(
    "text",
    [
        '[home]\ntiles = [{ entity = "not an entity" }]\n',
        '[home]\ntiles = [{ entity = "light.office", kind = "toaster" }]\n',
        '[sections]\nradio = "media_player.kitchen"\n',
    ],
)
def test_invalid_entities_name_the_field(tmp_path, text):
    write(tmp_path, "aether.toml", text)
    with pytest.raises(config.ConfigError, match=r"aether\.toml: (home|sections)\."):
        config.load(HA, tmp_path)


def test_the_example_file_is_valid():
    entities = config.load_entities(EXAMPLE)
    assert [tile.entity for tile in entities.home.tiles] == [
        "light.living_room",
        "lock.front_door",
        "sensor.living_room_temperature",
    ]
    assert entities.sections.calendar == "calendar.personal"


def test_data_dir_and_host(tmp_path):
    settings = config.load({}, tmp_path)
    assert settings.data_dir == tmp_path / "data"
    assert settings.host == "0.0.0.0"
    settings = config.load({"AETHER_DATA": "/var/lib/aether", "AETHER_HUB_HOST": "192.168.1.20"}, tmp_path)
    assert str(settings.data_dir) == "/var/lib/aether"
    assert settings.host == "192.168.1.20"
