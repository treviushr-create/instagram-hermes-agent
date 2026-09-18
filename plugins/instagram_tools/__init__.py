"""Instagram tools for the instagram-social-selling skill.

`fetch_new_signals` and `send_reply` call the real Meta Graph API
(graph_api.py) — they need INSTAGRAM_ACCESS_TOKEN and
INSTAGRAM_BUSINESS_ACCOUNT_ID in the environment to actually work; without
them they raise DeliveryError rather than pretending to have sent something.
"""

from __future__ import annotations

from .engine.domain import Qualification, Signal, SignalKind, utc_now
from .engine.ports import DeliveryReceipt

from . import graph_api, state
from .qualification import qualify as _qualify

__all__ = [
    "Signal",
    "SignalKind",
    "Qualification",
    "fetch_new_signals",
    "qualify",
    "send_reply",
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
