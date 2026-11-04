"""Schutzmaßnahmen gegen Prompt-Injection und gefährliche Vorschläge.

Prompt-Injection: Jemand schreibt Anweisungen ins Ticket ("Ignoriere alle Regeln ...").
Man kann das nicht vollständig verhindern, nur erschweren und MESSEN (llmopsdesk-injection).
Hier zwei einfache Schichten:
1. neutralize_tags: Ein Ticket darf unsere Trenn-Tags nicht selbst schließen
   (sonst könnte es mit "</ticket>" aus dem Datenbereich "ausbrechen").
2. find_dangerous_commands: Prüft die ANTWORT auf zerstörerische Befehle. Das Programm
   führt nie etwas aus, aber ein Mensch könnte einen Vorschlag blind kopieren.
"""

import re

# Tags, mit denen wir im Prompt Daten von Anweisungen trennen
PROMPT_TAGS = ("ticket", "knowledge_base", "note", "previous_answer")

_TAG_PATTERN = re.compile(r"<\s*(/?)\s*(" + "|".join(PROMPT_TAGS) + r")\b[^>]*>", re.IGNORECASE)


def neutralize_tags(text: str) -> str:
    """Macht aus <ticket> bzw. </ticket> im Eingabetext harmloses [ticket] bzw. [/ticket]."""
    return _TAG_PATTERN.sub(lambda m: f"[{m.group(1)}{m.group(2).lower()}]", text)


DANGEROUS_PATTERNS = {
    "rm -rf": r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r",
    "mkfs": r"\bmkfs(\.\w+)?\b",
    "dd auf Gerät": r"\bdd\s+if=.*of=/dev/",
    "DROP TABLE/DATABASE": r"\bdrop\s+(table|database)\b",
    "chmod 777 rekursiv": r"\bchmod\s+-R\s+777\b",
    "Skript aus dem Netz ausführen": r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b",
    "Fork-Bombe": r":\(\)\s*\{",
}


def find_dangerous_commands(text: str) -> list[str]:
    """Liste der gefundenen gefährlichen Muster (leer = nichts gefunden)."""
    return [name for name, pattern in DANGEROUS_PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]
