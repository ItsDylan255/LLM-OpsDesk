# LLM OpsDesk

KI-gestützter IT-Support-Assistent: Er nimmt ein IT-Ticket als Text, lässt es von einem
Sprachmodell analysieren und liefert eine **geprüfte, strukturierte Antwort** (Kategorie,
Priorität, Zusammenfassung, mögliche Ursachen, nächste Schritte).

Der Schwerpunkt liegt nicht auf dem API-Aufruf selbst, sondern auf allem drumherum:
**Messbarkeit** (Tokens, Kosten, Latenz pro Aufruf), **Qualitätsprüfung** (Pydantic, Testsatz),
**austauschbare Anbieter** und **Sicherheit/Datenschutz**.

> **Hinweis zur Entstehung:** Dieses Projekt wurde mit KI-Unterstützung (Claude Code von
> Anthropic) entwickelt ("vibe coding"). Architektur und Entscheidungen wurden gemeinsam
> erarbeitet; der Code ist bewusst einfach gehalten und ausführlich kommentiert.

## Status

| Schritt | Inhalt | Stand |
|---|---|---|
| 1 | Kern: Provider (Claude, Mock), Aufgaben-Konzept, Validierung, Reparaturversuch, Metriken, CLI | ✅ |
| 2 | Testsatz (30 Tickets, Deutsch/Englisch), Auswertungsskript, Baseline, CI | geplant |
| 3 | Wissensbasis + Retrieval (RAG) mit Quellenangaben, Prompt-Varianten im Vergleich | geplant |
| 4 | Maskierung sensibler Daten, Prompt-Injection-Tests | geplant |
| 5 | README mit Ergebnistabelle und Grenzen | geplant |
| 6 | FastAPI + schlichte Web-Oberfläche | geplant |
| 7 | Docker | geplant |
| 8 | Lokales Modell über Ollama im Vergleich | geplant |

## Installation (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env   # danach den API-Key in .env eintragen
```

## Benutzung

```powershell
# Ohne API-Key und ohne Kosten (feste Mock-Antwort):
llmopsdesk examples\ticket_ssh_de.txt

# Mit Claude (braucht ANTHROPIC_API_KEY in .env):
llmopsdesk examples\ticket_ssh_de.txt --provider claude
```

Jeder Modellaufruf wird in `logs/metrics.csv` protokolliert (Tokens, Kosten, Latenz, gültig ja/nein).

Tests:

```powershell
python -m pytest
```

## Aufbau

```
src/llmopsdesk/
├── providers/      WIE wir ein Modell aufrufen
│   ├── base.py     gemeinsame Schnittstelle (LLMProvider, LLMResponse)
│   ├── mock.py     Schein-Anbieter für Tests und CI
│   └── claude.py   Claude API
├── tasks/          WAS das Modell tun soll
│   ├── base.py     Task: Prompt + Antwortformat
│   └── ticket.py   Aufgabe "Ticket analysieren"
├── runner.py       führt eine Aufgabe aus, prüft und repariert die Antwort
├── metrics.py      Tokens, Kosten, Latenz in CSV
└── cli.py          Kommandozeile
```

**Erweiterbar:** Das Ticket-System ist nur die erste Aufgabe. Eine neue Aufgabe ist eine neue
Datei in `tasks/` (Prompt + Pydantic-Modell) plus ein Eintrag in `tasks/__init__.py`.
Ein neuer Anbieter ist eine neue Datei in `providers/` mit einer Methode `complete()`.

## Sicherheit und Datenschutz

- Der API-Key steht nur in `.env`, die per `.gitignore` nie ins Repo kommt.
- Der Ticket-Text wird als **Daten** behandelt (zwischen `<ticket>`-Tags, mit ausdrücklicher Anweisung,
  darin enthaltene Befehle nicht zu befolgen). Wie gut das wirkt, wird in Schritt 4 gemessen.
- Das Programm führt **nie** Befehle aus; `next_steps` sind nur Vorschläge für Menschen.
- Alle Beispieltickets sind erfunden.

## Ausblick

Langfristig soll aus dem Projekt ein persönlicher Assistent für viele Aufgaben werden:
gleiche Infrastruktur (Provider, Validierung, Messung, Maskierung), verschiedene Aufgaben
und Wissensbasen, optional komplett lokal über Ollama.
