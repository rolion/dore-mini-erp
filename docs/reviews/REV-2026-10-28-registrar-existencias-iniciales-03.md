# REV-2026-10-28-registrar-existencias-iniciales-03: huecos menores de prueba y de resumen
**Status:** Resolved (verificado por el Quality Gate, ciclo 3, 2026-10-28)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v1)
**Spec reference:** EDGE-06 (usuario no administrador -> 403), UI-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1. EDGE-06 exige 403 para no administrador; el comportamiento viene del permiso por defecto (`CompanyModulePermission` extiende `CompanyAdminPermission`) pero ninguna prueba de `inventory/tests/test_stock.py` lo ejercita (solo el módulo deshabilitado).
2. En el resumen de `stock-opening.component.html`, `@for (item of summaryLines; track item.name)` usa el nombre como clave: dos productos con el mismo nombre generan claves duplicadas (aviso NG0955 en desarrollo y renderizado ineficiente).

## Expected behavior
Prueba explícita de 403 para un miembro no administrador en `POST /api/stock/openings/` y `GET /api/stock/`; clave de `track` única (p. ej. `productId` o el índice).

## Actual behavior
Sin prueba de rol; `track item.name` no es único si hay nombres repetidos.

## Evidence
`grep -n "403" backend/modules/inventory/tests/test_stock.py` -> solo líneas 229-230 (módulo deshabilitado). Revisión de código del HTML del resumen.
