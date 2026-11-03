# Lógica de negocio en vistas y componente

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** CLAUDE.md (DDD / frontend)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

`backend/modules/agenda/api.py` calcula disponibilidad, valida solapamientos y gestiona el bloqueo sin capa `application/`. `AgendaComponent` concentra HTTP, modelos y fechas sin `services/` ni `models/`. Nota: el ADR/plan pudo aceptar esta estructura; delivery-build debe contrastarlo antes de reestructurar.

Origen: tercer Quality Gate independiente sobre `7d521eb`.
