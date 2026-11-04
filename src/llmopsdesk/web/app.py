"""Web-Oberfläche und JSON-API mit FastAPI.

Start:  llmopsdesk-web            (dann http://127.0.0.1:8000 im Browser öffnen)

Seiten:
- GET  /            Formular
- POST /analyze     Ergebnis als HTML
- GET  /metrics     Kennzahlen aus logs/metrics.csv und den gespeicherten Auswertungen
- GET  /kb/{id}     eine Notiz aus der Wissensbasis (für die Quellenangaben)
- POST /api/analyze dasselbe als JSON (für andere Programme)
- GET  /health      "läuft der Server?" (z. B. für Docker)

Sicherheit:
- Jinja2 mit autoescape: Alles vom Modell wird als TEXT angezeigt, nie als HTML.
  Schreibt das Modell <script>, sieht der Browser &lt;script&gt;.
- Content-Security-Policy: Der Browser lädt nur Dateien von diesem Server, kein fremdes JavaScript.
- Maximale Ticket-Länge, damit niemand riesige (teure) Texte schickt.
- Standardmäßig nur von diesem Rechner erreichbar (127.0.0.1), keine Anmeldung eingebaut.
"""

import argparse
import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

from .. import compare, metrics
from ..evaluation import RESULTS_DIR
from ..providers import PROVIDER_NAMES, get_provider
from ..retrieval import get_retriever
from ..runner import run_task
from ..tasks import TASKS, get_task
from .i18n import DEFAULT_LANGUAGE, LANGUAGES, TEXTS

load_dotenv()

MAX_TICKET_CHARS = 5000
HERE = Path(__file__).parent

app = FastAPI(title="LLM OpsDesk", version="0.1.0")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
# autoescape=True ist der wichtigste Schutz gegen XSS in dieser App.
templates = Jinja2Templates(env=Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=True))


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# --- Hilfsfunktionen -------------------------------------------------------------

def choose_language(request: Request) -> str:
    """Sprache aus ?lang=..., sonst aus dem Cookie, sonst Deutsch."""
    lang = request.query_params.get("lang") or request.cookies.get("lang")
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def claude_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def variant_names() -> list[str]:
    # "ticket" (die Standard-Variante) zuerst, danach v0 bis v5
    return ["ticket"] + [name for name in TASKS if name != "ticket"]


def render(request: Request, template: str, **context) -> HTMLResponse:
    lang = choose_language(request)
    context.update(t=TEXTS[lang], lang=lang, claude_available=claude_available(),
                   providers=PROVIDER_NAMES, variants=variant_names(),
                   # Sprachlinks: Ergebnisseiten (POST) kann man nicht neu laden, dann zur Startseite
                   lang_base=request.url.path if request.method == "GET" else "/")
    response = templates.TemplateResponse(request, template, context)
    if request.query_params.get("lang") in LANGUAGES:
        response.set_cookie("lang", lang, samesite="lax")  # Sprachwahl merken
    return response


def analyze(text: str, task_name: str, provider_name: str, mask: bool) -> dict:
    """Gemeinsamer Kern für HTML-Seite und JSON-API."""
    if task_name not in TASKS:
        raise HTTPException(422, f"Unbekannte Variante: {task_name}")
    if provider_name not in PROVIDER_NAMES:
        raise HTTPException(422, f"Unbekannter Provider: {provider_name}")

    task = get_task(task_name)
    try:
        result = run_task(task, text, get_provider(provider_name), mask=mask)
    except Exception as exc:  # z. B. kein API-Key, keine Verbindung: Seite soll trotzdem antworten
        return {"analysis": None, "error": str(exc), "call_failed": True}

    metrics.log_run(result.calls, result.output is not None, task.name, task.prompt_version)
    costs = [metrics.estimate_cost(c.model, c.input_tokens, c.output_tokens) for c in result.calls]
    return {
        "analysis": result.output.model_dump() if result.output is not None else None,
        "error": result.error,
        "call_failed": False,
        "warnings": result.warnings,
        "masked_count": result.masked_count,
        "context_ids": result.context_ids,
        "usage": {
            "model": result.calls[-1].model,
            "calls": len(result.calls),
            "input_tokens": sum(c.input_tokens for c in result.calls),
            "output_tokens": sum(c.output_tokens for c in result.calls),
            "latency_s": round(sum(c.latency_s for c in result.calls), 2),
            "cost_usd": None if None in costs else sum(costs),
        },
    }


# --- HTML-Seiten -----------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return render(request, "index.html", max_chars=MAX_TICKET_CHARS, default_provider="mock",
                  default_variant="ticket", ticket="")


@app.post("/analyze", response_class=HTMLResponse)
def analyze_form(
    request: Request,
    ticket: Annotated[str, Form(min_length=1, max_length=MAX_TICKET_CHARS)],
    provider: Annotated[str, Form()] = "mock",
    variant: Annotated[str, Form()] = "ticket",
    mask: Annotated[bool, Form()] = False,  # nicht angehakte Checkbox wird gar nicht gesendet
):
    data = analyze(ticket, variant, provider, mask)
    return render(request, "result.html", ticket=ticket, provider=provider, variant=variant,
                  mask=mask, **data)


@app.get("/metrics", response_class=HTMLResponse)
def metrics_page(request: Request):
    rows = metrics.summarize_calls(metrics.read_calls())
    datasets = compare.load_latest(RESULTS_DIR, include_mock=False) if RESULTS_DIR.exists() else []
    eval_rows = [compare.row_for(d) for d in datasets]
    return render(request, "metrics.html", rows=rows, eval_header=compare.HEADER, eval_rows=eval_rows)


@app.get("/kb/{note_id}", response_class=HTMLResponse)
def kb_note(request: Request, note_id: str):
    # Nur IDs, die es wirklich gibt: so kann niemand über den Pfad fremde Dateien lesen.
    documents = {doc.id: doc for doc in get_retriever().documents}
    if note_id not in documents:
        raise HTTPException(404, "Notiz nicht gefunden")
    return render(request, "note.html", note=documents[note_id])


# --- JSON-API --------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TICKET_CHARS)
    task: str = "ticket"
    provider: str = "mock"
    mask: bool = True


@app.post("/api/analyze")
def analyze_api(body: AnalyzeRequest) -> dict:
    return analyze(body.text, body.task, body.provider, body.mask)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(prog="llmopsdesk-web", description="Web-Oberfläche starten")
    # 127.0.0.1 = nur von diesem Rechner erreichbar. 0.0.0.0 nur im Container oder bewusst im Netz.
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
