"""Reputation-risk triage for tags and comments about the account.

Separate from qualification.py on purpose: qualification.py scores buying
intent for a lead you might sell to; this scores whether a human should look
at something someone else posted or said *about* the account. Different
question, different keywords, and — unlike a sales draft — nothing here ever
gets sent anywhere. It only decides how loudly to tell the owner "someone
tagged you" or "someone commented," so a handful of keyword checks is the
right amount of code here too.
"""

from __future__ import annotations

import re

from .engine.domain import ReputationAssessment, Signal

_NEGATIVE = re.compile(
    r"\b(?:golpe|golpista|fraude|enganad|mentira|p[ée]ssimo|horr[íi]vel|"
    r"n[ãa]o\s+recomendo|nunca\s+mais|ridículo|ridiculo|vergonha|"
    r"decepcion|falso|fake|denunci)\b",
    re.IGNORECASE,
)
_POSITIVE = re.compile(
    r"\b(?:incr[íi]vel|maravilhos|ador[ei]i|amei|recomendo|top|excelente|"
    r"sensacional|perfeito|obrigad[oa])\b",
    re.IGNORECASE,
)


def assess(signal: Signal) -> ReputationAssessment:
    text = signal.text
    if _NEGATIVE.search(text):
        return ReputationAssessment(
            risk="flag",
            reasons=("linguagem negativa/acusatória detectada — vale checar rápido",),
        )
    if _POSITIVE.search(text):
        return ReputationAssessment(risk="info", reasons=("elogio ou marcação positiva",))
    return ReputationAssessment(risk="watch", reasons=("sem sinal claro de tom — vale uma olhada quando puder",))
