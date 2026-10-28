# REV-2026-10-28-inventario-consultar-existencias-historial-02: Desviación del plan no documentada (métodos de repositorio no creados)

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-28-inventario-consultar-existencias-historial.md (v1)
**Spec reference:** Proposed solution (repositorio: `balances_by_pair()`, `has_history_in()`); Files/components affected (`domain/repositories.py`, `django/movement_repository.py`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan propone añadir `balances_by_pair()` y `has_history_in()` al repositorio. La implementación reutiliza `list_balances()` (sin filtro) y `products_with_history()` y no toca `domain/repositories.py` ni `movement_repository.py`. Funciona (AC-08 verificado), pero el TASK declara como desviaciones solo dos puntos y concluye «Ninguna otra».

## Expected behavior
Las desviaciones respecto al plan quedan registradas en el TASK (o el plan se ajusta).

## Actual behavior
La sección «Desviaciones» del TASK omite este cambio. Nota: `list_balances()` agrega todo el libro de la empresa aunque haya filtro de búsqueda (riesgo de rendimiento ya anotado en el plan).

## Evidence
`git diff origin/main...HEAD --stat` no incluye `domain/repositories.py` ni `infrastructure/django/movement_repository.py`; `stock_use_cases.py` usa `self.stock.list_balances()` y `self.stock.products_with_history(...)`.
