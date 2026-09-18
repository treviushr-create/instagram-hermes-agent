"""Instagram tools for the instagram-social-selling skill.

`qualify` is real (see qualification.py) — it doesn't need the RealDeal
engine at all, see engine_audit/README.md for why. `fetch_new_signals` and
`send_reply` are still stubs: they need real Meta API credentials (Passo 5-8
of the Meta setup) that don't exist yet. Shipping a fake reply engine that
"sends" would be worse than not having one, so they raise on purpose rather
than pretending.
"""

from __future__ import annotations

from engine.domain import Qualification, Signal, SignalKind, utc_now

from .qualification import qualify as _qualify

__all__ = ["Signal", "SignalKind", "Qualification", "fetch_new_signals", "qualify", "send_reply"]


def fetch_new_signals() -> list[Signal]:
    """Return Instagram DMs/comments received since the last check.

    TODO: call the Meta Graph API (Instagram Business Login) with the
    credentials from the Meta setup guide (INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_BUSINESS_ACCOUNT_ID). No control-plane code to wait on here —
    this is a plain Graph API GET, same shape trevius-selling's
    lib/instagram-api.ts already proved out, just in Python.
    """
    raise NotImplementedError("wire this to the Meta Graph API once app credentials exist")


def qualify(signal: Signal) -> Qualification:
    return _qualify(signal)


def send_reply(signal: Signal, text: str) -> None:
    """Send an owner-approved reply back to the lead via the official API.

    Must only ever be called after explicit owner approval in the chat —
    that rule lives in SKILL.md, not here, but this function is the last line
    of defense: it should refuse to run without an approval token once one
    exists.
    """
    raise NotImplementedError("wire this to the Meta API send path")
