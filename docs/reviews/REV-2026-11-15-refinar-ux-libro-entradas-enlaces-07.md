# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-07: En móvil la lista de Entradas no permite llegar al botón del detalle

**Status:** Resolved
**Severity:** High
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md (v2)
**Spec reference:** DDR-libro-entradas-filtros-totales (tabla apilada en móvil); preexistente, fuera del alcance de este task
**Plan mode:** COMPACTO
**Suggested owner:** delivery-start

## Description
En móvil la lista de Entradas no permite llegar al botón del detalle.

## Expected behavior
En ≈375 px la tabla se apila o se desplaza para llegar a todas las columnas y a la acción «Ver entrada».

## Actual behavior
El cuerpo de ngx-datatable mide 940 px en un contenedor de 233 px con overflow-x hidden y sin desplazamiento; el botón del ojo queda en x=982 (viewport 375). No se puede abrir un detalle desde la lista en móvil.

## Evidence
Medido en navegador (API simulada, 375x812): body [scrollWidth 940, clientWidth 233, overflow hidden], eyeLeft 982. No lo introduce este PR (`columnMode="flex"` ya estaba en origin/main).

## Resolution
Se activó `[scrollbarH]="true"` en la tabla de la lista: en 375 px el cuerpo se desplaza horizontalmente (940/295 px, overflow auto) y el botón del ojo queda alcanzable (x 277–307 tras desplazar; antes 922, fuera de pantalla). Escritorio sin cambios (sin desplazamiento, «Monto» 1180/1180). **Desviación del DDR original:** la tabla se desplaza, no se apila (un diseño apilado exige reemplazar `ngx-datatable` por una tabla propia; queda como mejora futura).
