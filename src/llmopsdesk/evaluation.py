"""Auswertung: einen Testsatz durch eine Aufgabe laufen lassen und Kennzahlen berechnen.

Aufruf:  llmopsdesk-eval --provider mock
         llmopsdesk-eval --provider claude --repeat 3

Kennzahlen (vorher festgelegt, damit man nicht nachträglich schönrechnet):
- valid_rate:      Anteil Antworten, die nach höchstens einer Reparatur gültig sind
- accuracy[feld]:  Anteil Tickets, bei denen das Feld exakt dem Label entspricht
- within_one[feld]: bei geordneten Feldern (Priorität): höchstens eine Stufe daneben
- Tokens, Kosten und Dauer pro Ticket
Alles wird zusätzlich getrennt nach Sprache (de/en) ausgegeben.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from .metrics import estimate_cost, log_call
from .providers import PROVIDER_NAMES, get_provider
from .providers.base import LLMProvider, LLMResponse
from .runner import run_task
from .tasks import TASKS, Task, get_task

DEFAULT_CASES = Path("evals/tickets.jsonl")
RESULTS_DIR = Path("evals/results")


@dataclass
class CaseResult:
    case_id: str
    lang: str
    output: BaseModel | None
    error: str | None
    exact: dict[str, bool]        # Feld -> stimmt exakt?
    within_one: dict[str, bool]   # geordnetes Feld -> höchstens eine Stufe daneben?
    calls: list[LLMResponse] = field(default_factory=list)


def load_cases(path: Path) -> list[dict]:
    """Liest eine JSONL-Datei: eine Zeile = ein Testfall als JSON-Objekt."""
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def score_case(expected: dict, output: BaseModel | None, ordinal_fields: dict[str, list[str]]):
    """Vergleicht die Antwort mit dem Label. Ungültige Antwort = alles falsch."""
    actual = output.model_dump() if output is not None else {}
    exact = {name: actual.get(name) == value for name, value in expected.items()}

    within_one = {}
    for name, order in ordinal_fields.items():
        if name not in expected:
            continue
        if actual.get(name) in order:
            distance = abs(order.index(actual[name]) - order.index(expected[name]))
            within_one[name] = distance <= 1
        else:
            within_one[name] = False
    return exact, within_one


def evaluate(task: Task, cases: list[dict], provider: LLMProvider, log: bool = True) -> list[CaseResult]:
    results = []
    for case in cases:
        run = run_task(task, case["text"], provider)
        exact, within_one = score_case(case["expected"], run.output, task.ordinal_fields)
        results.append(CaseResult(case["id"], case.get("lang", "?"), run.output, run.error,
                                  exact, within_one, run.calls))
        if log:
            last = len(run.calls) - 1
            for attempt, response in enumerate(run.calls):
                valid = attempt == last and run.output is not None
                log_call(response, task.name, task.prompt_version, attempt, valid)
    return results


def _rate(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(results: list[CaseResult]) -> dict:
    """Fasst die Ergebnisse zusammen: gesamt und je Sprache."""

    def block(subset: list[CaseResult]) -> dict:
        fields = sorted({name for r in subset for name in r.exact})
        ordinal = sorted({name for r in subset for name in r.within_one})
        return {
            "n": len(subset),
            "valid_rate": _rate([r.output is not None for r in subset]),
            "accuracy": {f: _rate([r.exact[f] for r in subset if f in r.exact]) for f in fields},
            "within_one": {f: _rate([r.within_one[f] for r in subset if f in r.within_one]) for f in ordinal},
        }

    all_calls = [c for r in results for c in r.calls]
    costs = [estimate_cost(c.model, c.input_tokens, c.output_tokens) for c in all_calls]
    n = len(results) or 1

    summary = block(results)
    summary["by_lang"] = {lang: block([r for r in results if r.lang == lang])
                          for lang in sorted({r.lang for r in results})}
    summary["repairs"] = sum(max(len(r.calls) - 1, 0) for r in results)
    summary["avg_input_tokens"] = sum(c.input_tokens for c in all_calls) / n
    summary["avg_output_tokens"] = sum(c.output_tokens for c in all_calls) / n
    summary["avg_latency_s"] = sum(c.latency_s for c in all_calls) / n
    # Kosten nur, wenn alle Modelle in der Preistabelle stehen, sonst lieber "unbekannt".
    summary["total_cost_usd"] = None if None in costs else sum(costs)
    return summary


def pct(x: float) -> str:
    return f"{x * 100:5.1f} %"


def format_summary(summary: dict) -> str:
    lines = [f"Tickets: {summary['n']}   gültig: {pct(summary['valid_rate'])}   Reparaturen: {summary['repairs']}"]
    for name, value in summary["accuracy"].items():
        lines.append(f"  {name:<16} exakt: {pct(value)}")
    for name, value in summary["within_one"].items():
        lines.append(f"  {name:<16} max. 1 Stufe daneben: {pct(value)}")
    for lang, sub in summary["by_lang"].items():
        parts = ", ".join(f"{name} {pct(v)}" for name, v in sub["accuracy"].items())
        lines.append(f"  [{lang}] n={sub['n']}: {parts}")
    cost = summary["total_cost_usd"]
    lines.append(
        f"  Tokens/Ticket: in {summary['avg_input_tokens']:.0f}, out {summary['avg_output_tokens']:.0f}   "
        f"Zeit/Ticket: {summary['avg_latency_s']:.2f} s   "
        f"Kosten gesamt: {'unbekannt' if cost is None else f'${cost:.4f}'}"
    )
    return "\n".join(lines)


def save_results(meta: dict, summaries: list[dict], runs: list[list[CaseResult]]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS_DIR / f"{stamp}_{meta['task']}_{meta['prompt_version']}_{meta['provider']}.json"
    details = [
        {"run": i, "id": r.case_id, "lang": r.lang, "exact": r.exact, "within_one": r.within_one,
         "error": r.error, "output": r.output.model_dump() if r.output is not None else None}
        for i, results in enumerate(runs) for r in results
    ]
    data = {"meta": meta, "summaries": summaries, "cases": details}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="llmopsdesk-eval", description="Testsatz auswerten")
    parser.add_argument("--task", choices=list(TASKS), default="ticket")
    parser.add_argument("--provider", choices=PROVIDER_NAMES, default="mock")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES, help="JSONL-Datei mit Testfällen")
    parser.add_argument("--repeat", type=int, default=1, help="Durchläufe (Modelle antworten nicht immer gleich)")
    parser.add_argument("--limit", type=int, default=None, help="nur die ersten N Fälle (zum Ausprobieren)")
    parser.add_argument("--no-save", action="store_true", help="Ergebnis nicht unter evals/results speichern")
    args = parser.parse_args(argv)

    task = get_task(args.task)
    cases = load_cases(args.cases)[: args.limit]
    provider = get_provider(args.provider)
    reviewed = sum(1 for c in cases if c.get("reviewed"))

    print(f"Aufgabe {task.name} (Prompt {task.prompt_version}), Provider {provider.name}, "
          f"{len(cases)} Fälle, davon von einem Menschen geprüft: {reviewed}")
    if reviewed < len(cases):
        print("  Hinweis: Nicht alle Labels sind geprüft, die Ergebnisse sind vorläufig.")

    runs, summaries = [], []
    for i in range(args.repeat):
        results = evaluate(task, cases, provider)
        summary = summarize(results)
        runs.append(results)
        summaries.append(summary)
        print(f"\nDurchlauf {i + 1}/{args.repeat}\n{format_summary(summary)}")

    if args.repeat > 1:
        print("\nStreuung über alle Durchläufe (min - max):")
        for name in summaries[0]["accuracy"]:
            values = [s["accuracy"][name] for s in summaries]
            print(f"  {name:<16} {min(values) * 100:.1f} % - {max(values) * 100:.1f} %")

    if not args.no_save:
        first_calls = [c for r in runs[0] for c in r.calls]
        meta = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "task": task.name, "prompt_version": task.prompt_version, "provider": provider.name,
            "model": first_calls[0].model if first_calls else "", "cases_file": str(args.cases),
            "n_cases": len(cases), "reviewed_cases": reviewed, "repeat": args.repeat,
        }
        print(f"\nGespeichert: {save_results(meta, summaries, runs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
