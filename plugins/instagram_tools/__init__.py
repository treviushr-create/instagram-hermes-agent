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

from . import facts as _facts
from . import graph_api, state
from .engine.domain import Qualification, ReputationAssessment, Signal, SignalKind
from .engine.ports import DeliveryReceipt
from .qualification import qualify as _qualify
from .reputation import assess as _assess_reputation

TOOLSET = "instagram"

__all__ = [
    "Signal",
    "SignalKind",
    "Qualification",
    "ReputationAssessment",
    "fetch_new_signals",
    "fetch_new_mentions",
    "fetch_new_own_comments",
    "qualify",
    "assess_reputation",
    "send_reply",
    "get_facts",
    "set_fact",
    "remove_fact",
    "register",
]


def fetch_new_signals() -> list[Signal]:
    """New DMs since the last poll, deduped against state.py."""
    all_signals = graph_api.fetch_new_conversations()
    new_signals = [s for s in all_signals if state.is_new(s.external_event_id)]
    for signal in new_signals:
        state.mark_seen(signal.external_event_id)
    return new_signals


def fetch_new_mentions() -> list[Signal]:
    """New posts/reels where someone tagged this account, deduped.

    Tags on someone else's own post, not @-mentions inside a comment — Meta
    only pushes those through a webhook, which this agent has no inbound
    port to receive (see graph_api.fetch_new_tags for why).
    """
    all_signals = graph_api.fetch_new_tags()
    new_signals = [s for s in all_signals if state.is_new(s.external_event_id)]
    for signal in new_signals:
        state.mark_seen(signal.external_event_id)
    return new_signals


def fetch_new_own_comments() -> list[Signal]:
    """New comments on the account's own recent posts, deduped."""
    all_signals = graph_api.fetch_new_comments()
    new_signals = [s for s in all_signals if state.is_new(s.external_event_id)]
    for signal in new_signals:
        state.mark_seen(signal.external_event_id)
    return new_signals


def qualify(signal: Signal) -> Qualification:
    return _qualify(signal)


def assess_reputation(signal: Signal) -> ReputationAssessment:
    return _assess_reputation(signal)


def get_facts() -> dict[str, str]:
    return _facts.get_all()


def set_fact(key: str, value: str) -> dict[str, str]:
    return _facts.set_fact(key, value)


def remove_fact(key: str) -> bool:
    return _facts.remove_fact(key)


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
    "description": "One Instagram DM/comment/tag, as returned by an instagram_fetch_* tool.",
    "properties": {
        "external_event_id": {"type": "string"},
        "account_id": {"type": "string"},
        "platform_user_id": {"type": "string", "description": "the sender's Instagram-scoped id"},
        "kind": {"type": "string", "enum": ["direct_message", "comment", "tag"]},
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


def _fetch_mentions_handler(_args: dict) -> dict:
    try:
        signals = fetch_new_mentions()
    except Exception as error:
        return {"ok": False, "error": str(error)}
    return {"ok": True, "signals": [_signal_to_dict(s) for s in signals]}


def _fetch_own_comments_handler(_args: dict) -> dict:
    try:
        signals = fetch_new_own_comments()
    except Exception as error:
        return {"ok": False, "error": str(error)}
    return {"ok": True, "signals": [_signal_to_dict(s) for s in signals]}


def _assess_reputation_handler(args: dict) -> dict:
    signal = _signal_from_args(args["signal"])
    result = assess_reputation(signal)
    return {"ok": True, "risk": result.risk, "reasons": list(result.reasons)}


def _get_facts_handler(_args: dict) -> dict:
    return {"ok": True, "facts": get_facts()}


def _set_fact_handler(args: dict) -> dict:
    try:
        facts = set_fact(args["key"], args["value"])
    except ValueError as error:
        return {"ok": False, "error": str(error)}
    return {"ok": True, "facts": facts}


def _remove_fact_handler(args: dict) -> dict:
    removed = remove_fact(args["key"])
    return {"ok": True, "removed": removed, "facts": get_facts()}


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

FETCH_MENTIONS = Tool(
    name="instagram_fetch_mentions",
    description=(
        "New posts/reels where someone tagged this account, already deduped. "
        "This is for reputation monitoring, not sales — call this "
        "periodically (or when the owner asks 'did anyone tag me?') to see "
        "if someone posted something about the owner worth knowing about. "
        "Returns {ok: true, signals: [...]} or {ok: false, error}."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    handler=_fetch_mentions_handler,
)

FETCH_OWN_COMMENTS = Tool(
    name="instagram_fetch_own_comments",
    description=(
        "New comments on the account's own recent posts, already deduped. "
        "A public comment can carry either a sales question (use "
        "instagram_qualify) or a reputation risk (use "
        "instagram_assess_reputation) — check both, it's often not obvious "
        "which from the text alone. Returns {ok: true, signals: [...]} or "
        "{ok: false, error}."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    handler=_fetch_own_comments_handler,
)

ASSESS_REPUTATION_TOOL = Tool(
    name="instagram_assess_reputation",
    description=(
        "Triage a tag or comment for reputation risk (flag/watch/info) — "
        "different question from instagram_qualify, which scores buying "
        "intent. Use this for signals from instagram_fetch_mentions, and "
        "for comments that read like a public complaint rather than a "
        "sales question."
    ),
    parameters={
        "type": "object",
        "properties": {"signal": _SIGNAL_SCHEMA},
        "required": ["signal"],
        "additionalProperties": False,
    },
    handler=_assess_reputation_handler,
)

GET_FACTS_TOOL = Tool(
    name="instagram_facts_get",
    description=(
        "Everything the owner has already confirmed about the business — "
        "price, delivery time, payment methods, whatever came up before. "
        "Call this BEFORE drafting any sales reply, so you don't ask the "
        "owner something they already told you. Returns {ok: true, facts: "
        "{key: value, ...}}."
    ),
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
    handler=_get_facts_handler,
)

SET_FACT_TOOL = Tool(
    name="instagram_facts_set",
    description=(
        "Save one fact the owner just confirmed in this conversation (e.g. "
        "key='preco_vestido_azul', value='R$89, entrega em 3 dias úteis'). "
        "Call this right after the owner tells you something reusable, so "
        "the next lead who asks the same thing doesn't require asking the "
        "owner again. Never save something the owner didn't actually say."
    ),
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "short snake_case identifier, e.g. 'preco_vestido_azul'"},
            "value": {"type": "string"},
        },
        "required": ["key", "value"],
        "additionalProperties": False,
    },
    handler=_set_fact_handler,
)

REMOVE_FACT_TOOL = Tool(
    name="instagram_facts_remove",
    description="Forget a fact — use when the owner corrects or retires something previously saved (price changed, item sold out, etc.).",
    parameters={
        "type": "object",
        "properties": {"key": {"type": "string"}},
        "required": ["key"],
        "additionalProperties": False,
    },
    handler=_remove_fact_handler,
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

TOOLS: tuple[Tool, ...] = (
    FETCH_SIGNALS,
    FETCH_MENTIONS,
    FETCH_OWN_COMMENTS,
    QUALIFY_TOOL,
    ASSESS_REPUTATION_TOOL,
    GET_FACTS_TOOL,
    SET_FACT_TOOL,
    REMOVE_FACT_TOOL,
    SEND_REPLY_TOOL,
)


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
