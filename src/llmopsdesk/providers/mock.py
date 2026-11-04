"""Ein Schein-Anbieter für Tests und CI: kein API-Key, keine Kosten, immer gleiche Antworten."""

import json

from .base import LLMResponse

# Eine gültige Ticket-Analyse als Standardantwort.
# json.dumps statt Text von Hand: so ist das JSON garantiert gültig.
DEFAULT_RESPONSE = json.dumps({
    "category": "network",
    "priority": "medium",
    "summary": "Mock-Antwort: Es wurde kein echtes Modell aufgerufen.",
    "possible_causes": ["Mock-Provider aktiv"],
    "next_steps": ["Für echte Analysen --provider claude verwenden"],
    "sources": [],
    "needs_more_info": False,
})


class MockProvider:
    name = "mock"

    def __init__(self, responses: list[str] | None = None, model: str = "mock"):
        # Mehrere Antworten erlauben Tests wie "erst kaputtes JSON, dann gültiges".
        self.responses = responses or [DEFAULT_RESPONSE]
        self.model = model
        # Merkt sich jeden Aufruf, damit Tests prüfen können, was gesendet wurde.
        self.calls: list[dict] = []

    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse:
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens})
        # 1. Aufruf -> Antwort 0, 2. Aufruf -> Antwort 1, ...
        # Gibt es keine weitere Antwort, wird die letzte wiederholt.
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        text = self.responses[index]
        return LLMResponse(
            text=text,
            # Grobe Schätzung (ca. 4 Zeichen pro Token). Nie für echte Auswertungen benutzen!
            input_tokens=(len(system) + len(user)) // 4,
            output_tokens=len(text) // 4,
            latency_s=0.0,
            model=self.model,
            provider=self.name,
            stop_reason="end_turn",
        )
