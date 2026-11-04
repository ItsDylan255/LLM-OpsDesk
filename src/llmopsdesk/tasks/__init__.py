"""Verzeichnis aller Aufgaben. Neue Aufgabe = neue Datei + ein Eintrag in TASKS."""

from .base import Task
from .ticket import TICKET_TASK

TASKS: dict[str, Task] = {
    TICKET_TASK.name: TICKET_TASK,
}


def get_task(name: str) -> Task:
    if name not in TASKS:
        raise ValueError(f"Unbekannte Aufgabe: {name!r}. Erlaubt: {list(TASKS)}")
    return TASKS[name]


__all__ = ["TASKS", "Task", "get_task"]
