# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-10: Quedan `text-muted` sin migrar en estados de carga y vacío

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md (v2)
**Spec reference:** AC-05 (no enumera estos textos; inconsistencia, no incumplimiento)
**Plan mode:** COMPACTO
**Suggested owner:** delivery-build

## Description
Los textos de «Cargando…», «Sin registros» y «N entradas» siguen con `text-muted`, mientras el resto de textos auxiliares pasó a `text-body-secondary`.

## Expected behavior
Textos auxiliares con el mismo color secundario y contraste medido.

## Actual behavior
`text-muted` en `entry-list.component.html` (cargando, «sin registros», «N entradas») y `entry-detail.component.html` (cargando); contraste no medido (el pie de tabla midió 4,59:1).

## Evidence
`grep text-muted` en `frontend/panel_admin/src/app/features/accounting` (Quality Gate, 3.ª pasada).
