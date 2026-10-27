# REV-2026-10-27-configuracion-por-modulo-y-empresa-03: Sin validacion de cliente en el campo de porcentaje y suscripciones de valueChanges acumuladas

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-configuracion-por-modulo-y-empresa.md (v1)
**Spec reference:** AC-10, UI-02 (DDR: Guardar deshabilitado si el formulario es invalido)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
ModuleSettingsComponent no valida en cliente (el DDR indicaba 'cliente o servidor' y deshabilitar Guardar si es invalido); ademas `apply()` crea una suscripcion nueva a `form.valueChanges` por cada carga/guardado, sobre formularios descartados.

## Expected behavior
Errores de formato visibles antes de enviar y una sola suscripcion viva.

## Actual behavior
El texto invalido solo se detecta tras el PATCH (el servidor lo valida correctamente, por lo que no hay riesgo de datos). Las suscripciones viejas quedan atadas al DestroyRef hasta destruir el componente (fuga menor).

## Evidence
Lectura de module-settings.component.ts (apply, save). Deuda menor; no bloquea.
