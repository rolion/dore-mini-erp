# REV-2026-11-13-crear-cuentas-mapear-metodos-pago-06: UI-05 (enlace desde Módulos) no implementado

**Status:** Resolved
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-13-crear-cuentas-mapear-metodos-pago.md (v1)
**Spec reference:** UI-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El 409 de habilitar ya muestra «Falta configurar antes de habilitar: …» con los métodos; no hay enlace a la pantalla. Declarado como desviación 5.

## Expected behavior
Añadir el enlace o aceptar la desviación (cambio de Specification: requiere aprobación).

## Actual behavior
Ver descripción.

## Evidence
Desviación 5 de `## Implementación`.

## Resolution (2026-11-13)
`ModulesApiError.code` y enlace «Ir a Cuentas y Métodos de pago» en el diálogo de módulos ante `incomplete_configuration`; specs.
