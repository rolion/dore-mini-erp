# REV-2026-11-04-refinar-ux-pacientes-odontologia-03: HTML/ARIA no válido en datos personales y pestañas del registro

**Status:** Resolved (corregido en el commit siguiente al Quality Gate; verificado con pruebas propias, pendiente de re-revisión independiente)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-refinar-ux-pacientes-odontologia.md (v1)
**Spec reference:** Non-functional requirements (accesibilidad mínima, §7 del sistema de diseño); AC-24
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
(1) En la lectura de Datos personales hay un <div> con solo un badge y un <p> como hijos directos de <dl>. (2) Las pestañas del registro de cambios usan role="tablist"/"tab" y aria-selected, pero no hay role="tabpanel", aria-controls ni navegación con flechas.

## Expected behavior
<dl> solo con grupos dt/dd (o div que los envuelvan); patrón de pestañas completo (tabpanel + aria-controls) o sin roles ARIA de pestaña.

## Actual behavior
Estructura <dl> inválida (patient-detail.component.html:164-169 y :168) y tablist incompleto (:192-195, :196-200).

## Evidence
patient-detail.component.html:165 <div class="mb-3"><span class="badge ...">; :168 <p class="small text-warning-emphasis mb-0" role="status"> dentro de <dl>; :192 <ul class="nav nav-tabs mb-3" role="tablist"> sin tabpanel. Revisión estática; sin lector de pantalla.
