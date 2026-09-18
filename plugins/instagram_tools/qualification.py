"""Simple, honest qualification for one Instagram signal.

Deliberately NOT a port of social-selling-control-plane's qualification.py/
rules.py — those are ~2000 lines of regex tuned incident-by-incident to one
client's high-ticket coaching sales script, and they earn their complexity by
running unattended at scale with no per-message human approval.

This agent's design is different: every draft this qualifier feeds into goes
to the owner for approval before it ever reaches the lead (see SKILL.md). The
human approval step is the safety net; this function's only job is deciding
how loudly to ask for the owner's attention, not whether a message is safe to
send. That is why a handful of keyword checks is the right amount of code
here, not a gap to fill in later.
"""

from __future__ import annotations

import re

from engine.domain import Qualification, Signal

_BUYING_INTENT = re.compile(
    r"\b(?:pre[çc]o|quanto\s+custa|valor|comprar|onde\s+(?:eu\s+)?(?:consigo\s+)?compro|"
    r"tem\s+dispon[íi]vel|manda\s+o\s+link|como\s+fa[çc]o\s+pra\s+comprar|"
    r"tem\s+no\s+tamanho|pix)\b",
    re.IGNORECASE,
)
_QUESTION = re.compile(r"\?")


def qualify(signal: Signal) -> Qualification:
    text = signal.text
    if _BUYING_INTENT.search(text):
        return Qualification(
            score=0.9,
            priority="hot",
            reasons=("pergunta direta sobre preço/compra",),
        )
    if _QUESTION.search(text):
        return Qualification(
            score=0.5,
            priority="warm",
            reasons=("pergunta que espera resposta",),
        )
    return Qualification(score=0.2, priority="cold", reasons=("sem sinal claro de intenção de compra",))
