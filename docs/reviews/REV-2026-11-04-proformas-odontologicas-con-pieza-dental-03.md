# REV-2026-11-04-proformas-odontologicas-con-pieza-dental-03: El formulario desborda horizontalmente la página en móvil

**Status:** Resolved (en esta rama; el mismo defecto existe en el formulario de Cotizaciones del PR #52)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-proformas-odontologicas-con-pieza-dental.md (v1)
**Spec reference:** AC-10, UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En un viewport de 390 px la página del formulario de proforma se hacía más ancha que la pantalla (`scrollWidth` 842 frente a `clientWidth` 390) y la barra superior fija se estiraba.

## Expected behavior
Sin desplazamiento horizontal de la página; la tabla de líneas se desplaza dentro de su contenedor `.table-responsive`.

## Actual behavior
El `<span class="visually-hidden">` de la cabecera «Quitar» tiene `position: absolute` y, sin un ancestro posicionado, su bloque contenedor es la ventana: escapa del `overflow` del contenedor y ensancha la página. Se comprobó ocultando `thead` (390) y añadiendo `position-relative` al contenedor (390).

## Evidence
Navegador integrado, 390×844, `/es/pocketbiz/dentistry/patients/<id>/proformas/nueva`: `scrollWidth` 842 → 390 tras añadir la clase `position-relative` a `div.table-responsive` en `dental-proforma-form.component.html` (corregido y verificado tras recargar). La misma marca existe en `features/quotations/pages/proforma-form.component.html` (PR #52), que no se modificó aquí; requiere la misma clase.
