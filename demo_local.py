"""Local demo of the qualify step against a few realistic DMs.

Not a substitute for the real Hermes loop (draft/approve/send need a live
Meta account and the Hermes gateway) — this is here so progress is visible
without Docker, Plow, or Meta credentials while those pieces come online.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")

from plugins.instagram_tools import Signal, SignalKind, qualify

EXAMPLES = [
    "Oi, quanto custa o vestido azul que vc postou?",
    "Lindo esse post! ❤️",
    "Vocês têm no tamanho M? Onde eu compro?",
    "Bom dia",
    "Consigo pagar no pix?",
]

print(f"{'MENSAGEM':<55} {'PRIORIDADE':<10} SCORE  MOTIVO")
print("-" * 100)
for text in EXAMPLES:
    signal = Signal(
        external_event_id=f"demo-{hash(text)}",
        account_id="demo-account",
        platform_user_id="demo-lead",
        kind=SignalKind.DIRECT_MESSAGE,
        occurred_at=datetime.now(timezone.utc),
        text=text,
    )
    result = qualify(signal)
    reason = result.reasons[0] if result.reasons else ""
    print(f"{text:<55} {result.priority:<10} {result.score:<6} {reason}")
