"""Puerto neutro de la configuración por defecto de una empresa (ADR-configuracion-contable-por-defecto-...).

Cada módulo dueño registra desde su `apps.py` una sección: `export(company_id, ctx)` lee su configuración de una
empresa y `apply(company_id, data, ctx)` la aplica a otra completando solo lo que falta (idempotente, por claves
naturales: nunca UUID). Este paquete no importa módulos de negocio; `accounts` y los comandos solo conocen este puerto.
"""
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from django.db import transaction

SNAPSHOT_PATH = Path(__file__).with_name('snapshot.json')
SNAPSHOT_VERSION = 1

# `ctx` es un diccionario compartido entre secciones de una misma ejecución: una sección publica ahí mapas
# nombre↔UUID de lo suyo (p. ej. `classification_ids`) para que la siguiente no importe a su dueño.
Export = Callable[[UUID, dict], dict]
Apply = Callable[[UUID, dict, dict], dict[str, int]]


class DefaultsError(Exception):
    """El snapshot es inválido o referencia algo inexistente; no se guarda nada."""


@dataclass(frozen=True)
class Section:
    key: str
    order: int
    export: Export
    apply: Apply


_sections: dict[str, Section] = {}


def register(key: str, *, order: int, export: Export, apply: Apply) -> None:
    _sections[key] = Section(key, order, export, apply)


def _ordered() -> list[Section]:
    return sorted(_sections.values(), key=lambda s: s.order)


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise DefaultsError(f'No se pudo leer el snapshot de configuración: {exc}') from None
    return _checked(data)


def _checked(data: object) -> dict:
    if not isinstance(data, dict) or data.get('version') != SNAPSHOT_VERSION:
        raise DefaultsError(f'El snapshot debe ser un objeto con version {SNAPSHOT_VERSION}.')
    return data


def export_all(company_id: UUID) -> dict:
    data: dict = {'version': SNAPSHOT_VERSION}
    ctx: dict = {}
    for section in _ordered():
        data[section.key] = section.export(company_id, ctx)
    return data


def apply_all(company_id: UUID, snapshot: dict | None = None, *, dry_run: bool = False,
              profile: str | None = None) -> dict[str, dict[str, int]]:
    """Aplica el snapshot a la empresa, todo o nada; con `dry_run` calcula el resultado y revierte.

    `profile` (p. ej. el tipo de empresa) llega a las secciones en `ctx['profile']`; una sección que lo entienda
    ajusta lo suyo y las demás lo ignoran. Sin perfil se aplica el snapshot tal cual.
    """
    data = _checked(snapshot) if snapshot is not None else load_snapshot()
    report: dict[str, dict[str, int]] = {}
    ctx: dict = {'profile': profile}
    with transaction.atomic():
        for section in _ordered():
            report[section.key] = section.apply(company_id, data.get(section.key) or {}, ctx)
        if dry_run:
            transaction.set_rollback(True)
    return report
