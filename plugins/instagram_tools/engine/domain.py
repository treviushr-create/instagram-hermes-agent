"""Core vocabulary for the Instagram social-selling loop.

Frozen dataclasses, StrEnum, __post_init__ validation — fields sized for
SKILL.md's loop (perceive -> qualify -> compose -> approve -> send) and
nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


class SignalKind(StrEnum):
    DIRECT_MESSAGE = "direct_message"
    COMMENT = "comment"
    TAG = "tag"  # someone tagged the account in their own post/reel


class DraftState(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EDITED = "edited"
    DECLINED = "declined"
    SENT = "sent"


@dataclass(frozen=True, slots=True)
class Signal:
    """One inbound DM or comment, as reported by the Meta API."""

    external_event_id: str
    account_id: str
    platform_user_id: str
    kind: SignalKind
    occurred_at: datetime
    sender_username: str | None = None
    text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.external_event_id.strip():
            raise ValueError("external_event_id é obrigatório")
        if not self.account_id.strip():
            raise ValueError("account_id é obrigatório")
        if not self.platform_user_id.strip():
            raise ValueError("platform_user_id é obrigatório")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at precisa de timezone")


@dataclass(frozen=True, slots=True)
class Qualification:
    """The outcome of scoring one signal: how much attention it deserves."""

    score: float
    priority: str  # "hot" | "warm" | "cold"
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.priority not in {"hot", "warm", "cold"}:
            raise ValueError("priority precisa ser hot, warm ou cold")


@dataclass(frozen=True, slots=True)
class ReputationAssessment:
    """How much attention a tag/comment-about-you deserves — not a sales
    score. 'risk' names why a human should look, not that it's dangerous."""

    risk: str  # "flag" | "watch" | "info"
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.risk not in {"flag", "watch", "info"}:
            raise ValueError("risk precisa ser flag, watch ou info")


@dataclass(frozen=True, slots=True)
class Draft:
    """A composed reply, waiting for the owner's approval over chat."""

    draft_id: str
    signal_id: str
    text: str
    state: DraftState = DraftState.PENDING_APPROVAL

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("draft vazio")
