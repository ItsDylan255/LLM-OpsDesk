"""Retrieval: passende Notizen aus der Wissensbasis (kb/) zu einem Text finden.

Verfahren: BM25, eine klassische Stichwortsuche (so arbeiten auch viele Suchmaschinen).
Idee: Ein Wort zählt umso mehr, je seltener es in der Wissensbasis vorkommt
("ssh" ist aussagekräftiger als "server") und je öfter es in einer Notiz steht.

Zweisprachigkeit: Eine reine Stichwortsuche findet die englische Notiz "disk full" nicht,
wenn das Ticket "Festplatte voll" sagt. Lösung hier: Jede Notiz hat eine Zeile
"keywords:" mit Begriffen auf Deutsch UND Englisch. Das ist einfach, braucht keine
weitere Bibliothek und lässt sich messen (llmopsdesk-retrieval).
Alternative für später: Embeddings (Suche nach Bedeutung statt nach Wörtern).
"""

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DEFAULT_KB_DIR = Path(os.getenv("LLMOPSDESK_KB_DIR", "kb"))

# Häufige Wörter ohne Aussagekraft. Bewusst kurz gehalten.
STOPWORDS = set("""
der die das den dem des ein eine einen einem einer und oder aber nicht ist sind war
wird werden mit von für auf aus bei nach seit vor zu zum zur im in an am als auch es
ich mein meine wir uns sie er man kann können bitte noch nur so wie was dass da
the a an and or but not is are was were be been with of for on from at by to in as
it i my we our you can could please is this that there since after before
""".split())

# Kurze Fachbegriffe, die trotz weniger als 3 Buchstaben zählen sollen.
SHORT_TERMS = {"vpn", "dns", "ssh", "tls", "ssl", "ad", "ap", "ip", "ci", "nfs", "smb", "psu", "raid"}


@dataclass
class Document:
    id: str          # Dateiname ohne .md, wird als Quelle angegeben
    title: str
    keywords: str
    body: str

    @property
    def search_text(self) -> str:
        # Titel und Stichwörter doppelt: sie beschreiben die Notiz am besten.
        return f"{self.title} {self.title} {self.keywords} {self.keywords} {self.body}"


def tokenize(text: str) -> list[str]:
    """Text -> Liste von Wörtern in Kleinbuchstaben, ohne Füllwörter."""
    words = re.findall(r"[a-zäöüß0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS and (len(w) >= 3 or w in SHORT_TERMS)]


def load_documents(kb_dir: Path = DEFAULT_KB_DIR) -> list[Document]:
    """Liest alle .md-Dateien. Erwartetes Format: '# Titel', 'keywords: ...', danach Text."""
    docs = []
    for path in sorted(kb_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        title = lines[0].lstrip("# ").strip() if lines else path.stem
        keywords = ""
        body_lines = []
        for line in lines[1:]:
            if line.lower().startswith("keywords:") and not keywords:
                keywords = line.split(":", 1)[1].strip()
            else:
                body_lines.append(line)
        docs.append(Document(path.stem, title, keywords, "\n".join(body_lines).strip()))
    return docs


class BM25Retriever:
    # k1: wie stark wiederholte Wörter zählen; b: wie stark lange Notizen abgewertet werden.
    # Das sind die üblichen Standardwerte.
    k1 = 1.5
    b = 0.75

    def __init__(self, documents: list[Document], min_score: float = 0.0):
        self.documents = documents
        # Treffer unter dieser Schwelle werden verworfen: lieber keine Notiz als eine falsche.
        self.min_score = min_score
        self.doc_terms = [Counter(tokenize(d.search_text)) for d in documents]
        self.doc_lengths = [sum(c.values()) for c in self.doc_terms]
        self.avg_length = sum(self.doc_lengths) / len(documents) if documents else 0.0
        # In wie vielen Notizen kommt jedes Wort vor?
        self.doc_freq = Counter(term for counts in self.doc_terms for term in counts)

    def idf(self, term: str) -> float:
        """Seltene Wörter bekommen ein hohes Gewicht, häufige ein niedriges."""
        n = len(self.documents)
        df = self.doc_freq.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def score(self, query_terms: list[str], index: int) -> float:
        counts = self.doc_terms[index]
        length_factor = self.k1 * (1 - self.b + self.b * self.doc_lengths[index] / self.avg_length)
        total = 0.0
        for term in set(query_terms):
            tf = counts.get(term, 0)
            if tf:
                total += self.idf(term) * tf * (self.k1 + 1) / (tf + length_factor)
        return total

    def search(self, query: str, top_k: int = 3) -> list[tuple[Document, float]]:
        """Die besten Notizen mit ihrer Punktzahl, beste zuerst."""
        terms = tokenize(query)
        scored = [(doc, self.score(terms, i)) for i, doc in enumerate(self.documents)]
        scored = [(doc, s) for doc, s in scored if s > self.min_score]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]


# Schwelle aus der Messung mit llmopsdesk-retrieval (siehe README, Abschnitt Retrieval).
DEFAULT_MIN_SCORE = 6.0

_cache: dict[Path, BM25Retriever] = {}


def get_retriever(kb_dir: Path = DEFAULT_KB_DIR) -> BM25Retriever:
    """Lädt die Wissensbasis nur einmal pro Programmlauf."""
    if kb_dir not in _cache:
        _cache[kb_dir] = BM25Retriever(load_documents(kb_dir), min_score=DEFAULT_MIN_SCORE)
    return _cache[kb_dir]


def retrieval_report(cases: list[dict], retriever: BM25Retriever, top_k: int) -> dict:
    """Misst die Suche allein, ohne Sprachmodell (kostet also nichts).

    - hit_rate:   Anteil Tickets MIT passender Notiz, bei denen sie unter den Treffern ist
    - empty_rate: Anteil Tickets OHNE passende Notiz, bei denen die Suche nichts liefert
    """
    with_note, without_note, misses = [], [], []
    for case in cases:
        if "relevant_kb" not in case:
            continue
        found = [doc.id for doc, _ in retriever.search(case["text"], top_k)]
        if case["relevant_kb"]:
            ok = any(note in found for note in case["relevant_kb"])
            with_note.append(ok)
        else:
            ok = not found
            without_note.append(ok)
        if not ok:
            misses.append({"id": case["id"], "expected": case["relevant_kb"], "found": found})
    return {
        "hit_rate": sum(with_note) / len(with_note) if with_note else 0.0,
        "empty_rate": sum(without_note) / len(without_note) if without_note else 0.0,
        "n_with_note": len(with_note),
        "n_without_note": len(without_note),
        "misses": misses,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="llmopsdesk-retrieval", description="Suche in der Wissensbasis messen")
    parser.add_argument("--cases", type=Path, default=Path("evals/tickets.jsonl"))
    parser.add_argument("--kb", type=Path, default=DEFAULT_KB_DIR)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-score", type=float, nargs="*", default=[DEFAULT_MIN_SCORE],
                        help="eine oder mehrere Schwellen zum Vergleichen, z. B. --min-score 0 3 6 9")
    args = parser.parse_args(argv)

    with args.cases.open(encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]
    documents = load_documents(args.kb)
    print(f"{len(documents)} Notizen, top_k={args.top_k}")
    for threshold in args.min_score:
        report = retrieval_report(cases, BM25Retriever(documents, min_score=threshold), args.top_k)
        print(f"\nSchwelle {threshold}: passende Notiz gefunden {report['hit_rate'] * 100:.0f} % "
              f"(n={report['n_with_note']}), richtig leer {report['empty_rate'] * 100:.0f} % "
              f"(n={report['n_without_note']})")
        for miss in report["misses"]:
            print(f"  daneben: {miss['id']} erwartet {miss['expected']}, gefunden {miss['found']}")
    return 0
