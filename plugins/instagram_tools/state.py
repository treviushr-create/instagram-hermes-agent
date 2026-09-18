"""Dedup state for signal polling.

A plain JSON file on the agent's durable home (HERMES_HOME, /var/lib/hermes
inside the container — see plow-hermes-agent's README on why that path is
fixed) tracking which external_event_id values have already been surfaced,
so re-polling the same conversation doesn't re-open a resolved lead. No
database: the volume between docker compose up/down already gives this
persistence, and JSON scales fine for one seller's DM/comment volume.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_STATE_DIR = Path(os.environ.get("HERMES_HOME", ".")) / "instagram_tools"
_STATE_FILE = _STATE_DIR / "seen_signals.json"
_MAX_TRACKED = 5000


def _load() -> list[str]:
    try:
        return json.loads(_STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def is_new(external_event_id: str) -> bool:
    return external_event_id not in _load()


def mark_seen(external_event_id: str) -> None:
    seen = _load()
    if external_event_id in seen:
        return
    seen.append(external_event_id)
    if len(seen) > _MAX_TRACKED:
        seen = seen[-_MAX_TRACKED:]
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(seen))
