"""Wählt anhand eines Namens den passenden Anbieter aus.

Neuen Anbieter hinzufügen (z. B. Ollama):
1. Datei providers/ollama.py mit einer Klasse, die complete() hat
2. hier in get_provider() einen Fall ergänzen
"""

from .base import LLMProvider, LLMResponse

PROVIDER_NAMES = ["mock", "claude"]


def get_provider(name: str) -> LLMProvider:
    if name == "mock":
        from .mock import MockProvider
        return MockProvider()
    if name == "claude":
        # Import erst hier: Wer nur den Mock nutzt, braucht kein Anthropic-Setup.
        from .claude import ClaudeProvider
        return ClaudeProvider()
    raise ValueError(f"Unbekannter Provider: {name!r}. Erlaubt: {PROVIDER_NAMES}")


__all__ = ["LLMProvider", "LLMResponse", "PROVIDER_NAMES", "get_provider"]
