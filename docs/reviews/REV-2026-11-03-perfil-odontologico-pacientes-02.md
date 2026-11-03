# REV-2026-11-03-perfil-odontologico-pacientes-02: Reintento de búsqueda ausente en el alta

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-perfil-odontologico-pacientes.md (v1)
**Spec reference:** AC-08
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description

Reintento de búsqueda ausente en el alta en la revisión del refactor frontend.

## Expected behavior

Un error de búsqueda debía permitir repetir la consulta sin volver a escribir el término.

## Actual behavior

El modal mostraba la alerta sin acción de reintento.

## Evidence

El botón «Reintentar búsqueda» llama a `retryCustomers()`, que emite `this.lastSearch`. El error de búsqueda se conserva separado del error de alta. `TOTAL: 1084 SUCCESS`.
