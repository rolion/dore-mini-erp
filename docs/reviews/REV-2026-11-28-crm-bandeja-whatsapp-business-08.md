# REV-2026-11-28-crm-bandeja-whatsapp-business-08: La capa de infraestructura de CRM importa la capa API (`inbox_subscriber` → `inbox_views`)

**Status:** Open
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md (v1)
**Spec reference:** docs/architecture/ddd.md (dependencias domain ← application ← infrastructure/api; las vistas solo traducen HTTP); ADR-crm-bandeja-whatsapp-business
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`backend/modules/crm/infrastructure/inbox_subscriber.py::link_inbound` hace `from modules.crm.api.inbox_views import inbox_service` para armar el `InboxService`. El armado del servicio (composición de repositorios, adaptadores y `OpportunityService`) vive en el módulo de vistas y la infraestructura depende de la capa API (dependencia invertida). El propio TASK lo reconoce como deuda técnica pero no hay prueba de fronteras que lo cubra.

## Expected behavior
La composición del servicio vive en un módulo neutral (p. ej. `crm/infrastructure/inbox_factory.py`) que usan tanto las vistas como el suscriptor; infraestructura no importa `api`.

## Actual behavior
El suscriptor del worker carga las vistas DRF (y sus serializers) para autovincular; cualquier cambio en la API puede romper el autovínculo del worker.

## Evidence
`grep -n "inbox_views" backend/modules/crm/infrastructure/inbox_subscriber.py` → línea 11 `from modules.crm.api.inbox_views import inbox_service`; TASK, sección «Deuda técnica».
