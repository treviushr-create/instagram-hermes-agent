"""instagram_tools -- registers this agent's Instagram tools with Hermes.

The model calls tools by name, not by reading skill prose — a plugin that
only defines importable Python functions, with no `register(ctx)` calling
`ctx.register_tool(...)`, gives the model nothing to call. This follows the
same contract plow-pbc/life-assistant-hermes-agent's plugins/life_tools uses:
a Tool per capability, a JSON schema for its arguments, a handler returning
a JSON-serializable dict, registered in `register(ctx)`.

`fetch_new_signals`/`qualify`/`send_reply` stay plain, importable functions
too (demo_local.py and tests use them directly) — the Tool wrappers below
just expose the same three functions to the model.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial

from . import graph_api, state
from .engine.domain import Qualification, Signal, SignalKind
from .engine.ports import DeliveryReceipt
from .qualification import qualify as _qualify

TOOLSET = "instagram"

__all__ = [
    "Signal",
    "SignalKind",
    "Qualification",
    "fetch_new_signals",
    "qualify",
    "send_reply",
    "register",
]


def fetch_new_signals() -> list[Signal]:
    """New DMs since the last poll, deduped against state.py.

    Comments are not polled yet — add comment polling as its own function
    later rather than overloading this one.
    """
    all_signals = graph_api.fetch_new_conversations()
    new_signals = [s for s in all_signals if state.is_new(s.external_event_id)]
    for signal in new_signals:
        state.mark_seen(signal.external_event_id)
    return new_signals


def qualify(signal: Signal) -> Qualification:
    return _qualify(signal)


def send_reply(signal: Signal, text: str) -> DeliveryReceipt:
    """Send an owner-approved reply back to the lead via the official API.

    Must only ever be called after explicit owner approval in the chat —
    that rule lives in SKILL.md, not here. This function does not itself
    check for an approval token (the Hermes turn calling it is the thing
    that must have already gated on approval); it is the transport, not the
    policy.
    """
    if signal.kind == SignalKind.COMMENT:
        return graph_api.reply_to_comment(comment_id=signal.platform_user_id, text=text)
    return graph_api.send_text_message(recipient_id=signal.platform_user_id, text=text)


# --- Tool registration (what actually makes the model able to call these) ---

_SIGNAL_SCHEMA = {
    "type": "object",
    "description": "One Instagram DM/comment, as returned by instagram_fetch_signals.",
    "properties": {
        "external_event_id": {"type": "string"},
        "account_id": {"type": "string"},
        "platform_user_id": {"type": "string", "description": "the sender's Instagram-scoped id"},
        "kind": {"type": "string", "enum": ["direct_message", "comment"]},
        "occurred_at": {"type": "string", "description": "ISO 8601 timestamp"},
        "sender_username": {"type": "string"},
        "text": {"type": "string"},
    },
    "required": ["external_event_id", "platform_user_id", "text"],
}


def _signal_from_args(args: dict) -> Signal:
    """Build a Signal from a tool call's arguments.

    account_id isn't in any tool's JSON schema on purpose — this agent talks
    to exactly one Instagram account, so which one is an implementation
    detail, not something the model should have to track and repeat back on
    every call. Falls back to the configured account id, or a fixed
    placeholder in a context where none is set yet (Signal itself still
    requires the field to be non-empty).
    """
    occurred_at = args.get("occurred_at")
    return Signal(
        external_event_id=args["external_event_id"],
        account_id=args.get("account_id") or os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID") or "self",
        platform_user_id=args["platform_user_id"],
        kind=SignalKind(args.get("kind") or "direct_message"),
        occurred_at=datetime.fromisoformat(occurred_at) if occurred_at else datetime.now(timezone.utc),
        sender_username=args.get("sender_username"),
        text=args.get("text", ""),
    )


def _signal_to_dict(signal: Signal) -> dict:
    return {
        "external_event_id": signal.external_event_id,
        "account_id": signal.account_id,
        "platform_user_id": signal.platform_user_id,
        "kind": signal.kind.value,
        "occurred_at": signal.occurred_at.isoformat(),
        "sender_username": signal.sender_username,
        "text": signal.text,
    }


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    handler: object  # callable(args: dict) -> dict, JSON-serializable

    @property
    def schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


def _fetch_signals_handler(_args: dict) -> dict:
    try:
        signals = fetch_new_signals()
    except Exception as error:  # DeliveryError (missing credentials) or a real API failure
        return {"ok": False, "error": str(error)}
    return {"ok": True, "signals": [_signal_to_dict(s) for s in signals]}


def _qualify_handler(args: dict) -> dict:
    signal = _signal_from_args(args["signal"])
    result = qualify(signal)
    return {"ok": True, "score": result.score, "priority": result.priority, "reasons": list(result.reasons)}


def _send_reply_handler(args: dict) -> dict:
    signal = _signal_from_args(args["signal"])
    try:
        receipt = send_reply(signal, args["text"])
    except Exception as error:
        return {"ok": False, "error": str(error)}
    return {"ok": True, "message_id": receipt.message_id}


FETCH_SIGNALS = Tool(
    name="instagram_fetch_signals",
    description=(
        "New Instagram DMs since the last check, already deduped — call this "
        "to see if there is anything new to handle. Returns "
        "{ok: true, signals: [...]}, or {ok: false, error} when the "
        "Instagram account is not connected yet (say so plainly, don't "
        "pretend there is nothing new)."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    handler=_fetch_signals_handler,
)

QUALIFY_TOOL = Tool(
    name="instagram_qualify",
    description="Score and prioritize one Instagram signal (hot/warm/cold) before drafting a reply.",
    parameters={
        "type": "object",
        "properties": {"signal": _SIGNAL_SCHEMA},
        "required": ["signal"],
        "additionalProperties": False,
    },
    handler=_qualify_handler,
)

SEND_REPLY_TOOL = Tool(
    name="instagram_send_reply",
    description=(
        "Send a reply back to the lead via the official Instagram API. Only "
        "call this after the owner has explicitly approved this exact text "
        "in this conversation — never before."
    ),
    parameters={
        "type": "object",
        "properties": {"signal": _SIGNAL_SCHEMA, "text": {"type": "string"}},
        "required": ["signal", "text"],
        "additionalProperties": False,
    },
    handler=_send_reply_handler,
)

TOOLS: tuple[Tool, ...] = (FETCH_SIGNALS, QUALIFY_TOOL, SEND_REPLY_TOOL)


def _run(tool: Tool, args: dict, **_kwargs) -> str:
    return json.dumps(tool.handler(args or {}))


def register(ctx) -> None:
    for tool in TOOLS:
        ctx.register_tool(
            name=tool.name,
            toolset=TOOLSET,
            schema=tool.schema,
            handler=partial(_run, tool),
            description=tool.description,
        )
