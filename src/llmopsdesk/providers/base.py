"""Gemeinsame Schnittstelle für alle Modell-Anbieter.

Der Rest des Programms kennt nur diese Datei. Dadurch kann man den Anbieter
austauschen (Claude, Mock), ohne anderen Code zu ändern.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResponse:
    """Das Ergebnis eines einzelnen Modellaufrufs, einheitlich für alle Anbieter."""

    text: str            # die Antwort des Modells als Text
    input_tokens: int    # Tokens, die wir geschickt haben (kosten Geld)
    output_tokens: int   # Tokens, die das Modell erzeugt hat (kosten mehr Geld)
    latency_s: float     # Dauer des Aufrufs in Sekunden
    model: str           # welches Modell geantwortet hat
    provider: str        # welcher Anbieter (z. B. "claude", "mock")
    stop_reason: str = ""  # warum das Modell aufgehört hat, z. B. "max_tokens"


class LLMProvider(Protocol):
    """Jeder Anbieter muss genau diese Methode haben.

    Protocol heißt: Eine Klasse muss nicht davon erben. Es reicht, dass sie
    eine passende Methode complete() besitzt ("Duck Typing" mit Typprüfung).
    """

    name: str

    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse: ...
