# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-10: PLAN, TASK y cuerpo del PR conservan afirmaciones de v1 que contradicen el estado real

**Status:** Resolved
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v2)
**Spec reference:** PLAN v2 (Non-functional requirements, AC-03, Database/migrations); TASK ## Publicación; cuerpo del PR #89
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
Documentación incoherente con el estado real (hay migración `purchases/0009_payment_advances`, el pago sí contabiliza y los pagos anticipados son anticipos a proveedores):
1. PLAN v2, «Non-functional requirements»: «sin migraciones» (contradice «Database / migrations» v2 del mismo PLAN).
2. PLAN v2, AC-03: «Compras no postea al pagar» (contradice AC-11/AC-12 de v2).
3. TASK `## Publicación`: «Sin migraciones».
4. Cuerpo del PR #89: «Changes» dice «Sin migraciones» y luego lista la 0009; «Specification / Plan» dice «la implementación de v2 está pendiente (delivery-build)»; «Testing» cita solo los números de v1 (2052/1598); «Known limitations» dice «pago anticipado deja Proveedores deudor hasta recibir» (v1; en v2 es un anticipo a proveedores en Activo, y el propio ADR v2 lo reemplaza).
5. ADR de recepción, «Consecuencias»: «Sin migraciones» (v1; la migración la cubre el ADR de pagos §consecuencias, pero no hay nota cruzada).

## Expected behavior
Los artefactos describen un único estado: migración 0009 aditiva, pago contabilizado, anticipos a proveedores, implementación v2 hecha y verificaciones vigentes.

## Actual behavior
Textos de v1 sin actualizar en PLAN, TASK, ADR de recepción y PR.

## Evidence
```
$ grep -n "sin migraciones" -i docs/plans/PLAN-*reconocer-compras*.md docs/tasks/TASK-reconocer-compras*.md
PLAN: "`Decimal`, BOB sin conversión; una consulta extra por recepción para `find_automatic_entry`; sin migraciones."
TASK: "...Incluye ADR (reconocer al recibir)... Sin migraciones. Pendientes (v2): ..."
$ gh pr view 89 --json body -q .body
"- API: 409 ... Sin migraciones."  /  "la implementación de v2 está pendiente (delivery-build)."  /  "pago anticipado deja Proveedores deudor hasta recibir"
```

## Resolution
Resuelto: PLAN v2, ADR de recepción, TASK y cuerpo del PR actualizados (migración 0009, AC-03, cifras de pruebas, límite de pagos anticipados).
