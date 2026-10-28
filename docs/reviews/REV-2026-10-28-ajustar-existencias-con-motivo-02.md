# REV-2026-10-28-ajustar-existencias-con-motivo-02: Clave de ajuste ya usada por otra empresa produce IntegrityError (500)

**Status:** Fixed (pendiente de verificación en el ciclo 2)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-28-ajustar-existencias-con-motivo.md (v1)
**Spec reference:** INV-08, INV-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El `id` del ajuste (clave de idempotencia del cliente) es la clave primaria global de `inventory_stock_adjustment`. `ConfirmAdjustment` busca la replica con `DjangoStockAdjustmentRepository(company_id).get(...)`, que filtra por empresa; si otra empresa ya uso ese UUID, la busqueda no lo ve y el `insert` choca con la PK. De forma analoga, la referencia `AJ-<8 hex>` es unica por empresa pero se deriva de solo 32 bits del id, y una colision tambien daria `IntegrityError`.

## Expected behavior
Ningun dato de otra empresa influye en la respuesta; una clave repetida debe dar un 4xx controlado (p. ej. 409 `adjustment_id_reused` o 400 en `adjustment_id`), no 500.

## Actual behavior
`IntegrityError` no capturada (500) en la segunda empresa; la transaccion se revierte, no hay corrupcion de datos. Probabilidad practicamente nula salvo que alguien reutilice a proposito un UUID.

## Evidence
Revision de codigo: `adjustment_repository.py:50-61` (`get`/`insert` con PK global y `company_id` solo en el filtro de lectura), `adjustment_use_cases.py:57-81`. No hay prueba que cubra el caso; no se reprodujo en ejecucion.
