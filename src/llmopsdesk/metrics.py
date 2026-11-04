"""Schreibt pro Modellaufruf eine Zeile mit Tokens, Kosten und Dauer in eine CSV-Datei."""

import csv
from datetime import datetime, timezone
from pathlib import Path

from .providers.base import LLMResponse

LOG_FILE = Path("logs/metrics.csv")

FIELDS = [
    "timestamp", "task", "prompt_version", "provider", "model", "attempt",
    "input_tokens", "output_tokens", "cost_usd", "latency_s", "valid", "stop_reason",
]

# Preise in US-Dollar pro 1 Million Tokens: (Input, Output).
# Stand: Anthropic-Preisliste, abgerufen 2026-11-04. Vor Auswertungen auf
# der Preisseite des Anbieters prüfen, Preise ändern sich!
# Haiku 5.5: Preis gilt für Prompts bis 100.000 Tokens (darüber teurer).
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "mock": (0.0, 0.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Kosten in US-Dollar, oder None, wenn das Modell nicht in der Preistabelle steht."""
    prices = PRICES_PER_MTOK.get(model)
    if prices is None:
        return None
    price_in, price_out = prices
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def log_call(
    response: LLMResponse,
    task: str,
    prompt_version: str,
    attempt: int,
    valid: bool,
    log_file: Path = LOG_FILE,
) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)  # legt logs/ an, falls nötig
    new_file = not log_file.exists()
    cost = estimate_cost(response.model, response.input_tokens, response.output_tokens)

    # "a" = anhängen; newline="" verhindert unter Windows leere Zwischenzeilen
    with log_file.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()  # Spaltennamen nur einmal, ganz oben
        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "task": task,
            "prompt_version": prompt_version,
            "provider": response.provider,
            "model": response.model,
            "attempt": attempt,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost_usd": "" if cost is None else f"{cost:.6f}",
            "latency_s": f"{response.latency_s:.2f}",
            "valid": valid,
            "stop_reason": response.stop_reason,
        })
