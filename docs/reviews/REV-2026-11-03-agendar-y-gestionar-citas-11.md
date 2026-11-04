# REV-2026-11-03-agendar-y-gestionar-citas-11: Tras el reintento por página inexistente el indicador «Cargando…» se apaga con la petición en curso

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** AC-09 (estados cargando/vacío/error/éxito)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En `AppointmentListComponent.search`, el manejador de error del 404 llama a `this.search(1)` dentro del `subscribe` de la petición original, que lleva `finalize(() => this.loading = false)`. El `finalize` externo se ejecuta después del callback de error, de modo que pisa el `loading = true` que acaba de poner la búsqueda de la página 1.

## Expected behavior
Mientras se carga la página 1 de reemplazo se muestra «Cargando…», se mantienen deshabilitados «Filtrar», «Limpiar filtros» y la paginación, y no aparece el mensaje de vacío.

## Actual behavior
Por revisión de código: durante esa segunda petición `loading` es `false`, así que (con `rows` vacío) puede verse un instante «Aún no hay citas registradas.» y los botones quedan habilitados. Se corrige solo al terminar la petición. Efecto visual breve; no se observó en el navegador porque la respuesta local es casi instantánea.

## Evidence
`frontend/panel_admin/src/app/features/agenda/pages/appointment-list.component.ts`, método `search`: `.pipe(takeUntilDestroyed(...), finalize(() => this.loading = false)).subscribe({ ..., error: failure => { if (failure.status === 404 && page > 1) this.search(1); ... } })`. El spec `goes back to the first page…` no comprueba `loading`.
