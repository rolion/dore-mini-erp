"""Consultas del libro de asientos (CONT-11): listado filtrado y lectura de un asiento.

Sin Django: el repositorio entra por puerto.
"""
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from modules.accounting.domain.journal import JournalEntry, JournalEntryNotFound


@dataclass(frozen=True)
class JournalFilters:
    """Filtros del libro de asientos; todos opcionales."""
    date_from: date | None = None
    date_to: date | None = None
    account_id: UUID | None = None
    source: str | None = None
    origin_kind: str | None = None


class JournalReader(Protocol):
    """Puerto de lectura: asientos de una empresa."""

    def search(self, filters: JournalFilters): ...

    def get(self, entry_id: UUID) -> JournalEntry | None: ...


class ListJournalEntries:
    """Cabeceras de la empresa que cumplen los filtros, en el orden total estable del libro (INV-04)."""

    def __init__(self, journal: JournalReader):
        self.journal = journal

    def execute(self, filters: JournalFilters):
        return self.journal.search(filters)


class GetJournalEntry:
    def __init__(self, journal: JournalReader):
        self.journal = journal

    def execute(self, entry_id: UUID) -> JournalEntry:
        entry = self.journal.get(entry_id)
        if entry is None:
            raise JournalEntryNotFound(str(entry_id))
        return entry
