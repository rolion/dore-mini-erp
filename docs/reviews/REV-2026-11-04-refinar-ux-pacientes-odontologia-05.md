# REV-2026-11-04-refinar-ux-pacientes-odontologia-05: Huecos de prueba en el mapeo AC->verificacion (EDGE-01, EDGE-04, EDGE-06, AC-07, AC-12 parcial)

**Status:** Resolved (corregido en el commit siguiente al Quality Gate; verificado con pruebas propias, pendiente de re-revisión independiente)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-refinar-ux-pacientes-odontologia.md (v1)
**Spec reference:** Test Specification / Acceptance criteria mapping del PLAN; EDGE-01, EDGE-04, EDGE-06, AC-07
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El PLAN asigna pruebas a EDGE-01 (reintentar búsqueda), EDGE-04 (adulto con responsable guardado), EDGE-06 (409 al guardar por archivado externo) y AC-07 (etiqueta «Inactivo» por i18n / diálogo de teléfono duplicado), pero los specs de este PR no los ejercitan de forma explícita (AC-07 solo lo cubre i18n:check; el diálogo de teléfono duplicado pertenece al componente de alta rápida preexistente).

## Expected behavior
Una prueba por EDGE-01/04/06 que falle si se rompe el comportamiento.

## Actual behavior
grep en los specs de dentistry: no hay casos con status 409 en el guardado de la ficha, ni invocación de retryCustomers(), ni caso de fecha a adulto con responsable guardado.

## Evidence
patient-detail.component.spec.ts: solo status 400 (línea 74); patient-create.component.spec.ts: 409 solo en la creación (línea 82); sin referencias a retryCustomers ni 'Inactivo'. Comportamiento de EDGE-04 existe en patient-detail.component.ts:79-86 sin prueba directa.
