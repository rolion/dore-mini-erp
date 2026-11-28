# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-02: Finalizar descarta en silencio observaciones sin guardar y no pide confirmación

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v1)
**Spec reference:** UI-02/UI-05; DDR (Finalizar: «confirmación breve»); INV-04 (no cerrar en silencio)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En el detalle de la atención, las observaciones se guardan con un botón aparte. «Finalizar» llama directamente a `POST …/finish/` y, al responder, `apply()` reemplaza el campo con el valor del servidor.

## Expected behavior
El DDR indica «Finalizar: `btn btn-success` con confirmación breve». Una acción terminal e irreversible no debería perder texto tecleado: guardar las observaciones pendientes antes de finalizar, o avisar/confirmar.

## Actual behavior
Si el odontólogo escribe observaciones y pulsa «Finalizar» sin «Guardar observaciones», el texto se pierde sin aviso y la atención queda de solo lectura. Tampoco hay confirmación previa a finalizar.

## Evidence
- `frontend/panel_admin/src/app/features/dentistry/pages/encounter-detail.component.ts:114-125` (`run('finish')` sin guardar ni confirmar) y `:99-104` (`apply` hace `observations.setValue(detail.encounter?.observations)`).
- `frontend/panel_admin/src/app/features/dentistry/pages/encounter-detail.component.html` (botón Finalizar con `(click)="run('finish')"`).
- `docs/design/DDR-gestionar-atencion-odontologica-desde-citas-listado-y-detalle-de-atencion.md` («Finalizar: … con confirmación breve»).

**Confirmado en la 2.ª pasada:** confirmFinish guarda las observaciones pendientes antes de finalizar y finalizar pide confirmación con diálogo; pruebas 'saves typed observations before finishing' y 'finishes directly when there is nothing unsaved'.
