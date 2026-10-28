# REV-2026-10-28-registrar-existencias-iniciales-10: El TASK conserva secciones «Review» y «Publicación» de la v1 que ya no describen el PR
**Status:** Resolved (secciones Review y Publicación del TASK reescritas para la v2)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v2)
**Spec reference:** docs/tasks/TASK-registrar-existencias-iniciales.md (secciones «Review» y «Publicación»); CLAUDE.md (flujo `delivery-*`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-publish

## Description
Tras el rebase v2, `docs/tasks/TASK-registrar-existencias-iniciales.md` mantiene, sin marcarlas como históricas, la sección «Review» (veredicto PASS con 746 tests, REV-07 como «requiere decidir») y la sección «Publicación», que dice textualmente que los cambios sensibles incluyen una «migración aditiva `inventory/0002`: tablas `inventory_stock_movement` e `inventory_stock_balance`» y cita el ADR v1 (reemplazado). En v2 no hay migración ni tablas propias. Quien apruebe el PR leería un riesgo de base de datos inexistente y un veredicto obsoleto. (La sección «Implementación» sí fue marcada como v1 histórica.)

## Expected behavior
«Review» y «Publicación» reflejan la v2 (sin migración; ADR vigente `...-apertura-sobre-libro-de-movimientos`; cifras actuales) o marcan lo anterior como histórico.

## Actual behavior
Texto de v1 presente como vigente. Además la etapa del TASK sigue en REVIEW (esperado hasta este Quality Gate).

## Evidence
`grep -n "inventory_stock_balance" docs/tasks/TASK-registrar-existencias-iniciales.md` -> línea 118 (sección «Publicación»: migración aditiva `inventory/0002`, tablas `inventory_stock_movement` e `inventory_stock_balance`); la sección «Review» (líneas ~104-111) describe 746 tests, PASS v1 y REV-07 pendiente.\|0002" docs/tasks/TASK-registrar-existencias-iniciales.md` → coincidencias en las secciones «Review» y «Publicación» (que describen la migración y las tablas de v1).
