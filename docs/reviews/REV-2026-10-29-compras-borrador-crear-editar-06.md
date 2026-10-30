# REV-2026-10-29-compras-borrador-crear-editar-06: detalles visuales menores en el formulario y la lista de compras

**Status:** Closed (verificado en el ciclo 3)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-compras-borrador-crear-editar.md (v1)
**Spec reference:** AC-13, AC-15, UI-02, UI-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Hallazgos de la revisión visual en el navegador (escritorio ≈1440 px, tablet ≈1024 px, móvil 375 px, tema claro y oscuro de la plantilla), sin impacto funcional:

1. En anchos medios (≈1024 px) el subtotal por línea y el total se parten en dos renglones («Bs» / «34.00») dentro del formulario.
2. Una línea con cantidad inválida (p. ej. 1.5 en un producto cuya unidad no admite fracciones) muestra igualmente su subtotal («Bs 6.75») y entra en el total mostrado, aunque no se pueda guardar.
3. En la lista de compras, la columna «Total» queda alineada a la izquierda (el `text-end` del `span` no alcanza a la celda).

## Expected behavior
1. Importes en una sola línea (`text-nowrap`).
2. El subtotal y el total solo cuentan líneas válidas (si la cantidad es inválida, el subtotal es «—»).
3. Importes alineados a la derecha, como en el detalle.

## Actual behavior
Ver Description.

## Evidence
Capturas del navegador integrado sobre una instancia local aislada (SQLite desechable): formulario con la línea «Cajas de cartón» cantidad 1.5 → mensaje «La cantidad debe ser un entero mayor a cero.» y subtotal «Bs 6.75», total «Bs 31.75»; con cantidad 2 → total «Bs 34.00» y guardado correcto («Compra guardada», detalle con proveedor, líneas, unidad y total).
