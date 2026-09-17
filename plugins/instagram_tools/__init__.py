"""Instagram tools for the instagram-social-selling skill.

STUB. Each function below is the seam where the audited, de-identified
decision engine (see ../../engine_audit/README.md) gets wired in. Nothing here
talks to Meta yet — filling that in is the next concrete task, not a detail
left for later out of laziness: shipping a fake reply engine that "sends"
would be worse than not having one.

The real implementation should keep the same shape the control-plane already
proved out: perceive -> qualify -> compose -> guard -> act, each step a
function that a Hermes turn can call and get a plain-data answer back.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Signal:
    id: str
    kind: str  # "direct_message" | "comment"
    text: str
    sender_username: str


def fetch_new_signals() -> list[Signal]:
    """Return Instagram DMs/comments received since the last check.

    TODO: call the Meta Graph API (Instagram Business Login) the same way
    social-selling-control-plane's perception.py does, once that module has
    been through the audit in engine_audit/README.md.
    """
    raise NotImplementedError("wire this to the Meta API + audited perception logic")


def qualify(signal: Signal) -> dict:
    """Score and prioritize a signal.

    TODO: port the scoring logic from qualification.py after stripping the
    client-specific references the audit found there.
    """
    raise NotImplementedError("wire this to the audited qualification logic")


def send_reply(signal_id: str, text: str) -> None:
    """Send an owner-approved reply back to the lead via the official API.

    Must only ever be called after explicit owner approval in the chat —
    that rule lives in SKILL.md, not here, but this function is the last line
    of defense: it should refuse to run without an approval token once one
    exists.
    """
    raise NotImplementedError("wire this to the Meta API send path")
