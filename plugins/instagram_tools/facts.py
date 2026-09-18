"""Business facts the owner has confirmed — price, delivery time, payment
methods, whatever comes up. Read before drafting so the same question isn't
asked twice; written whenever the owner states something worth remembering.

This is the actual mechanism behind SKILL.md's "never invent information the
owner hasn't confirmed": a fact only exists here because the owner said it in
this chat, and the model is the one deciding what's worth saving — this
module just persists whatever key/value it's given, plain JSON on the
agent's durable home (HERMES_HOME), same pattern as state.py.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_FACTS_DIR = Path(os.environ.get("HERMES_HOME", ".")) / "instagram_tools"
_FACTS_FILE = _FACTS_DIR / "business_facts.json"
_MAX_FACTS = 200
_MAX_VALUE_LEN = 300


def _load() -> dict[str, str]:
    try:
        return json.loads(_FACTS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(facts: dict[str, str]) -> None:
    _FACTS_DIR.mkdir(parents=True, exist_ok=True)
    _FACTS_FILE.write_text(json.dumps(facts, ensure_ascii=False, indent=2))


def get_all() -> dict[str, str]:
    return _load()


def set_fact(key: str, value: str) -> dict[str, str]:
    key = key.strip().lower()
    value = value.strip()
    if not key:
        raise ValueError("chave do fato é obrigatória")
    if not value:
        raise ValueError("valor do fato é obrigatório")
    facts = _load()
    facts[key] = value[:_MAX_VALUE_LEN]
    if len(facts) > _MAX_FACTS:
        # Drop nothing silently -- refuse instead, so the owner notices and
        # cleans up stale facts on purpose rather than losing one at random.
        raise ValueError(f"limite de {_MAX_FACTS} fatos atingido — remova algum antes de adicionar")
    _save(facts)
    return facts


def remove_fact(key: str) -> bool:
    key = key.strip().lower()
    facts = _load()
    if key not in facts:
        return False
    del facts[key]
    _save(facts)
    return True
