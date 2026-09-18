"""Interfaces the instagram_tools plugin implements against.

Sized to exactly this agent's own loop (perceive -> qualify -> compose ->
approve -> send) — no CRM/Calendar/audio-video integrations, no fact schema
beyond what a single Instagram seller's DM/comment flow needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .domain import Draft, Qualification, Signal


class DeliveryError(RuntimeError):
    """A send to the Meta API failed."""

    def __init__(self, message: str, *, retryable: bool, status_code: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class DeliveryReceipt:
    message_id: str

    def __post_init__(self) -> None:
        if not self.message_id.strip():
            raise ValueError("message_id do recibo é obrigatório")


class InboxReader(Protocol):
    """Reads new DMs/comments from the Meta API for one connected account."""

    def read_new_signals(self) -> tuple[Signal, ...]: ...


class Qualifier(Protocol):
    """Scores and prioritizes one signal."""

    def qualify(self, signal: Signal) -> Qualification: ...


class Composer(Protocol):
    """Drafts a reply, grounded only in facts the owner has confirmed."""

    def compose(self, *, signal: Signal, known_facts: dict[str, str]) -> Draft: ...


class Sender(Protocol):
    """Sends an owner-approved draft back to the lead via the official API."""

    def send(self, *, signal: Signal, text: str) -> DeliveryReceipt: ...


class ApprovalChannel(Protocol):
    """The Plow Chat side: asks the owner to approve/edit/decline a draft."""

    def request_approval(self, draft: Draft) -> None: ...

    def poll_decision(self, draft_id: str) -> str | None:
        """Returns 'approved' | 'declined' | an edited text, or None if still pending."""
        ...
