# Image für die Web-Oberfläche von LLM OpsDesk.
# Bauen:   docker build -t llmopsdesk .
# Starten: docker compose up   (siehe docker-compose.yml)

# "slim" = abgespecktes Debian mit Python, deutlich kleiner als das volle Image
FROM python:3.14-slim

# Keine .pyc-Dateien schreiben (Dateisystem ist im Betrieb schreibgeschützt)
# und Ausgaben sofort ins Docker-Log statt gepuffert
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- Schritt 1: nur die Abhängigkeiten installieren ---------------------------------
# Docker baut in Schichten (Layern) und verwendet unveränderte Schichten wieder.
# pyproject.toml ändert sich selten, der Code oft. Darum zuerst nur pyproject.toml
# kopieren und mit einem leeren Platzhalter-Paket installieren: Diese teure Schicht
# (alle Pakete herunterladen) wird dann bei Code-Änderungen nicht neu gebaut.
COPY pyproject.toml ./
RUN mkdir -p src/llmopsdesk && touch src/llmopsdesk/__init__.py \
    && pip install . \
    && pip uninstall -y llmopsdesk

# --- Schritt 2: den eigentlichen Code installieren -----------------------------------
COPY src ./src
RUN pip install --no-deps . && rm -rf src build

# Daten, die das Programm zur Laufzeit liest
COPY kb ./kb
COPY evals ./evals

# --- Schritt 3: nicht als root laufen ------------------------------------------------
# Wird die App angegriffen, hat der Angreifer nur die Rechte dieses Benutzers.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/logs \
    && chown appuser:appuser /app/logs
USER appuser

EXPOSE 8000

# Docker prüft regelmäßig, ob die App antwortet (curl ist im slim-Image nicht enthalten)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# 0.0.0.0: im Container auf allen Schnittstellen lauschen, sonst ist die App von außen
# nicht erreichbar. Wer sie erreichen darf, regelt das Port-Mapping in docker-compose.yml.
CMD ["llmopsdesk-web", "--host", "0.0.0.0", "--port", "8000"]
