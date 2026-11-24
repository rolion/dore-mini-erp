# REV-2026-11-23-pedido-pantalla-unica-creacion-12: Documentos desactualizados tras PLAN v4 (DDR, TASK, PR)

**Status:** Fixed
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-23-pedido-pantalla-unica-creacion.md (v4)
**Spec reference:** AC-14
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tras el commit c557ff45 (PLAN v4: «Pagado» y «Saldo» en los importes) tres artefactos siguen describiendo el estado anterior.

## Expected behavior
DDR, TASK y PR coherentes con el PLAN v4 / AC-14.

## Actual behavior
- `docs/design/DDR-pedido-pantalla-unica-creacion-detalle-pedido-en-curso.md:18` define los Importes como «Subtotal · Descuento · Total»; la implementación agrega Pagado y Saldo.
- `docs/tasks/TASK-pedido-pantalla-unica-creacion.md:91` (## Plan) dice «v2, COMPLETO»; el plan vigente es v4.
- La descripción del PR 118 lista «PLAN v3» en la sección Changes (Docs); en «Related plan» ya dice v4.

## Evidence
Lecturas de los tres archivos y `gh pr view 118`.

## Resolución
Pendiente. Solo documentación; no bloquea.
