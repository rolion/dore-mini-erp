# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-03: El listado clínico arma conjuntos de IDs no acotados por el rango de fechas

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v1)
**Spec reference:** AC-01, NFR (sin N+1 / rendimiento del listado), Deuda técnica del TASK
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`EncounterQueries.listing` carga en memoria todos los `customer_id` con perfil odontológico (y los de la búsqueda) y, para `encounter_status`, todos los `appointment_id` de atenciones de esos pacientes de **toda la historia**, y los pasa como listas `IN (...)`/`NOT IN (...)` a Agenda. El TASK declara que el rango ≤31 días lo acota, pero esos conjuntos no dependen del rango.

## Expected behavior
El costo de la consulta debería depender del rango pedido (p. ej. limitar las atenciones por `appointment_id` de las citas del rango, o unir por rango de fechas), no del total histórico de pacientes/atenciones.

## Actual behavior
Con clínicas de miles de pacientes/atenciones, cada petición al listado construye listas de miles de UUID (`dental_customer_ids`, `exclude_ids`/`only_ids`). Funcional en el MVP; riesgo de degradación al crecer.

## Evidence
- `backend/modules/dentistry/application/encounters.py:141-166` (`dental_customer_ids`, `exclude_ids = list(encounters.values_list('appointment_id'...))`, `only_ids`).
- `backend/modules/agenda/services.py:70-83` (`customer_id__in=list(...)`, `exclude(pk__in=list(...))`).
- TASK, «Deuda técnica / notas»: reconocido como suficiente para MVP.
