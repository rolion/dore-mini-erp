# REV-2026-11-18-adaptar-reportes-libro-partida-doble-02: Desviaciones del contrato API-01 no declaradas en el TASK

**Status:** Fixed (pendiente de re-verificación)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-18-adaptar-reportes-libro-partida-doble.md (v1)
**Spec reference:** API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El TASK declara tres desviaciones (snake_case, 403, saldos solo del libro), pero la respuesta además omite campos del contrato API-01 sin declararlo.

## Expected behavior
La respuesta incluye `accountingEnabled` y, por cuenta, `inflow` y `outflow` además de `opening/net/closing`; o el TASK declara y justifica su omisión.

## Actual behavior
`ledger_data` no emite `accountingEnabled` y cada cuenta trae solo account_id, name, opening, net, closing. El modelo del frontend (`LedgerAccountFlow`) tampoco los tiene. La sección «Desviaciones» del TASK no los menciona.

## Evidence
- backend/modules/reporting/api/serializers.py:38-54
- docs/tasks/TASK-adaptar-reportes-libro-partida-doble.md ## Implementación (Desviaciones)
- docs/plans/PLAN-2026-11-18-adaptar-reportes-libro-partida-doble.md API-01

## Resolución
Aceptado: se declara en `## Implementación` del TASK (sin `accountingEnabled` porque el módulo deshabilitado responde 403; por cuenta solo `opening/net/closing` porque entradas/salidas por cuenta no suman a los totales por asiento).
