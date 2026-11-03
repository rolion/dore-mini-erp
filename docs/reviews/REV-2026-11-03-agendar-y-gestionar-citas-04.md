# REV-2026-11-03-agendar-y-gestionar-citas-04: ADR/DDR/PLAN no reflejan las desviaciones implementadas

**Status:** Fixed (pendiente de reverificación en el próximo Quality Gate)
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** ADR decisión 3 (search_customer_ids); DDR (NgbModal); TASK ## Implementación
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La búsqueda por cliente usa el snapshot customer_name con icontains y los diálogos son <dialog> nativos; ambas desviaciones están solo en el TASK, mientras ADR y DDR siguen en estado Propuesto con la decisión original. Consecuencia funcional: si se renombra un cliente, las citas antiguas no se encuentran por el nombre nuevo.

## Expected behavior
ADR/DDR actualizados (o desviación aceptada explícitamente) y limitación del snapshot en las consecuencias.

## Actual behavior
ADR dice «Para filtrar por nombre de cliente usa search_customer_ids»; el código filtra customer_name__icontains.

## Evidence
appointments_api.py: rows.filter(customer_name__icontains=...). docs/adr/ADR-agendar-...md decisión 3.

## Resolución
ADR y DDR actualizados con las desviaciones (`<dialog>`, búsqueda por snapshot) y la limitación del snapshot.
