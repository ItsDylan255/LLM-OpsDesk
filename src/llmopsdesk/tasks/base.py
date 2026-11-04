"""Was eine "Aufgabe" (Task) ist.

Eine Aufgabe beschreibt, WAS das Modell tun soll:
- system_prompt:      die Anweisungen an das Modell
- build_user_prompt:  macht aus dem Eingabetext (und ggf. Notizen) die Nachricht an das Modell
- output_model:       das Pydantic-Modell, gegen das die Antwort geprüft wird
- kb_top_k:           wie viele Notizen aus der Wissensbasis mitgeschickt werden (0 = keine)

Tickets analysieren ist die erste Aufgabe. Eine neue Aufgabe (z. B. Logdateien
zusammenfassen) ist einfach eine neue Datei in tasks/ plus ein Eintrag in
tasks/__init__.py. Provider, Runner und Metriken bleiben unverändert.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from pydantic import BaseModel

if TYPE_CHECKING:  # nur für die Typprüfung, verhindert einen Import-Kreis
    from ..retrieval import Document


@dataclass(frozen=True)  # frozen: eine Aufgabe wird nach dem Erstellen nicht mehr verändert
class Task:
    name: str
    prompt_version: str  # bei jeder Prompt-Änderung erhöhen, damit Messungen vergleichbar bleiben
    system_prompt: str
    build_user_prompt: Callable[[str, list["Document"]], str]
    output_model: type[BaseModel]
    max_tokens: int = 2000  # Obergrenze für die Antwortlänge (inklusive Nachdenken des Modells)
    kb_top_k: int = 0       # 0 = ohne Wissensbasis, sonst Anzahl mitgeschickter Notizen
    # Felder mit geordneten Werten, z. B. Priorität low < medium < high < critical.
    # Die Auswertung zählt dort zusätzlich "höchstens eine Stufe daneben".
    ordinal_fields: dict[str, list[str]] = field(default_factory=dict)
