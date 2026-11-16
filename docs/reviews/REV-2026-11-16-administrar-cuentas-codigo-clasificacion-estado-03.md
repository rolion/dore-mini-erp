# REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-03: Clave i18n sin uso

**Status:** Closed
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-administrar-cuentas-codigo-clasificacion-estado.md (v1)
**Spec reference:** N/A
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`ACCOUNTING.ACCOUNT_DIALOG.SIN_TIPO` quedó sin uso en es/en/pt (la lista ahora muestra «—»). `i18n:check` solo detecta claves faltantes.

## Expected behavior
Sin claves huérfanas.

## Actual behavior
Una clave sin uso por idioma. Sin efecto funcional.

## Evidence
Informe del Quality Gate, hallazgo 3.

## Resolution
Corregido: se eliminó `SIN_TIPO` de es/en/pt.
