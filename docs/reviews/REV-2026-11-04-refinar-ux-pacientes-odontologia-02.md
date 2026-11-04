# REV-2026-11-04-refinar-ux-pacientes-odontologia-02: El error global «Guarda o cancela los cambios…» no se limpia al resolver las secciones

**Status:** Resolved (corregido en el commit siguiente al Quality Gate; verificado con pruebas propias, pendiente de re-revisión independiente)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-refinar-ux-pacientes-odontologia.md (v1)
**Spec reference:** AC-15 (bloqueo con cambios sin guardar), AC-17 (se eliminan banners globales de resultado)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
toggleActive() escribe el mensaje de bloqueo en this.error (banner global alert-danger). this.error solo se vuelve a limpiar en load() o tras confirmar un cambio de estado.

## Expected behavior
El aviso desaparece cuando el usuario guarda o cancela la sección pendiente (o se muestra junto al botón de archivar y se descarta solo).

## Actual behavior
Tras recibir el aviso, si el usuario guarda/cancela, el banner rojo sigue visible hasta recargar o volver a archivar. Los errores de archivar/reactivar también quedan en el banner global sin botón de descartar.

## Evidence
patient-detail.component.ts:152-153 (this.error = tr('...GUARDA_O_CANCELA_LOS_CAMBIOS'...); return;) y :161 (error: ... this.error = errorMessage(error)); cancelClinical()/cancelAdmin()/saveClinical()/saveAdmin() no tocan this.error. Hallazgo por lectura de código; no reproducido en navegador.
