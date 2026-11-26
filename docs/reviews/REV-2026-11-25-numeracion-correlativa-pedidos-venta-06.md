# REV-2026-11-25-numeracion-correlativa-pedidos-venta-06: La descripción del PR y partes del TASK aún dicen que los cancelados heredados quedan sin número (PLAN v2 lo cambió)

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-25-numeracion-correlativa-pedidos-venta.md (v2)
**Spec reference:** AC-12 (v2)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-publish

## Description
El PLAN v2, el ADR, el DDR, el código (`0008`) y las pruebas son coherentes: los CANCELLED heredados con fecha dentro de un período se numeran. La descripción del PR #124 y dos pasajes del TASK no se actualizaron.

## Expected behavior
Toda la documentación y la descripción del PR dicen lo mismo que AC-12 v2: `0007` numera los confirmados y `0008` los cancelados heredados; solo quedan sin número los NEW y los de fecha fuera de todo período.

## Actual behavior
- PR #124 (`gh pr view 124`): línea de Migraciones menciona solo `0006` y `0007`; la lista de limitaciones afirma «Pedidos heredados cancelados o con fecha fuera de todo período quedan sin número»; «No realizado» y «Cambio sensible» solo nombran `0007`.
- `docs/tasks/TASK-numeracion-correlativa-pedidos-venta.md` línea 96 (Modelos y migraciones: solo `0006` y `0007`) y línea 130 (cambio sensible: «migraciones `0006` y `0007`»), sin `0008`.

## Evidence
- `gh pr view 124 --json body` y `grep -n -i "cancel\|0008" docs/tasks/TASK-numeracion-correlativa-pedidos-venta.md`.
- Impacto: un aprobador humano que lea el PR creería que los cancelados siguen sin número y no sabría que hay una migración de datos más que probar contra una copia de producción.

## Resolución
Pendiente: actualizar la descripción del PR y las líneas 96 y 130 del TASK (mencionar `0008` y que los cancelados heredados se numeran).

## Resolución
Resuelto: el TASK menciona ahora `0008` (implementación, no verificado y publicación) y la descripción del PR #124 se actualizó con `0008`, el cambio de AC-12 (PLAN v2) y las limitaciones vigentes.
