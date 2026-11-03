# REV-2026-11-02-registrar-profesionales-y-especialidades-01: Guardar habilitado con formulario inválido

**Status:** Closed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-registrar-profesionales-y-especialidades.md (v3)
**Spec reference:** AC-07 / UI-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El botón Guardar omite la condición form.invalid que exige el sistema de diseño, sección 3, Botones.

## Expected behavior
Deshabilitar Guardar cuando el formulario es inválido, está cargando o guardando.

## Actual behavior
Solo está deshabilitado durante carga/guardado. submit() sí evita enviar datos inválidos; el impacto es consistencia visual, sin pérdida de integridad.

## Evidence
Comando ejecutado: `Get-Content frontend/panel_admin/src/app/features/personnel/pages/profile-form.component.html` (HEAD e91f7ee).

```html
<button type="submit" class="btn btn-primary" [disabled]="saving || loading">{{ saving ? 'Guardando…' : 'Guardar' }}</button>
```

Comando ejecutado: `Get-Content docs/design/design-system.md`.

```text
Al guardar se deshabilita el botón (`[disabled]="form.invalid || saving || loading"`).
```

## Resolution
Corregido en c471e4c: `[disabled]="form.invalid || saving || loading"`. Test existente ampliado verifica botón deshabilitado con campos inválidos y habilitado tras corregirlos. Logs finales: TOTAL: 34 SUCCESS; build producción y lint exit 0. Revisor comprobó diff e91f7ee..HEAD y evidencia; sin cambios de código por el revisor.
