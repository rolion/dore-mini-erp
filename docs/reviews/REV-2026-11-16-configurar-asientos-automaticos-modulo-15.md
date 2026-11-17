# REV-2026-11-16-configurar-asientos-automaticos-modulo-15: El error 400 de una fila queda en el idioma anterior al cambiar de idioma

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v4)
**Spec reference:** AC-14
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ConfigRow.error` guarda el texto ya traducido en el momento del error (`problemText(...)` dentro de `save()`), a diferencia de `rowIssue(row)` y `issueText(issue)`, que se calculan en la plantilla y sí siguen al idioma.

## Expected behavior
Al cambiar el idioma con el panel abierto, el mensaje de error de la fila se vuelve a traducir (guardar `problem`/mensaje de respaldo y traducir al renderizar).

## Actual behavior
Con el panel abierto en español se provocó un 400 (cuenta deshabilitada en otra pestaña); al cambiar a inglés y luego a portugués el error siguió en español («La cuenta «Ingresos extra» está deshabilitada; elija otra o actívela en Cuentas.»). Tras recargar en inglés el mismo caso se mostró correctamente traducido («The account “Ingresos temporal 3” is disabled; choose another one or enable it in Accounts.»).

## Evidence
Navegador: /es/pocketbiz/sales/settings, error en la fila SALES_INCOME, selector de idioma de la cabecera (es -> en -> pt), `.text-danger` de la fila sin cambios. Código: `posting-config-panel.component.ts` `save()` -> `row.error = problemText(...)`.

## Resolution
`ConfigRow` guarda la causa del error (`errorProblem`) y el texto se arma al mostrarlo (`rowError`): cambiar de idioma con el panel abierto lo retraduce. Prueba añadida.
