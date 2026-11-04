from llmopsdesk.providers.mock import DEFAULT_RESPONSE, MockProvider
from llmopsdesk.runner import MAX_REPAIRS, extract_json, run_task
from llmopsdesk.tasks.ticket import TICKET_TASK


def test_valid_answer_needs_no_repair():
    provider = MockProvider()
    result = run_task(TICKET_TASK, "SSH hängt", provider)
    assert result.error is None
    assert result.output.category == "network"
    assert result.repairs_used == 0


def test_system_prompt_and_ticket_are_sent():
    provider = MockProvider()
    run_task(TICKET_TASK, "SSH hängt", provider)
    call = provider.calls[0]
    assert call["system"] == TICKET_TASK.system_prompt
    assert "<ticket>\nSSH hängt\n</ticket>" in call["user"]


def test_invalid_then_valid_uses_one_repair():
    provider = MockProvider(responses=["das ist kein JSON", DEFAULT_RESPONSE])
    result = run_task(TICKET_TASK, "SSH hängt", provider)
    assert result.output is not None
    assert result.repairs_used == 1
    # Die Reparatur-Nachricht enthält die kaputte Antwort, damit das Modell sie korrigieren kann.
    assert "das ist kein JSON" in provider.calls[1]["user"]


def test_gives_up_after_max_repairs():
    provider = MockProvider(responses=["kaputt"])
    result = run_task(TICKET_TASK, "SSH hängt", provider)
    assert result.output is None
    assert result.error is not None
    assert len(result.calls) == 1 + MAX_REPAIRS


def test_schema_violation_triggers_repair():
    # Gültiges JSON, aber falscher Wert: auch das muss repariert werden.
    bad = DEFAULT_RESPONSE.replace('"network"', '"Netzwerk"')
    provider = MockProvider(responses=[bad, DEFAULT_RESPONSE])
    result = run_task(TICKET_TASK, "SSH hängt", provider)
    assert result.output is not None
    assert result.repairs_used == 1


def test_extract_json_ignores_surrounding_text():
    text = 'Hier ist die Analyse:\n{"a": 1}\nViel Erfolg!'
    assert extract_json(text) == '{"a": 1}'
