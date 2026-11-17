# REV-2026-11-16-motor-central-asientos-partida-doble-02: Capa application/journal.py del PLAN no implementada y no declarada como desviación

**Status:** Resolved (verificado en el segundo Quality Gate)
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-16-motor-central-asientos-partida-doble.md (v1)
**Spec reference:** PLAN > Architecture considerations y Files/components affected (application/journal.py); ADR
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El PLAN pide casos de uso en `application/journal.py` con puertos (cuentas, períodos, repositorio) probables con dobles; la fachada solo compone adaptadores.

## Expected behavior
Casos de uso en `application/journal.py` o desviación declarada en la sección Implementación del TASK.

## Actual behavior
La orquestación (validación de cuentas con bloqueo, idempotencia, rechazo del libro anterior, bloqueo del período, reversión) vive en `backend/modules/accounting/services.py:474-558`, sin capa application; el dominio sí queda sin Django. Las desviaciones declaradas en el TASK (1)-(4) no mencionan este cambio. Funcionalmente correcto y cubierto por pruebas de integración, pero rompe el patrón de ddd.md (servicios finos) y la fachada concentra lógica.

## Evidence
`ls backend/modules/accounting/application` -> coverage, fiscal_periods, regularization_summary, regularize, transition_diagnosis, use_cases (sin journal.py). `git diff origin/accounting...HEAD --stat` no incluye application/journal.py.
