import json

from llmopsdesk import evaluation
from llmopsdesk.evaluation import evaluate, load_cases, score_case, summarize
from llmopsdesk.providers.mock import MockProvider
from llmopsdesk.tasks import get_task
from llmopsdesk.tasks.ticket import TicketAnalysis

TICKET_TASK = get_task("ticket")

ORDER = {"priority": ["low", "medium", "high", "critical"]}


def make_output(category="network", priority="medium"):
    return TicketAnalysis(category=category, priority=priority, summary="x",
                          possible_causes=[], next_steps=[], sources=[])


def test_score_exact_and_within_one():
    expected = {"category": "network", "priority": "high", "needs_more_info": False}
    exact, within = score_case(expected, make_output(priority="medium"), ORDER)
    assert exact == {"category": True, "priority": False, "needs_more_info": True}
    assert within == {"priority": True}  # medium ist nur eine Stufe neben high


def test_score_two_steps_off_is_not_within_one():
    expected = {"priority": "critical"}
    _, within = score_case(expected, make_output(priority="medium"), ORDER)
    assert within == {"priority": False}


def test_invalid_output_scores_everything_wrong():
    exact, within = score_case({"category": "network", "priority": "low"}, None, ORDER)
    assert exact == {"category": False, "priority": False}
    assert within == {"priority": False}


def test_summary_with_mock(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # Log-Datei landet im Testordner
    cases = [
        {"id": "a", "lang": "de", "text": "x", "expected": {"category": "network", "priority": "medium"}},
        {"id": "b", "lang": "en", "text": "y", "expected": {"category": "storage", "priority": "high"}},
    ]
    summary = summarize(evaluate(TICKET_TASK, cases, MockProvider()))
    # Der Mock antwortet immer "network/medium": Fall a stimmt, Fall b nicht.
    assert summary["n"] == 2
    assert summary["valid_rate"] == 1.0
    assert summary["accuracy"]["category"] == 0.5
    assert summary["within_one"]["priority"] == 1.0
    assert summary["by_lang"]["de"]["accuracy"]["category"] == 1.0
    assert summary["by_lang"]["en"]["accuracy"]["category"] == 0.0
    assert summary["total_cost_usd"] == 0.0


def test_testset_is_complete_and_valid():
    cases = load_cases(evaluation.DEFAULT_CASES)
    assert len(cases) == 30
    assert len({c["id"] for c in cases}) == 30  # keine doppelten IDs
    for case in cases:
        # Jedes Label muss ein erlaubter Wert sein, sonst wäre der Testsatz selbst fehlerhaft.
        make_output(case["expected"]["category"], case["expected"]["priority"])
        assert case["lang"] in ("de", "en")


def test_main_runs_with_mock_and_saves(tmp_path, monkeypatch, capsys):
    cases_file = tmp_path / "cases.jsonl"
    cases_file.write_text(json.dumps(
        {"id": "a", "lang": "de", "text": "x", "expected": {"category": "network"}}) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert evaluation.main(["--cases", str(cases_file), "--repeat", "2"]) == 0
    saved = list((tmp_path / "evals" / "results").glob("*_mock.json"))
    assert len(saved) == 1
    data = json.loads(saved[0].read_text(encoding="utf-8"))
    assert len(data["summaries"]) == 2
    assert "Streuung" in capsys.readouterr().out
