# REV-2026-11-03-crear-proformas-de-servicios-06: Desviaciones del DDR y del design-system en las pantallas (revisión estática)

**Status:** Resolved (pendiente de re-verificación con PostgreSQL y revisión visual)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v1)
**Spec reference:** AC-11; UI-01..04; DDR-crear-proformas-de-servicios-pantallas-proformas; design-system.md §8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Revisión estática de las tres páginas (no se levantó la app: sin credenciales de BD, **no verificada visualmente**: móvil, escritorio, tema claro y oscuro).

## Expected behavior
Cumplir la checklist §8 («fechas `dd/MM/yyyy HH:mm`») y el DDR.

## Actual behavior
1. Fechas en ISO (`{{ p.date }}`, `{{ row.date }}`, `{{ version.date }}`, `valid_until`), sin `date: 'dd/MM/yyyy'`. Otros features sí usan el pipe `date`.
2. DDR: el formulario lleva «Presentar» (con diálogo); está implementado solo en el detalle.
3. DDR: los filtros de la lista van «en la URL». El estado vive solo en el formulario reactivo y se pierde al volver desde el detalle.
4. DDR: el componente `proforma-lines` no existe; la tabla va dentro del formulario. El TASK lo declara.
5. Sin aviso al abandonar con cambios sin guardar; solo el indicador (deuda declarada en el TASK).
6. El selector de servicios carga `pageSize: 100` activos, sin búsqueda; un catálogo con más de 100 servicios queda inalcanzable.
7. En el diálogo, Escape lo cierra mientras `saving` es verdadero (el botón «Volver» sí se bloquea).
8. Checklist: uso de `money` (lista y detalle), badges `col-*` y breadcrumb OK. El formulario muestra importes sin `money` (usa «Bs» en cabeceras; aceptable). Los estados cargando, vacío, error, éxito y el doble envío bloqueado están presentes.

## Evidence
`proforma-detail.component.html`: `<dd ...>{{ p.date }}</dd>`; `proforma-list.component.html`: `<td>{{ row.date }}</td>`. En `proforma-form.component.html` no hay botón «Presentar». `proforma-list.component.ts` no lee ni escribe `queryParams`. `ServicesApiService.list({ active: true, pageSize: 100 })`.
