"""Vergleichstabelle: liest gespeicherte Auswertungen und stellt die Varianten nebeneinander.

Aufruf:  llmopsdesk-compare                    (Tabelle anzeigen)
         llmopsdesk-compare --output evals/RESULTS.md
Pro Kombination aus Aufgabe, Provider und Modell zählt die neueste Auswertung.
Bei mehreren Durchläufen (--repeat) wird der Mittelwert gezeigt.
"""

import argparse
import json
import sys
from pathlib import Path

from .evaluation import RESULTS_DIR


def load_latest(results_dir: Path, include_mock: bool) -> list[dict]:
    latest: dict[tuple, dict] = {}
    # Dateinamen beginnen mit dem Zeitstempel: sortiert = älteste zuerst, neuere überschreiben.
    for path in sorted(results_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data["meta"]
        if meta["provider"] == "mock" and not include_mock:
            continue
        latest[(meta["task"], meta["provider"], meta["model"])] = data
    return sorted(latest.values(), key=lambda d: (d["meta"]["model"], d["meta"]["task"]))


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def row_for(data: dict) -> list[str]:
    meta, runs = data["meta"], data["summaries"]

    def avg(get):
        values = [get(s) for s in runs]
        values = [v for v in values if v is not None]
        return mean(values) if values else None

    def pct(value):
        return "–" if value is None else f"{value * 100:.0f} %"

    cost = avg(lambda s: s["total_cost_usd"])
    cost_per_ticket = None if cost is None else cost / meta["n_cases"]
    return [
        meta["task"],
        meta["model"],
        str(meta["repeat"]),
        pct(avg(lambda s: s["valid_rate"])),
        pct(avg(lambda s: s["accuracy"].get("category"))),
        pct(avg(lambda s: s["accuracy"].get("priority"))),
        pct(avg(lambda s: s["within_one"].get("priority"))),
        pct(avg(lambda s: s["accuracy"].get("needs_more_info"))),
        pct(avg(lambda s: s.get("retrieval_hit"))),
        pct(avg(lambda s: s.get("sources_correct"))),
        f"{avg(lambda s: s['avg_input_tokens']):.0f}",
        f"{avg(lambda s: s['avg_output_tokens']):.0f}",
        "–" if cost_per_ticket is None else f"${cost_per_ticket:.5f}",
        f"{avg(lambda s: s['avg_latency_s']):.2f} s",
    ]


HEADER = ["Variante", "Modell", "Läufe", "gültig", "Kategorie", "Priorität", "Prio ±1",
          "unklar erkannt", "Notiz gefunden", "Quellen richtig", "Tokens in", "Tokens out",
          "Kosten/Ticket", "Zeit/Ticket"]


def build_table(datasets: list[dict]) -> str:
    """Markdown-Tabelle, die man direkt ins README kopieren kann."""
    lines = ["| " + " | ".join(HEADER) + " |", "|" + "---|" * len(HEADER)]
    lines += ["| " + " | ".join(row_for(d)) + " |" for d in datasets]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="llmopsdesk-compare", description="Auswertungen vergleichen")
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    parser.add_argument("--include-mock", action="store_true", help="auch Mock-Läufe zeigen")
    parser.add_argument("--output", type=Path, help="Tabelle zusätzlich in diese Datei schreiben")
    args = parser.parse_args(argv)

    datasets = load_latest(args.results, args.include_mock) if args.results.exists() else []
    if not datasets:
        print("Keine Auswertungen gefunden. Erst llmopsdesk-eval laufen lassen.")
        return 1
    table = build_table(datasets)
    print(table)
    if args.output:
        args.output.write_text(table + "\n", encoding="utf-8")
        print(f"\nGespeichert: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
