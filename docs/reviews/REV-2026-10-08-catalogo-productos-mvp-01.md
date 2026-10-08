# REV-2026-10-08-catalogo-productos-mvp-01: Cambio de idioma por defecto fuera del alcance del plan v1

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-10-08-catalogo-productos-mvp.md (v1)
**Spec reference:** N/A (Non-functional: "Compatibilidad: sin cambios en rutas de demo"; la lista "Files/components affected" no incluye estos archivos)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-plan

## Description
El diff modifica `core/service/language.service.ts`, `app.config.ts` y agrega `language.service.spec.ts`: la aplicación arranca en español en lugar de tomar el idioma del navegador. Son archivos que el plan v1 no menciona y el cambio es global.

## Expected behavior
El plan v1 limita los archivos editados del frontend a `app.routes.ts`, `routes.json` e `i18n/*.json`.

## Actual behavior
El cambio fue pedido por el usuario después de la entrega y está documentado en `## Implementación` del TASK (sección "Ajustes posteriores"). No cambia la Specification ni viola ADR/DDR. El plan no fue actualizado.

## Evidence
`git diff origin/main...HEAD --stat` incluye `language.service.ts`, `language.service.spec.ts` y `app.config.ts`. Los 44 specs (incluido `language.service.spec.ts`) pasan.

## Required action
No bloquea el PR. En una próxima versión del plan, registrar el cambio en el changelog. No requiere retrabajo de código.
