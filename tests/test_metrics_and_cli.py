import csv
import json

import pytest

from llmopsdesk import cli, metrics
from llmopsdesk.metrics import estimate_cost, log_call
from llmopsdesk.providers import get_provider
from llmopsdesk.providers.base import LLMResponse


def make_response(model="claude-haiku-5-5"):
    return LLMResponse(text="{}", input_tokens=1_000_000, output_tokens=1_000_000,
                       latency_s=1.234, model=model, provider="claude", stop_reason="end_turn")


def test_cost_for_known_model():
    # 1 Mio. Input + 1 Mio. Output = genau Input-Preis + Output-Preis
    price_in, price_out = metrics.PRICES_PER_MTOK["claude-haiku-5-5"]
    assert estimate_cost("claude-haiku-5-5", 1_000_000, 1_000_000) == pytest.approx(price_in + price_out)


def test_cost_for_unknown_model_is_none():
    assert estimate_cost("unbekannt", 10, 10) is None


def test_log_call_writes_header_once(tmp_path):
    # tmp_path: ein leerer Ordner, den pytest für jeden Test neu anlegt
    log_file = tmp_path / "logs" / "metrics.csv"
    log_call(make_response(), "ticket", "v1", attempt=0, valid=True, log_file=log_file)
    log_call(make_response(), "ticket", "v1", attempt=1, valid=False, log_file=log_file)

    rows = list(csv.DictReader(log_file.open(encoding="utf-8")))
    assert len(rows) == 2
    assert rows[0]["task"] == "ticket"
    assert rows[0]["latency_s"] == "1.23"
    assert rows[1]["valid"] == "False"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_provider("gibt-es-nicht")


def test_cli_with_mock_prints_valid_json(tmp_path, monkeypatch, capsys):
    # monkeypatch.chdir: der Test läuft im leeren Ordner, logs/ landet dort
    monkeypatch.chdir(tmp_path)
    ticket = tmp_path / "ticket.txt"
    ticket.write_text("SSH auf web01 hängt", encoding="utf-8")

    exit_code = cli.main([str(ticket), "--provider", "mock"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["category"] == "network"
    assert (tmp_path / "logs" / "metrics.csv").exists()
