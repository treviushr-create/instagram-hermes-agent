"""Owner-controlled settings: which mode the agent runs in, and whether it
can send a grounded sales reply without waiting for approval first.

Same persistence pattern as facts.py/state.py — plain JSON on HERMES_HOME.
Kept in its own file, not folded into facts.py, because these aren't
business facts the owner told a lead about; they're how the agent itself is
allowed to behave.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_DIR = Path(os.environ.get("HERMES_HOME", ".")) / "instagram_tools"
_FILE = _DIR / "settings.json"

MODES = ("seller", "creator")
_DEFAULTS = {"mode": "seller", "autopilot": False}


def _load() -> dict:
    try:
        data = json.loads(_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)
    return {**_DEFAULTS, **data}


def _save(data: dict) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def get_mode() -> str:
    return _load()["mode"]


def set_mode(mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"modo precisa ser um de {MODES}")
    data = _load()
    data["mode"] = mode
    _save(data)
    return mode


def get_autopilot() -> bool:
    return bool(_load()["autopilot"])


def set_autopilot(enabled: bool) -> bool:
    data = _load()
    data["autopilot"] = bool(enabled)
    _save(data)
    return data["autopilot"]
