# REV-2026-11-15-modularidad-corte-historicos-contabilidad-02

Status: Open
Severity: Low
Category: IMPLEMENTATION
Related plan: docs/plans/PLAN-2026-11-15-modularidad-corte-historicos-contabilidad.md
Spec reference: ADR/DDR de periodos sin cobertura; AC-07
Plan mode: COMPLETO
Suggested owner: delivery-build

## Description
Los huecos se calculan con granularidad de día local: si se deshabilita y se rehabilita el mismo día no se registra hueco (previous.ended_on < following.started_on es falso), y un hueco [from,to) marca como no cubierta también la mañana del día de deshabilitación.

## Expected behavior
Documentar la granularidad por día o registrar el hueco intradía; coherencia entre 'in_gap' y el instante real de la deshabilitación.

## Actual behavior
Una operación fechada en el mismo día de una desactivación breve se considera cubierta aunque Contabilidad estuviera deshabilitada en ese momento.

## Evidence
backend/modules/accounting/domain/coverage.py: gaps() y coverage_status(); DjangoCoverageRepository.periods() convierte a timezone.localtime(...).date(). La conversión usa la zona local (correcto), pero se pierde la hora. La limitación no figura en '## Implementación' del TASK.
