"""Centralized YAML configuration system for LabVault.

Config file is stored at ~/.labvault/config.yaml and provides
vault-wide defaults for CLI and UI preferences.
"""

import os
from pathlib import Path
from typing import Any, Optional

# Lazy import to avoid startup penalty
_yaml = None

def _get_yaml():
    global _yaml
    if _yaml is None:
        import yaml
        _yaml = yaml
    return _yaml


def _config_dir() -> Path:
    """Return the global config directory (~/.labvault)."""
    return Path(os.environ.get("LABVAULT_CONFIG_DIR", Path.home() / ".labvault"))


def _config_path() -> Path:
    """Return the config file path."""
    return _config_dir() / "config.yaml"


_DEFAULTS = {
    "ui": {
        "port": 5555,
        "theme": "dark",
    },
    "default_project": None,
    "auto_metrics": False,
}


def load_config() -> dict:
    """Load the config file, merging with defaults."""
    yaml = _get_yaml()
    import copy
    cfg = copy.deepcopy(_DEFAULTS)
    path = _config_path()

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
            _deep_merge(cfg, user_cfg)
        except Exception:
            pass  # Silently fall back to defaults on parse errors

    return cfg


def save_config(cfg: dict) -> Path:
    """Write the config dict to disk as YAML."""
    yaml = _get_yaml()
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    return path


def get_config_value(key: str) -> Any:
    """Get a dotted-path config value (e.g. 'ui.port')."""
    cfg = load_config()
    parts = key.split(".")
    current = cfg
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def set_config_value(key: str, value: str) -> dict:
    """Set a dotted-path config value and save. Auto-casts numeric/bool strings."""
    cfg = load_config()
    parts = key.split(".")

    # Auto-cast value
    parsed = _auto_cast(value)

    # Navigate to the parent dict
    current = cfg
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]

    current[parts[-1]] = parsed
    save_config(cfg)
    return cfg


def _auto_cast(value: str) -> Any:
    """Cast string values to appropriate Python types."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    if value.lower() in ("none", "null", "~"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base (mutates base)."""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
