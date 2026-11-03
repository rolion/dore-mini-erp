# REV-2026-11-03-agendar-y-gestionar-citas-06: Truncado silencioso a 100 registros (profesionales y calendario)

**Status:** Verified
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** AC-09; AC-08 (paginación)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Selectores de profesional piden page_size 100 sin paginar y el calendario pide las citas del rango con page_size 100.

## Expected behavior
Más de 100 profesionales o citas en el rango no se omiten sin aviso.

## Actual behavior
Se descartan sin mensaje (improbable en un consultorio único, pero no avisa).

## Evidence
appointment-list.component.ts: personnel.list(... page_size: 100) y api.list({ ..., page_size: 100 }); appointment-form.component.ts igual.

## Resolución
`fetchAll` recorre todas las páginas de profesionales, servicios y citas del calendario; los clientes muestran «Se muestran N de M» cuando la búsqueda se trunca. Spec `fetch-all.spec.ts`.

## Verificación (Quality Gate 2)
Verificado en gate 2: fetchAll recorre next (fetch-all.ts, spec fetch-all.spec.ts); usado en profesionales, servicios y calendario; formulario muestra 'Se muestran N de M' para clientes.
