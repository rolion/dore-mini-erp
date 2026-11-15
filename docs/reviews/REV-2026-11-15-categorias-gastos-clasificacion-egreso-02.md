# REV-2026-11-15-categorias-gastos-clasificacion-egreso-02: La pestaña Egresos trunca silenciosamente a 100 categorías

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-categorias-gastos-clasificacion-egreso.md (v1)
**Spec reference:** AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`listCategories` pide `page_size=100` (máximo del servidor).

## Expected behavior
Listar todas las categorías activas o avisar si hay más.

## Actual behavior
Con más de 100 categorías activas las restantes no se pueden configurar y no hay aviso.

## Evidence
expense-config-api.service.ts (listCategories); backend/modules/expenses/api/pagination.py:11 (max_page_size = 100).
