# REV-2026-11-25-numeracion-correlativa-pedidos-venta-05: Ninguna prueba del backend comprueba que el 409 `fiscal_period_closed` envía `period`

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-numeracion-correlativa-pedidos-venta.md (v1)
**Spec reference:** API-02; UI-03; DDR-numeracion-correlativa-pedidos-venta-codigo-y-bloqueo («El período fiscal «{nombre}» está cerrado…»); resolución de REV-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La resolución de REV-04 hace que el aviso del frontend nombre el período cerrado a partir del campo `period` del 409. Ese campo lo emite el adaptador (`OrderNumberingAdapter.next_number`, `extra={'period': exc.name}`) y lo vuelca la vista (`sales/api/views.py:102`, `**exc.extra`), pero solo el spec de Karma (`orders-api.service.spec.ts`, con un cuerpo simulado) lo cubre; el contrato real del servidor no tiene prueba.

## Expected behavior
Una prueba de API del backend que fuerce el 409 `fiscal_period_closed` y afirme `response.json()['period'] == '<nombre del período>'`, de modo que un cambio de nombre o la pérdida del campo en el backend rompa una prueba y no solo degrade el aviso en silencio al texto genérico.

## Actual behavior
`test_start_in_a_closed_period_is_a_409` (`backend/modules/sales/tests/test_order_numbering.py`) afirma solo `status_code` y `code`. `grep -rn "'period'" backend/modules/sales --include=*.py` solo encuentra la línea del adaptador. Si el backend dejara de enviar `period`, todas las pruebas seguirían en verde y la UI mostraría el texto genérico.

## Evidence
- `grep -rn "'period'\|\"period\"" backend/modules/sales --include=*.py` devuelve únicamente `infrastructure/adapters.py:515`.
- Impacto bajo: el mensaje genérico sigue explicando el bloqueo; es un hueco de cobertura de contrato, no un defecto funcional (la lectura del código muestra que el campo sí se envía).

## Resolución
Resuelto: `test_start_in_a_closed_period_is_a_409` afirma además `response.json()['period'] == 'Gestión 2026'`. Se añadió después del Quality Gate ciclo 2 (cambio de una aserción en una prueba) y se verificó con una ejecución dirigida de `test_order_numbering`.
