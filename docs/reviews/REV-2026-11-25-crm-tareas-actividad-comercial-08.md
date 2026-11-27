# REV-2026-11-25-crm-tareas-actividad-comercial-08: El PR contra crm arrastra ~53 archivos ajenos (merge de PR 119 de main)

**Status:** Open (Low; aceptado, listado en Known limitations)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v1)
**Spec reference:** Plan: Files/components affected (alcance)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
origin/crm no contiene el PR 119 (cancelar ventas/devoluciones) pero la rama lo incluye por el merge 936c3a5e; el diff real del task es 936c3a5e..HEAD (51 archivos), mientras git diff origin/crm...HEAD muestra 104 (incluye sales, costing, reporting y docs de otro task).

## Expected behavior
El PR #123 (base crm) solo debe mostrar los cambios del task.

## Actual behavior
Un revisor humano vera cambios de backend/modules/sales, costing y reporting y docs/reviews de otro task, que no estan en el plan (riesgo de scope creep aparente). El contenido adicional no fue revisado aqui; sus pruebas (modules.customers modules.sales: 532 OK) pasan.

## Evidence
git log --oneline origin/crm..HEAD incluye 82a442fa Merge pull request #119 ...; git merge-base origin/crm HEAD = b09f12a3 = origin/crm. git diff origin/crm...HEAD --stat: 104 files changed; git diff 936c3a5e..HEAD --stat: 51 files changed.
