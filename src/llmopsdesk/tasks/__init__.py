"""Verzeichnis aller Aufgaben. Neue Aufgabe = neue Datei + Einträge in TASKS."""

from dataclasses import replace

from .base import Task
from .ticket import DEFAULT_VERSION, TICKET_VARIANTS

TASKS: dict[str, Task] = {task.name: task for task in TICKET_VARIANTS}

# "ticket" ist der bequeme Name für die aktuelle Standard-Variante.
TASKS["ticket"] = replace(TASKS[f"ticket-{DEFAULT_VERSION}"], name="ticket")


def get_task(name: str) -> Task:
    if name not in TASKS:
        raise ValueError(f"Unbekannte Aufgabe: {name!r}. Erlaubt: {list(TASKS)}")
    return TASKS[name]


__all__ = ["TASKS", "Task", "get_task"]
