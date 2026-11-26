# REV-2026-11-26-gestionar-recetas-produccion-02: Sin mensaje cuando el resultado se usa como ingrediente

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-gestionar-recetas-produccion.md (v1)
**Spec reference:** UI-03 / INV-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El formulario bloquea el envío si el producto resultante está como ingrediente, pero no muestra ningún mensaje ni existe la clave i18n.

## Expected behavior
Mensaje visible en la línea.

## Actual behavior
Envío bloqueado en silencio.

## Evidence
`RecipeFormComponent.hasLocalProblems` devuelve true y `save()` hace `return`.
