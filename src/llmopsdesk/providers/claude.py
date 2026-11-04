"""Anbieter für die Claude API von Anthropic."""

import os
import time

import anthropic

from .base import LLMResponse

DEFAULT_MODEL = "claude-haiku-5-5"


class ClaudeProvider:
    name = "claude"

    def __init__(self, model: str | None = None, timeout: float = 30.0, effort: str = "low"):
        # Reihenfolge: ausdrücklich übergeben > Umgebungsvariable > Standard
        self.model = model or os.getenv("LLMOPSDESK_MODEL", DEFAULT_MODEL)
        # "effort" steuert, wie gründlich das Modell nachdenkt. Für eine einfache
        # Einordnung reicht "low": weniger Tokens, schneller, billiger.
        self.effort = effort
        # Das SDK liest ANTHROPIC_API_KEY selbst aus der Umgebung (bzw. der .env).
        # max_retries=2: Das SDK wiederholt automatisch bei Netzwerkfehlern,
        # Überlastung (429) und Serverfehlern (5xx), mit wachsender Wartezeit.
        # Schlimmster Fall: 3 Versuche x 30 s Timeout = 90 s.
        self.client = anthropic.Anthropic(timeout=timeout, max_retries=2)

    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse:
        start = time.perf_counter()  # perf_counter ist die genaueste Uhr zum Messen
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": self.effort},
        )
        latency = time.perf_counter() - start

        # Die Antwort besteht aus mehreren Blöcken (z. B. "thinking" und "text").
        # Wir brauchen nur die Text-Blöcke.
        text = "".join(block.text for block in response.content if block.type == "text")

        return LLMResponse(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_s=latency,
            model=response.model,
            provider=self.name,
            stop_reason=response.stop_reason or "",
        )
