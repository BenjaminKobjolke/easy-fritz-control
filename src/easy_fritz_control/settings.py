"""Loads and validates boxes.json (path overridable via the EASY_FRITZ_CONFIG env var)."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from easy_fritz_control.constants import (
    CONFIG_ENV_VAR,
    DEFAULT_BLACKLIST_FILE,
    DEFAULT_CONFIG_FILE,
    DEFAULT_LOG_LEVEL,
)

_URL_SCHEMES = ("http://", "https://")


class ConfigError(Exception):
    """boxes.json is missing or invalid."""


class FritzBoxConfig(BaseModel):
    """Connection data of one FRITZ!Box."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    url: str
    username: str = ""
    password: SecretStr

    @field_validator("url")
    @classmethod
    def _url_has_scheme(cls, value: str) -> str:
        if not value.startswith(_URL_SCHEMES):
            raise ValueError("must start with http:// or https://")
        return value.rstrip("/")


class AppConfig(BaseModel):
    """All settings of the tool."""

    model_config = ConfigDict(frozen=True)

    boxes: list[FritzBoxConfig] = Field(min_length=1)
    blacklist_file: Path = Path(DEFAULT_BLACKLIST_FILE)
    log_level: str = DEFAULT_LOG_LEVEL

    @field_validator("boxes")
    @classmethod
    def _unique_names(cls, boxes: list[FritzBoxConfig]) -> list[FritzBoxConfig]:
        names = [box.name for box in boxes]
        if len(names) != len(set(names)):
            raise ValueError("box names must be unique")
        return boxes

    def select_boxes(self, name: str | None) -> list[FritzBoxConfig]:
        """All boxes, or only the one with the given name."""
        if name is None:
            return list(self.boxes)
        selected = [box for box in self.boxes if box.name == name]
        if not selected:
            raise ConfigError(f"unknown box '{name}'")
        return selected


def default_config_path() -> Path:
    return Path(os.getenv(CONFIG_ENV_VAR, DEFAULT_CONFIG_FILE))


def load_config(path: Path) -> AppConfig:
    """Read the config; a relative blacklist_file is resolved next to the config file."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ConfigError(f"config file not found: {path} (copy boxes.example.json)") from error
    try:
        config = AppConfig.model_validate_json(raw)
    except ValidationError as error:
        raise ConfigError(f"invalid {path}: {error}") from error
    return config.model_copy(update={"blacklist_file": path.parent / config.blacklist_file})
