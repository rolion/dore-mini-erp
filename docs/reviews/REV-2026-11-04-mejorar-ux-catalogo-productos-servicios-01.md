# REV-2026-11-04-mejorar-ux-catalogo-productos-servicios-01: se elimina la regla móvil de la cabecera de Servicios

**Status:** Closed
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-ux-catalogo-productos-servicios.md (v1)
**Spec reference:** AC-07, Non-functional requirements (móvil ≈390 px)
**Plan mode:** COMPLETO
**Suggested owner:** frontend (delivery-build)

## Description
`service-list.component.scss` contenía una regla `@media (max-width: 575px) { .service-list-header { height:auto; min-height:70px; padding-block:10px } }` (añadida en el commit e3165ba «correct mobile filters»). El diff la reemplaza por solo `@use '../../../shared/styles/table-actions';`. El HTML sigue usando `class="ngxTableHeader service-list-header d-flex flex-wrap ..."` (service-list.component.html:9).

## Expected behavior
Cambiar los botones de acción no debe quitar la corrección móvil: en <576 px la cabecera con buscador, filtros y botón debe poder crecer en alto.

## Actual behavior
`.ngxTableHeader` tiene `height: 70px` fijo (src/assets/scss/override/_table.scss:252-256). Sin la regla, con `flex-wrap` en móvil el contenido puede desbordar los 70 px y solaparse con la tabla. No se pudo verificar visualmente (la app requiere backend con PostgreSQL).

## Evidence
```
git diff origin/main...HEAD -- .../service-list.component.scss
-@media (max-width: 575px) {
-  .service-list-header { height: auto; min-height: 70px; padding-block: 10px; }
-}
+@use '../../../shared/styles/table-actions';
```
Ningún spec cubre esta regla.

## Resolución
Regla móvil restaurada (se perdió al añadir el @use de table-actions). Verificado con build; revisión visual a 390 px pendiente de una persona.
