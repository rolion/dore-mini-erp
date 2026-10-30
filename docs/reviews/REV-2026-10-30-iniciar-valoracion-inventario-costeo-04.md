# REV-2026-10-30-iniciar-valoracion-inventario-costeo-04: El resumen muestra el valor tal como se escribió

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-iniciar-valoracion-inventario-costeo.md (v1)
**Spec reference:** AC-02, UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Revisión visual en navegador, paso «3. Confirmar».

## Expected behavior
Los importes del resumen se muestran con 2 decimales, como los devolverá el servidor («Bs 100.50»).

## Actual behavior
Al escribir `100.5` el resumen muestra «Bs 100.5» (y el total «Bs 138.49» sí está bien calculado); tras confirmar, la consulta muestra «Bs 100.50». No afecta lo guardado.

## Evidence
Resumen: «Valor total: Bs 100.5»; consulta posterior: «Bs 100.50».
