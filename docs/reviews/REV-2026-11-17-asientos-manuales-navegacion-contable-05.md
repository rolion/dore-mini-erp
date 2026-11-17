# REV-2026-11-17-asientos-manuales-navegacion-contable-05: Formulario y lista de Movimientos exigen desplazamiento horizontal en móvil

**Status:** Resolved
**Severity:** Medium
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-17-asientos-manuales-navegacion-contable.md (v1)
**Spec reference:** UI-02, UI-03; checklist §8 (móvil ≈390 px)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start (DDR) / delivery-build

## Description
En 375 px la tabla de líneas del formulario muestra solo la columna Cuenta; Debe, Haber y «Quitar» quedan fuera de pantalla dentro de la tabla con scroll horizontal. En la lista, Total, Usuario y Acciones también quedan a la derecha.

## Expected behavior
Poder cargar importes y ver el total de cada fila sin tener que descubrir un scroll horizontal; p. ej. apilar cada línea (cuenta arriba, Debe y Haber debajo) en pantallas estrechas.

## Actual behavior
Sin desbordamiento de la página (`scrollWidth` = 375), pero los campos de importe no son visibles al abrir el formulario; Totales y Diferencia se ven sin sus valores.

## Evidence
Navegador integrado con preset móvil 375x812 sobre `/accounting/journal/new` y `/accounting/journal`; capturas del formulario (columna Cuenta sola) y de la lista (solo Fecha y Descripción). El DDR no definía el comportamiento móvil de la tabla de líneas.

## Resolución
Corregido (2026-11-17): bajo 768 px cada línea del formulario se apila (cuenta arriba; Debe, Haber y «Quitar» debajo; Totales y Diferencia con rótulo) y se anula el `min-width: 800px` de la tabla del tema; verificado en el navegador a 375 px. La lista de Movimientos conserva su desplazamiento horizontal (patrón de la lista de Entradas), con Fecha y Descripción visibles.
