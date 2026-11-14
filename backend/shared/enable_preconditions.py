"""Puerto neutro para exigir condiciones antes de habilitar un módulo en una empresa.

Quien dueñe la condición (p. ej. Contabilidad: mapeo de métodos completo) registra su verificador al arrancar;
`modularity` solo consulta este puerto, de modo que no importa módulos de negocio. Sin verificador no hay condición.
"""
from collections.abc import Callable
from uuid import UUID

# Devuelve los nombres de lo que falta (vacío = cumple).
Checker = Callable[[UUID], list[str]]

_checkers: dict[str, Checker] = {}


def register(module_key: str, checker: Checker) -> None:
    _checkers[module_key] = checker


def missing(company_id: UUID, module_key: str) -> list[str]:
    """Nombres de lo que falta para habilitar `module_key` en la empresa; vacío si no hay condición o se cumple."""
    checker = _checkers.get(module_key)
    return list(checker(company_id)) if checker else []
