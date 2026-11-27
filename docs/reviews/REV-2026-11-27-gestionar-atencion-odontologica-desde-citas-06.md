# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-06: Pantallas nuevas se apartan del DDR y del design-system (HEX repetidos, select nativo, sin spinner)

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v1)
**Spec reference:** DDR (filtros con ng-select, estado cargando con spinner); design-system §4 y §8 («No introduce HEX»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Diferencias entre lo implementado y lo diseñado/checklist:
1. `encounter-detail.component.scss` copia tres HEX del tema oscuro (`#16192a`, `#96a2b4`, `#fff`). El design-system §10 documenta esa repetición como deuda de Agenda; esta tarea la extiende a un componente nuevo (§8: «No introduce HEX»).
2. El DDR pide `ng-select` para el filtro de odontólogo; el listado usa `<select class="form-select">`.
3. El estado «cargando» es solo texto (`role="status"`), el DDR indica spinner.
4. La confirmación de cancelación usa `<dialog>` nativo (igual que Agenda; declarado en el TASK, aceptable) en lugar de `NgbModal` del DDR.

## Expected behavior
Seguir el DDR o actualizarlo, y reutilizar variables/parciales en vez de repetir HEX.

## Actual behavior
Ver arriba. Sin impacto funcional; accesibilidad básica correcta (labels asociados, `role=alert/status`, `aria-labelledby` en el diálogo, `aria-label` en el icono de inicio).

## Evidence
- `frontend/panel_admin/src/app/features/dentistry/pages/encounter-detail.component.scss:3-5`.
- `frontend/panel_admin/src/app/features/dentistry/pages/encounter-list.component.html` (`<select id="e-professional" class="form-select">`).
- `docs/design/design-system.md` §8 y §10.
