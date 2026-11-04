"""Führt eine Aufgabe mit einem Provider aus und prüft die Antwort.

Ablauf:
1. Falls die Aufgabe es verlangt: passende Notizen aus der Wissensbasis suchen (RAG)
2. Prompt bauen und Modell aufrufen
3. JSON aus der Antwort holen und mit Pydantic prüfen
4. Ist die Antwort ungültig: höchstens MAX_REPAIRS-mal mit der Fehlermeldung nachfragen
"""

import json
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from .providers.base import LLMProvider, LLMResponse
from .retrieval import BM25Retriever, get_retriever
from .tasks.base import Task

# Ein Reparaturversuch reicht meistens. Mehr Versuche kosten mehr Tokens und
# helfen selten, wenn das Modell es schon zweimal falsch gemacht hat.
MAX_REPAIRS = 1


@dataclass
class RunResult:
    output: BaseModel | None  # die geprüfte Antwort, oder None bei Misserfolg
    error: str | None         # Fehlermeldung des letzten Versuchs, oder None
    calls: list[LLMResponse] = field(default_factory=list)  # alle Modellaufrufe
    context_ids: list[str] = field(default_factory=list)    # mitgeschickte Notizen (RAG)

    @property
    def repairs_used(self) -> int:
        # Der erste Aufruf ist kein Reparaturversuch.
        return max(len(self.calls) - 1, 0)


def extract_json(text: str) -> str:
    """Holt das JSON-Objekt aus der Antwort, falls das Modell Text drumherum schreibt.

    Sucht vom ersten "{" bis zum letzten "}". re.DOTALL: "." passt auch auf Zeilenumbrüche.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def parse_output(text: str, output_model: type[BaseModel]) -> BaseModel:
    """Wirft json.JSONDecodeError oder ValidationError, wenn die Antwort ungültig ist."""
    data = json.loads(extract_json(text))
    return output_model.model_validate(data)


def build_repair_prompt(user_prompt: str, bad_answer: str, error: str) -> str:
    # Wir schicken die ursprüngliche Aufgabe noch einmal mit, plus die kaputte
    # Antwort und die Fehlermeldung. So weiß das Modell, was es korrigieren soll.
    return (
        f"{user_prompt}\n\n"
        f"Your previous answer was not valid:\n<previous_answer>\n{bad_answer}\n</previous_answer>\n"
        f"Error: {error}\n"
        "Reply again with ONLY the corrected JSON object."
    )


def run_task(
    task: Task, input_text: str, provider: LLMProvider, retriever: BM25Retriever | None = None
) -> RunResult:
    result = RunResult(output=None, error=None)

    documents = []
    if task.kb_top_k > 0:
        retriever = retriever or get_retriever()  # Tests können eine eigene Wissensbasis übergeben
        documents = [doc for doc, _score in retriever.search(input_text, task.kb_top_k)]
        result.context_ids = [doc.id for doc in documents]

    user_prompt = task.build_user_prompt(input_text, documents)

    prompt = user_prompt
    for _attempt in range(1 + MAX_REPAIRS):
        response = provider.complete(task.system_prompt, prompt, task.max_tokens)
        result.calls.append(response)
        try:
            result.output = parse_output(response.text, task.output_model)
            result.error = None
            return result
        except (json.JSONDecodeError, ValidationError) as exc:
            result.error = str(exc)
            prompt = build_repair_prompt(user_prompt, response.text, result.error)

    return result  # alle Versuche ungültig: output bleibt None, error ist gesetzt
