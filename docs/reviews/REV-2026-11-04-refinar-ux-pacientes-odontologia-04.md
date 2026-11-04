# REV-2026-11-04-refinar-ux-pacientes-odontologia-04: Vacío de la lista: posible mensaje duplicado y «Todos» sin pacientes cuenta como filtro

**Status:** Resolved (corregido en el commit siguiente al Quality Gate; verificado con pruebas propias, pendiente de re-revisión independiente)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-refinar-ux-pacientes-odontologia.md (v1)
**Spec reference:** AC-11 (vacío sin pacientes vs. con filtros), UI-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La lista muestra un <p> propio para el vacío y además conserva el emptyMessage del ngx-datatable (messages.emptyMessage = «No hay pacientes que coincidan con los filtros.»). Además hasFilters considera filtro el estado «Todos» (active = ''), de modo que un tenant sin pacientes que elija «Todos» ve «No hay pacientes que coincidan…» en lugar de «Aún no hay pacientes…».

## Expected behavior
Un solo mensaje de vacío; «Aún no hay pacientes…» cuando la empresa no tiene ninguno (aun con estado Todos).

## Actual behavior
Con count === 0 coexisten el <p> y el mensaje interno del datatable (no verificado visualmente: no se pudo levantar la app). El caso «Todos» sin pacientes muestra el mensaje de filtros.

## Evidence
patient-list.component.html:23-26 (@if (!loading && !error && count === 0) <p>...) y :27 [messages]="messages"; patient-list.component.ts get messages() { emptyMessage: tr('DENTISTRY.PATIENT_LIST.NO_HAY_PACIENTES_QUE_COINCIDAN') } y get hasFilters() { ... || this.active.value !== 'true' }.
