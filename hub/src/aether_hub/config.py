"""Hub settings: where Home Assistant is and which entities the screens show.

Secrets come from the environment, or from an uncommitted `.env` next to where the
hub is started; the environment wins. The entities come from a local TOML file
(`aether.toml`, or the path in AETHER_CONFIG). See docs/decisions.md, 018.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from .protocol import TileKind

ENV_HA_URL = "AETHER_HA_URL"
ENV_HA_TOKEN = "AETHER_HA_TOKEN"
ENV_CONFIG = "AETHER_CONFIG"
ENV_DATA = "AETHER_DATA"
ENV_HOST = "AETHER_HUB_HOST"

DEFAULT_CONFIG = "aether.toml"
DEFAULT_DATA = "data"
DEFAULT_HOST = "0.0.0.0"
DOTENV = ".env"

_ENTITY_ID = r"^[a-z0-9_]+\.[a-z0-9_]+$"


class ConfigError(ValueError):
    """The settings are missing or wrong. The message says what to fix."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TileConfig(_Model):
    entity: str = Field(pattern=_ENTITY_ID, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=60)
    kind: TileKind | None = None


class HomeConfig(_Model):
    tiles: tuple[TileConfig, ...] = Field(default=(), max_length=24)


class SectionsConfig(_Model):
    weather: str | None = Field(default=None, pattern=_ENTITY_ID)
    now_playing: str | None = Field(default=None, pattern=_ENTITY_ID)
    calendar: str | None = Field(default=None, pattern=_ENTITY_ID)


class Entities(_Model):
    home: HomeConfig = HomeConfig()
    sections: SectionsConfig = SectionsConfig()


class HomeAssistantConfig(_Model):
    url: str = Field(pattern=r"^(http|https|ws|wss)://\S+$")
    token: SecretStr


class Settings(_Model):
    home_assistant: HomeAssistantConfig | None = None
    """None runs the hub on demo data."""
    entities: Entities = Entities()
    data_dir: Path = Path(DEFAULT_DATA)
    """The hub's own files: its TLS certificate, the paired screens, the admin socket."""
    host: str = DEFAULT_HOST


def load_dotenv(path: Path, environ: MutableMapping[str, str]) -> None:
    """Adds KEY=VALUE lines from `path` to `environ`. Values already set are kept."""
    if not path.is_file():
        return
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.removeprefix("export ").partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not key or " " in key:
            raise ConfigError(f"{path}:{number}: expected KEY=VALUE")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        environ.setdefault(key, value)


def load_entities(path: Path) -> Entities:
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except FileNotFoundError:
        raise ConfigError(f"{path} not found. Copy aether.example.toml and list your entities.") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from None
    try:
        return Entities.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        raise ConfigError(f"{path}: {where}: {first['msg']}") from None


def load(environ: Mapping[str, str] | None = None, directory: Path | None = None) -> Settings:
    """Reads `.env`, the environment and the entities file. Demo settings when no Home Assistant is set."""
    directory = directory or Path.cwd()
    env = dict(os.environ if environ is None else environ)
    load_dotenv(directory / DOTENV, env)

    local = {
        "data_dir": directory / env.get(ENV_DATA, DEFAULT_DATA),
        "host": env.get(ENV_HOST, DEFAULT_HOST).strip() or DEFAULT_HOST,
    }
    url = env.get(ENV_HA_URL, "").strip()
    token = env.get(ENV_HA_TOKEN, "").strip()
    if not url and not token:
        return Settings(**local)
    if not url or not token:
        missing = ENV_HA_TOKEN if url else ENV_HA_URL
        raise ConfigError(f"{missing} is not set. Set both {ENV_HA_URL} and {ENV_HA_TOKEN}, or neither for demo data.")

    try:
        home_assistant = HomeAssistantConfig(url=url, token=SecretStr(token))
    except ValidationError:
        raise ConfigError(f"{ENV_HA_URL} must look like http://homeassistant.local:8123") from None
    entities = load_entities(directory / env.get(ENV_CONFIG, DEFAULT_CONFIG))
    return Settings(home_assistant=home_assistant, entities=entities, **local)
