# REV-2026-11-04-cobrar-servicios-anticipos-pagos-parciales-01: La fecha «hoy» del pago usa UTC en vez de la zona horaria configurada

**Status:** Resolved (corregido y verificado con prueba de integración el 2026-11-05)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-cobrar-servicios-anticipos-pagos-parciales.md (v1)
**Spec reference:** INV-03 (fecha no futura, por defecto hoy); CLAUDE.md (TIME_ZONE)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El caso de uso recibe `today` desde la vista como fecha UTC. El resto de módulos con fechas de pago (purchases, sales, inventory, customers) usan `timezone.localdate()`, que respeta `TIME_ZONE` (configurable en settings). El frontend repite el patrón con `new Date().toISOString().slice(0, 10)` (UTC) para el valor por defecto y el `max` del campo fecha.

## Expected behavior
"Hoy" es la fecha local según `TIME_ZONE` de la empresa: un pago registrado a las 21:00 locales en America/La_Paz (UTC-4) tiene fecha de ese día, y se rechaza una fecha de mañana local.

## Actual behavior
Con `TIME_ZONE` distinto de UTC, entre la medianoche UTC y la local, la fecha por defecto y la validación «no futura» usan el día siguiente: se puede registrar un pago fechado en el futuro local, y en zonas al este de UTC se rechaza el día de hoy local por la mañana. Los pagos quedan con fecha errónea (afecta orden y filtros por fecha futuros).

## Evidence
backend/modules/receivables/api/views.py:57 `today=lambda: datetime.now(timezone.utc).date()`
frontend/panel_admin/src/app/features/receivables/pages/commitment-detail.component.ts: `readonly today = new Date().toISOString().slice(0, 10);`
grep: purchases/api/payment_views.py:36 `today=timezone.localdate()`; sales/infrastructure/adapters.py:170 `return timezone.localdate()`.
Corrección sugerida: `django.utils.timezone.localdate` en la vista; en el front, fecha local (no ISO UTC).
