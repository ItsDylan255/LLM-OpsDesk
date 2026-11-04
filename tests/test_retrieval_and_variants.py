import json

import pytest

from llmopsdesk import compare
from llmopsdesk.evaluation import DEFAULT_CASES, evaluate, load_cases, summarize
from llmopsdesk.providers.mock import DEFAULT_RESPONSE, MockProvider
from llmopsdesk.retrieval import BM25Retriever, Document, load_documents, retrieval_report, tokenize
from llmopsdesk.runner import run_task
from llmopsdesk.tasks import TASKS, get_task

DOCS = [
    Document("disk-full", "Festplatte voll / disk full", "festplatte, voll, disk, full, space", "df -h prüfen"),
    Document("vpn", "VPN geht nicht / VPN down", "vpn, tunnel, route", "Tunnelstatus prüfen"),
    Document("printer", "Drucker / printer", "drucker, printer, papierstau", "Klappen öffnen"),
]


def test_tokenize_drops_stopwords_and_keeps_short_terms():
    assert tokenize("Die VPN-Verbindung ist weg") == ["vpn", "verbindung", "weg"]


def test_search_finds_note_across_languages():
    retriever = BM25Retriever(DOCS)
    # Deutsches Ticket, Treffer über die zweisprachigen Stichwörter
    assert retriever.search("Die Festplatte ist voll", top_k=1)[0][0].id == "disk-full"
    assert retriever.search("no space left, disk is full", top_k=1)[0][0].id == "disk-full"


def test_min_score_returns_nothing_for_unrelated_text():
    retriever = BM25Retriever(DOCS, min_score=1.0)
    assert retriever.search("Bitte schnell beheben", top_k=3) == []


def test_load_documents_reads_title_and_keywords(tmp_path):
    (tmp_path / "note.md").write_text("# Titel\n\nkeywords: a, b\n\nText", encoding="utf-8")
    doc = load_documents(tmp_path)[0]
    assert (doc.id, doc.title, doc.keywords, doc.body) == ("note", "Titel", "a, b", "Text")


def test_every_expected_note_exists_in_kb():
    note_ids = {doc.id for doc in load_documents()}
    for case in load_cases(DEFAULT_CASES):
        for note in case["relevant_kb"]:
            assert note in note_ids, f"{case['id']} verweist auf fehlende Notiz {note}"


def test_retrieval_report_counts_hits_and_empty():
    cases = [
        {"id": "a", "text": "Festplatte voll", "relevant_kb": ["disk-full"]},
        {"id": "b", "text": "Bitte schnell beheben", "relevant_kb": []},
    ]
    report = retrieval_report(cases, BM25Retriever(DOCS, min_score=1.0), top_k=2)
    assert report["hit_rate"] == 1.0
    assert report["empty_rate"] == 1.0


def test_rag_variant_sends_notes_and_records_them():
    provider = MockProvider()
    result = run_task(get_task("ticket-v3"), "Die Festplatte ist voll", provider, BM25Retriever(DOCS))
    assert result.context_ids[0] == "disk-full"
    user = provider.calls[0]["user"]
    assert '<note id="disk-full">' in user
    assert user.index("<knowledge_base>") < user.index("<ticket>")


def test_variant_without_kb_sends_no_notes():
    provider = MockProvider()
    result = run_task(get_task("ticket-v1"), "Die Festplatte ist voll", provider, BM25Retriever(DOCS))
    assert result.context_ids == []
    assert "<knowledge_base>" not in provider.calls[0]["user"]


def test_v4_shortens_notes():
    long_doc = Document("long", "Lang", "festplatte", "x" * 5000)
    provider = MockProvider()
    run_task(get_task("ticket-v4"), "Festplatte", provider, BM25Retriever([long_doc]))
    assert "x" * 600 in provider.calls[0]["user"]
    assert "x" * 601 not in provider.calls[0]["user"]


@pytest.mark.parametrize("name", [n for n in TASKS])
def test_every_variant_builds_a_prompt(name):
    task = get_task(name)
    assert task.system_prompt
    assert "<ticket>" in task.build_user_prompt("Test", DOCS[:1])


def test_sources_metric_with_mock(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cited = json.loads(DEFAULT_RESPONSE) | {"sources": ["disk-full"]}
    cases = [{"id": "a", "lang": "de", "text": "Festplatte voll", "expected": {"category": "storage"},
              "relevant_kb": ["disk-full"]}]
    task = get_task("ticket-v3")
    # Statt der echten Wissensbasis bekommt der Runner unsere kleine Test-Wissensbasis.
    monkeypatch.setattr("llmopsdesk.runner.get_retriever", lambda: BM25Retriever(DOCS))
    summary = summarize(evaluate(task, cases, MockProvider([json.dumps(cited)])))
    assert summary["retrieval_hit"] == 1.0
    assert summary["sources_correct"] == 1.0


def test_compare_builds_table_from_saved_results(tmp_path):
    summary = {"valid_rate": 1.0, "accuracy": {"category": 0.5, "priority": 0.25, "needs_more_info": 1.0},
               "within_one": {"priority": 0.75}, "avg_input_tokens": 300, "avg_output_tokens": 80,
               "avg_latency_s": 1.5, "total_cost_usd": 0.003}
    data = {"meta": {"task": "ticket-v1", "provider": "claude", "model": "claude-haiku-5-5",
                     "n_cases": 30, "repeat": 1}, "summaries": [summary], "cases": []}
    (tmp_path / "20260101T000000Z_ticket-v1_claude.json").write_text(json.dumps(data), encoding="utf-8")

    table = compare.build_table(compare.load_latest(tmp_path, include_mock=False))
    assert "| ticket-v1 | claude-haiku-5-5 | 1 | 100 % | 50 % | 25 % | 75 % |" in table
    assert "$0.00010" in table  # 0.003 $ / 30 Tickets
