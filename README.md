# LLM OpsDesk

[![CI](https://github.com/ItsDylan255/LLM-OpsDesk/actions/workflows/ci.yml/badge.svg)](https://github.com/ItsDylan255/LLM-OpsDesk/actions/workflows/ci.yml)

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
| 2 | Testsatz (30 Tickets, Deutsch/Englisch), Auswertung, CI | ✅ (Baseline mit Claude folgt, sobald ein API-Key da ist) |
| 3 | Wissensbasis + Retrieval (RAG) mit Quellenangaben, Prompt-Varianten v0-v5, Vergleichstabelle | ✅ (Messung mit Claude folgt) |
| 4 | Maskierung sensibler Daten, Prompt-Injection-Tests, Warnung bei gefährlichen Befehlen | ✅ (Messung mit Claude folgt) |
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

## Evaluation

Der Testsatz [`evals/tickets.jsonl`](evals/tickets.jsonl) enthält 30 erfundene Tickets
(15 Deutsch, 15 Englisch, alle sechs Kategorien, drei absichtlich unklare Tickets).
Die Labels folgen festen Regeln: [`evals/LABELING.md`](evals/LABELING.md).

```powershell
llmopsdesk-eval --provider mock              # Funktionstest, kostet nichts
llmopsdesk-eval --provider claude --repeat 3 # echte Messung, 3 Durchläufe wegen Streuung
```

Gemessen werden: Anteil gültiger Antworten, Trefferquote je Feld (Kategorie, Priorität,
`needs_more_info`), Priorität "höchstens eine Stufe daneben", alles auch getrennt nach
Sprache, dazu Tokens, Kosten und Dauer pro Ticket. Ergebnisse landen in `evals/results/`.

**Vergleichswert:** Der Mock antwortet immer "network / medium" und erreicht damit 20 %
bei der Kategorie. Jedes echte Modell muss deutlich besser sein als diese "dumme" Konstante.

### Prompt-Varianten

| Version | Idee | Prompt-Größe (geschätzt*) |
|---|---|---|
| v0 | minimal: nur Felder und erlaubte Werte | ~130 Tokens |
| v1 | Baseline: Felder mit Beschreibung | ~240 Tokens |
| v2 | v1 + Regeln für Kategorie und Priorität | ~500 Tokens |
| v3 | v2 + Wissensbasis: bis zu 3 ganze Notizen, Quellenangabe | ~710 Tokens |
| v4 | sparsam: kurze Regeln, 2 gekürzte Notizen, kurze Antworten | ~530 Tokens |
| v5 | v4 + ein Beispiel (few-shot) | ~620 Tokens |

\* Schätzung mit dem Mock (4 Zeichen ≈ 1 Token). Echte Zahlen liefert die Messung mit Claude.

```powershell
llmopsdesk-eval --provider claude --task all --repeat 3   # alle Varianten messen
llmopsdesk-compare --output evals/RESULTS.md               # Vergleichstabelle erzeugen
```

### Retrieval (Wissensbasis)

[`kb/`](kb/) enthält 19 eigene Troubleshooting-Notizen. Die Suche ist **BM25**, eine klassische
Stichwortsuche ohne zusätzliche Bibliothek. Damit deutsche Tickets englische Begriffe finden
und umgekehrt, hat jede Notiz eine Zeile `keywords:` mit Begriffen in **beiden Sprachen**.
Für 9 der 30 Tickets gibt es absichtlich **keine** passende Notiz: Dann soll die Suche nichts
liefern, statt eine falsche Notiz mitzuschicken.

Gemessen ohne Sprachmodell (`llmopsdesk-retrieval`, kostet nichts), top 3:

| Schwelle (min_score) | passende Notiz gefunden (n=21) | richtig leer (n=9) |
|---|---|---|
| 0 | 100 % | 22 % |
| 3 | 100 % | 44 % |
| **6 (gewählt)** | **95 %** | **100 %** |
| 8 | 95 % | 100 % |

Der eine Fehlgriff (t18, "Cronjob ... nicht gelaufen") liegt an fehlendem Stemming:
"nächtliche" passt nicht auf "nächtlich". **Achtung:** Die Schwelle wurde an denselben
30 Tickets gewählt, an denen sie gemessen wird. Das Ergebnis ist deshalb etwas zu optimistisch.

**Grenzen:** 30 Tickets sind wenig, ein Ticket entspricht 3,3 Prozentpunkten. Kleine
Unterschiede zwischen Varianten können Zufall sein, deshalb mehrere Durchläufe (`--repeat`).
Die Tickets wurden mit KI-Hilfe geschrieben und werden von Hand geprüft (Feld `reviewed`).

## Aufbau

```
src/llmopsdesk/
├── providers/      WIE wir ein Modell aufrufen
│   ├── base.py     gemeinsame Schnittstelle (LLMProvider, LLMResponse)
│   ├── mock.py     Schein-Anbieter für Tests und CI
│   └── claude.py   Claude API
├── tasks/          WAS das Modell tun soll
│   ├── base.py     Task: Prompt + Antwortformat
│   └── ticket.py   Aufgabe "Ticket analysieren" in den Varianten v0-v5
├── runner.py       führt eine Aufgabe aus, prüft und repariert die Antwort
├── masking.py      sensible Daten vor dem API-Aufruf maskieren
├── safety.py       Tags entschärfen, gefährliche Befehle erkennen
├── injection.py    Prompt-Injection-Tests (llmopsdesk-injection)
├── retrieval.py    Suche in der Wissensbasis (BM25), llmopsdesk-retrieval
├── evaluation.py   Testsatz auswerten (llmopsdesk-eval)
├── compare.py      Vergleichstabelle der Varianten (llmopsdesk-compare)
├── metrics.py      Tokens, Kosten, Latenz in CSV
└── cli.py          Kommandozeile
evals/              Testsatz und Label-Regeln
kb/                 Wissensbasis: 19 Troubleshooting-Notizen
.github/workflows/  CI: Tests mit Python 3.10 und 3.14, nur Mock
```

**Erweiterbar:** Das Ticket-System ist nur die erste Aufgabe. Eine neue Aufgabe ist eine neue
Datei in `tasks/` (Prompt + Pydantic-Modell) plus ein Eintrag in `tasks/__init__.py`.
Ein neuer Anbieter ist eine neue Datei in `providers/` mit einer Methode `complete()`.

## Sicherheit

**Maskierung** ([`masking.py`](src/llmopsdesk/masking.py)): Vor jedem Aufruf eines Cloud-Anbieters
werden IP- und MAC-Adressen, Hostnamen, E-Mail-Adressen, Benutzernamen, Passwörter und API-Keys
durch Platzhalter ersetzt (`web01` → `[HOST_1]`). Gleiche Werte bekommen gleiche Platzhalter.
Die Zuordnung bleibt lokal; in der Antwort werden die Originale wieder eingesetzt, **außer Geheimnissen**.
Mit `--no-mask` lässt sich messen, ob die Maskierung die Qualität senkt (`llmopsdesk-eval --no-mask`).

**Prompt-Injection** ([`safety.py`](src/llmopsdesk/safety.py)), mehrere einfache Schichten:
1. Ticket und Notizen stehen in Tags und sind im System-Prompt ausdrücklich als *Daten* markiert.
2. Tags im Eingabetext werden entschärft (`</ticket>` → `[/ticket]`), damit ein Ticket nicht aus dem
   Datenbereich "ausbrechen" oder eine gefälschte Notiz einschleusen kann.
3. Die Antwort muss das feste JSON-Schema erfüllen; freie Antworten wie "PWNED" fallen durch.
4. Antworten werden auf zerstörerische Befehle geprüft (`rm -rf`, `mkfs`, `curl ... | bash` ...) und
   dann mit Warnung angezeigt. Das Programm führt **nie** Befehle aus.

[`evals/injection.jsonl`](evals/injection.jsonl) enthält 12 Angriffe (Deutsch und Englisch) in sechs
Gruppen: Priorität erzwingen, Ausgabe kapern, aus Tags ausbrechen, System-Prompt auslesen,
gefährliche Befehle unterschieben, Geheimnisse senden.

```powershell
llmopsdesk-injection --provider claude --task ticket-v3
```

Mit dem Mock (auch in der CI) sind nur die Prüfungen aussagekräftig, die *unseren* Code testen:
Verlässt ein Passwort, eine IP oder ein ausgebrochener Tag den Rechner? Alle anderen Prüfungen messen
das Modell. **Prompt-Injection lässt sich nicht vollständig verhindern**, nur erschweren und messen.

**Grenzen der Maskierung:** Sie arbeitet mit festen Mustern (Regex). Personennamen im Fließtext
("Frau Müller kann nicht drucken") werden nicht erkannt; dafür bräuchte man Named Entity Recognition.
Hostnamen werden nur erkannt, wenn sie wie `web01` (Buchstaben + 2-3 Ziffern) oder wie ein
vollständiger Domainname aussehen.

## Datenschutz (DSGVO)

- **Nur erfundene Daten:** Alle Tickets, Hostnamen und Personen in diesem Repo sind erfunden.
- **Datenminimierung (Art. 5 DSGVO):** Es geht nur der Ticket-Text an den Anbieter, und zwar maskiert.
  Die Wissensbasis-Suche läuft lokal.
- **Auftragsverarbeitung:** Wer echte Tickets an einen Cloud-Anbieter schickt, gibt personenbezogene
  Daten an einen Dienstleister weiter. Im echten Einsatz braucht es dafür einen Vertrag zur
  Auftragsverarbeitung (Art. 28 DSGVO) und eine Prüfung, wo die Daten verarbeitet werden.
- **Lokale Alternative:** Mit einem lokalen Modell über Ollama (Schritt 8) verlassen die Daten den
  Rechner gar nicht.
- **Logs:** `logs/metrics.csv` enthält nur Zahlen (Tokens, Kosten, Dauer), keine Ticket-Inhalte.
- **Geheimnisse:** Der API-Key steht nur in `.env`, die per `.gitignore` nie ins Repo kommt.

Hinweis: Dieser Abschnitt beschreibt die technischen Maßnahmen des Projekts und ist keine Rechtsberatung.

## Ausblick

Langfristig soll aus dem Projekt ein persönlicher Assistent für viele Aufgaben werden:
gleiche Infrastruktur (Provider, Validierung, Messung, Maskierung), verschiedene Aufgaben
und Wissensbasen, optional komplett lokal über Ollama.
