"""Maskierung: sensible Daten durch Platzhalter ersetzen, BEVOR Text an einen Cloud-Anbieter geht.

Beispiel:  "SSH auf web01 (10.0.0.5) geht nicht, user: mmuster"
       ->  "SSH auf [HOST_1] ([IP_1]) geht nicht, user: [USER_1]"

- Gleicher Wert -> gleicher Platzhalter. So erkennt das Modell noch, dass zweimal
  derselbe Server gemeint ist, ohne seinen Namen zu kennen.
- Die Zuordnung (Platzhalter -> Original) bleibt auf dem eigenen Rechner. Damit setzen
  wir die Originale in der Antwort wieder ein (außer Geheimnissen, siehe unmask_data).

Grenzen (bewusst, siehe README): Namen von Personen im Fließtext werden NICHT erkannt.
Regex findet nur, was ein festes Muster hat. Für mehr bräuchte man Named Entity Recognition.
"""

import re
from dataclasses import dataclass, field

# Hostnamen wie web01, db02, build03. Diese Wörter sehen ähnlich aus, sind aber Fachbegriffe.
HOST_ALLOWLIST_PREFIXES = ("sha", "rfc", "win", "x", "ipv", "tls", "ssl", "http", "utf", "iso", "raid")

# Bekannte Domain-Endungen für vollständige Namen wie shop.example.com
TLDS = "com|de|org|net|io|eu|local|lan|intern|internal|corp"

# Reihenfolge ist wichtig: Geheimnisse und E-Mails zuerst, damit z. B. die Domain in
# einer E-Mail-Adresse nicht schon vorher als Hostname ersetzt wird.
# Format: (Art, Muster, Nummer der Gruppe, die ersetzt wird; 0 = ganzer Treffer)
PATTERNS = [
    ("SECRET", re.compile(r"(?i)\b(?:passwort|password|kennwort|api[-_]?key|token|secret)\b\s*(?:[:=]|ist|is)\s*(\S+)"), 1),
    ("SECRET", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"), 0),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), 0),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), 0),
    ("MAC", re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"), 0),
    ("USER", re.compile(r"(?i)\b(?:user(?:name)?|benutzer(?:name)?|nutzer|login|konto|account)\s*[:=]\s*([\w.\-]+)"), 1),
    ("USER", re.compile(r"(?i)(?:/home/|C:\\Users\\)([\w.\-]+)"), 1),
    ("HOST", re.compile(rf"(?i)\b(?:[a-z0-9-]+\.)+(?:{TLDS})\b"), 0),
    ("HOST", re.compile(r"(?i)\b[a-z][a-z-]*\d{2,3}\b"), 0),
]


@dataclass
class MaskResult:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)  # "[HOST_1]" -> "web01"


def _is_real_ip(value: str) -> bool:
    # 999.1.1.1 passt auf das Muster, ist aber keine IP-Adresse (jede Zahl höchstens 255).
    return all(int(part) <= 255 for part in value.split("."))


def _should_mask(kind: str, value: str) -> bool:
    if kind == "IP":
        return _is_real_ip(value)
    if kind == "HOST":
        return not value.lower().startswith(HOST_ALLOWLIST_PREFIXES)
    return True


def mask_text(text: str) -> MaskResult:
    result = MaskResult(text)
    by_value: dict[str, str] = {}   # "web01" -> "[HOST_1]", damit gleiche Werte gleich bleiben
    counters: dict[str, int] = {}

    def placeholder(kind: str, value: str) -> str:
        if value not in by_value:
            counters[kind] = counters.get(kind, 0) + 1
            token = f"[{kind}_{counters[kind]}]"
            by_value[value] = token
            result.mapping[token] = value
        return by_value[value]

    for kind, pattern, group in PATTERNS:
        def replace(match: re.Match) -> str:
            value = match.group(group)
            if not _should_mask(kind, value):
                return match.group(0)
            if group == 0:
                return placeholder(kind, value)
            # Nur die Gruppe ersetzen, z. B. bei "user: mmuster" bleibt "user: " stehen.
            start, end = match.span(group)
            whole_start = match.start(0)
            full = match.group(0)
            return full[: start - whole_start] + placeholder(kind, value) + full[end - whole_start:]

        result.text = pattern.sub(replace, result.text)
    return result


def unmask_text(text: str, mapping: dict[str, str], keep_secrets: bool = True) -> str:
    for token, original in mapping.items():
        if keep_secrets and token.startswith("[SECRET_"):
            continue  # Passwörter sollen auch lokal nicht in der Antwort auftauchen
        text = text.replace(token, original)
    return text


def unmask_data(data, mapping: dict[str, str]):
    """Setzt die Originale in allen Texten einer Antwort wieder ein (auch in Listen)."""
    if isinstance(data, str):
        return unmask_text(data, mapping)
    if isinstance(data, list):
        return [unmask_data(item, mapping) for item in data]
    if isinstance(data, dict):
        return {key: unmask_data(value, mapping) for key, value in data.items()}
    return data
