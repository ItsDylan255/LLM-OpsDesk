"""Kommandozeile: llmopsdesk <datei> [--provider mock|claude] [--task ticket]"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from .metrics import log_run
from .providers import PROVIDER_NAMES, get_provider
from .runner import run_task
from .tasks import TASKS, get_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llmopsdesk", description="Text mit einem Sprachmodell analysieren")
    parser.add_argument("input_file", type=Path, help="Textdatei, z. B. ein Ticket")
    parser.add_argument("--task", choices=list(TASKS), default="ticket", help="welche Aufgabe (Standard: ticket)")
    parser.add_argument("--provider", choices=PROVIDER_NAMES, default="mock",
                        help="welches Modell (Standard: mock, kostet nichts)")
    parser.add_argument("--no-mask", action="store_true",
                        help="sensible Daten NICHT maskieren (nur für lokale Modelle sinnvoll)")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()  # liest .env, damit ANTHROPIC_API_KEY als Umgebungsvariable verfügbar ist
    # Windows nimmt bei umgeleiteter Ausgabe sonst eine alte Zeichenkodierung (ü wird zu �).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)

    input_text = args.input_file.read_text(encoding="utf-8")
    task = get_task(args.task)

    try:
        provider = get_provider(args.provider)
        result = run_task(task, input_text, provider, mask=not args.no_mask)
    except Exception as exc:  # oberste Ebene: verständliche Meldung statt langem Traceback
        print(f"Fehler beim Modellaufruf ({args.provider}): {exc}", file=sys.stderr)
        return 2

    log_run(result.calls, result.output is not None, task.name, task.prompt_version)

    if result.output is not None:
        print(result.output.model_dump_json(indent=2))
    else:
        print(f"Ungültige Modellantwort nach {len(result.calls)} Versuch(en): {result.error}", file=sys.stderr)

    for warning in result.warnings:
        print(f"WARNUNG: Die Antwort enthält einen gefährlichen Befehl ({warning}). Nicht blind ausführen!",
              file=sys.stderr)

    total_in = sum(c.input_tokens for c in result.calls)
    total_out = sum(c.output_tokens for c in result.calls)
    total_time = sum(c.latency_s for c in result.calls)
    print(
        f"\n[{result.calls[-1].model}] Aufrufe={len(result.calls)} "
        f"Tokens in={total_in} out={total_out} Zeit={total_time:.2f}s maskiert={result.masked_count}",
        file=sys.stderr,
    )
    return 0 if result.output is not None else 1


if __name__ == "__main__":
    sys.exit(main())
