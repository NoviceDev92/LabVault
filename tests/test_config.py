"""Tests for core/config.py — YAML configuration system."""

import os
from pathlib import Path

from labvault.core.config import (
    load_config,
    save_config,
    get_config_value,
    set_config_value,
    _auto_cast,
    _deep_merge,
)


def test_load_defaults(tmp_path, monkeypatch):
    """Loading config with no file returns defaults."""
    monkeypatch.setenv("LABVAULT_CONFIG_DIR", str(tmp_path))
    cfg = load_config()
    assert cfg["ui"]["port"] == 5555
    assert cfg["ui"]["theme"] == "dark"
    assert cfg["default_project"] is None


def test_save_and_load(tmp_path, monkeypatch):
    """Saving a config then loading it should return the same values."""
    monkeypatch.setenv("LABVAULT_CONFIG_DIR", str(tmp_path))
    cfg = {"ui": {"port": 8080, "theme": "light"}, "default_project": "my-proj"}
    save_config(cfg)

    loaded = load_config()
    assert loaded["ui"]["port"] == 8080
    assert loaded["ui"]["theme"] == "light"
    assert loaded["default_project"] == "my-proj"


def test_get_config_value_dotted(tmp_path, monkeypatch):
    """Dotted-path access for nested keys."""
    monkeypatch.setenv("LABVAULT_CONFIG_DIR", str(tmp_path))
    assert get_config_value("ui.port") == 5555
    assert get_config_value("ui.theme") == "dark"
    assert get_config_value("nonexistent.key") is None


def test_set_config_value(tmp_path, monkeypatch):
    """Setting a dotted-path value persists it."""
    monkeypatch.setenv("LABVAULT_CONFIG_DIR", str(tmp_path))
    set_config_value("ui.port", "9090")
    assert get_config_value("ui.port") == 9090  # auto-cast to int


def test_set_creates_nested_keys(tmp_path, monkeypatch):
    """Setting a deeply nested key auto-creates intermediate dicts."""
    monkeypatch.setenv("LABVAULT_CONFIG_DIR", str(tmp_path))
    set_config_value("export.latex.font_size", "12")
    assert get_config_value("export.latex.font_size") == 12


def test_auto_cast():
    """Verify string-to-type auto-casting."""
    assert _auto_cast("true") is True
    assert _auto_cast("false") is False
    assert _auto_cast("none") is None
    assert _auto_cast("42") == 42
    assert _auto_cast("3.14") == 3.14
    assert _auto_cast("hello") == "hello"


def test_deep_merge():
    """Verify recursive dict merging."""
    base = {"a": 1, "nested": {"x": 10, "y": 20}}
    override = {"nested": {"y": 99, "z": 30}, "b": 2}
    _deep_merge(base, override)
    assert base == {"a": 1, "nested": {"x": 10, "y": 99, "z": 30}, "b": 2}
