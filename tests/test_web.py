import json

import pytest
from fastapi.testclient import TestClient

from llmopsdesk import metrics
from llmopsdesk.providers.mock import DEFAULT_RESPONSE, MockProvider
from llmopsdesk.web import app as web


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Logs und Auswertungen landen im Testordner, nicht im Projekt.
    monkeypatch.setattr(metrics, "LOG_FILE", tmp_path / "metrics.csv")
    monkeypatch.setattr(web, "RESULTS_DIR", tmp_path / "results")
    return TestClient(web.app)


def use_mock_answer(monkeypatch, **changes):
    """Lässt den Mock eine bestimmte Antwort geben."""
    answer = json.dumps(json.loads(DEFAULT_RESPONSE) | changes)
    monkeypatch.setattr(web, "get_provider", lambda name: MockProvider([answer]))


def test_index_shows_form_with_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert '<form method="post" action="/analyze"' in response.text
    assert response.headers["content-security-policy"] == "default-src 'self'"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_analyze_shows_translated_result(client):
    response = client.post("/analyze", data={"ticket": "SSH hängt", "provider": "mock", "mask": "true"})
    assert response.status_code == 200
    assert "Kategorie: Netzwerk" in response.text


def test_language_switch_to_english_is_remembered(client):
    response = client.get("/?lang=en")
    assert "Analyze" in response.text
    assert response.cookies.get("lang") == "en"
    assert "Ticket text" in client.get("/").text  # Cookie wirkt beim nächsten Aufruf


def test_model_output_is_shown_as_text_not_html(client, monkeypatch):
    # Gibt das Modell HTML zurück, darf der Browser es nicht ausführen (XSS).
    use_mock_answer(monkeypatch, summary="<script>alert('xss')</script>")
    response = client.post("/analyze", data={"ticket": "Test", "provider": "mock"})
    assert "<script>alert" not in response.text
    assert "&lt;script&gt;alert" in response.text


def test_language_links_on_result_page_point_to_start_page(client):
    # /analyze geht nur per POST; ein Link "?lang=en" dorthin würde einen Fehler liefern.
    response = client.post("/analyze", data={"ticket": "Test", "provider": "mock"})
    assert 'href="/?lang=en"' in response.text


def test_dangerous_command_warning_is_shown(client, monkeypatch):
    use_mock_answer(monkeypatch, next_steps=["rm -rf / ausführen"])
    response = client.post("/analyze", data={"ticket": "Platte voll", "provider": "mock"})
    assert "gefährlichen Befehl" in response.text


def test_too_long_ticket_is_rejected(client):
    response = client.post("/analyze", data={"ticket": "x" * (web.MAX_TICKET_CHARS + 1), "provider": "mock"})
    assert response.status_code == 422


def test_unknown_variant_is_rejected(client):
    response = client.post("/analyze", data={"ticket": "x", "variant": "gibt-es-nicht"})
    assert response.status_code == 422


def test_failed_model_call_shows_error_page(client, monkeypatch):
    def broken_provider(name):
        raise RuntimeError("kein API-Key")
    monkeypatch.setattr(web, "get_provider", broken_provider)
    response = client.post("/analyze", data={"ticket": "x", "provider": "claude"})
    assert response.status_code == 200
    assert "kein API-Key" in response.text


def test_api_returns_json_and_logs_call(client, tmp_path):
    response = client.post("/api/analyze", json={"text": "SSH auf web01 hängt"})
    data = response.json()
    assert data["analysis"]["category"] == "network"
    assert data["masked_count"] == 1
    assert data["usage"]["calls"] == 1
    assert (tmp_path / "metrics.csv").exists()


def test_metrics_page_shows_logged_calls(client):
    assert "Noch keine Aufrufe" in client.get("/metrics").text
    client.post("/api/analyze", json={"text": "x"})
    page = client.get("/metrics").text
    assert "<td>mock</td>" in page


def test_kb_note_is_shown_and_unknown_ids_are_404(client):
    assert "dig +trace" in client.get("/kb/dns-resolution").text
    assert client.get("/kb/gibt-es-nicht").status_code == 404
    assert client.get("/kb/..%2F..%2Fpyproject").status_code == 404


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
