# ADR-confirmar-cancelar-compras-ciclo-de-vida-y-contrato: Estados, transiciones y contrato de confirmar/cancelar compras

**Estado:** Propuesto
**Task relacionado:** TASK-confirmar-cancelar-compras
**Fecha:** 2026-10-30

## Contexto
PB-COM-003 añade las primeras transiciones de `Purchase` (hoy solo `DRAFT`). Debe bloquear la edición al confirmar, permitir cancelar con motivo solo si no hay recepciones ni pagos, ser idempotente y no tocar inventario ni gastos. Recepciones y pagos de compras no existen todavía, pero el detalle ya debe mostrar sus estados y la cancelación debe respetarlos. Referencia: `Order.cancel` y `allowed_transitions` en Ventas (`ADR-ciclo-pedido-entrega-cobro-modelo-dominio`).

## Decisión
1. **Estados documentales** `PurchaseStatus`: `draft`, `confirmed`, `cancelled`. Transiciones solo por métodos del agregado: `Purchase.confirm(now)` (`draft → confirmed`) y `Purchase.cancel(reason, now)` (`draft|confirmed → cancelled`). `editable` sigue siendo «es borrador» (INV-09 de PB-COM-002), por lo que `PATCH` de una confirmada o cancelada ya responde 409.
2. **Reglas del dominio**: `confirm` exige ≥ 1 línea (error de campo `items`: «La compra necesita al menos un producto.») y que el estado sea `draft`; `cancel` exige motivo no vacío, recortado, ≤ 500 (error `reason`) y que **no** haya actividad: `reception_status != not_received` o `payment_status != unpaid` lanza `PurchaseCancellationBlocked`. Una cancelada no se confirma (`PurchaseInvalidTransition`).
3. **Idempotencia**: confirmar una confirmada y cancelar una cancelada **no lanzan error**: la capa de aplicación devuelve la compra sin cambios (ni nueva fecha ni nuevo motivo) y sin guardar. Repetir la acción no crea ni modifica ningún otro documento (la operación solo toca la fila de la compra).
4. **Regla entre agregados en aplicación**: `ConfirmPurchase` comprueba que el proveedor exista y esté **activo** (`_supplier_errors`, mismo mensaje `SUPPLIER_NOT_ACTIVE`) y junta ese error con el de `items` en un único `PurchaseValidationError`. No se re-valida el catálogo de los productos (se conserva el snapshot acordado).
5. **Concurrencia**: cada caso de uso lee con `select_for_update` dentro de `transaction.atomic` (como `UpdatePurchase`), de modo que dos clics simultáneos se serializan y el segundo resulta idempotente.
6. **Estados de recepción y pago (preparatorios)**: `reception_status` (`not_received`, `partial`, `received`) y `payment_status` (`unpaid`, `partial`, `paid`) son atributos del agregado, con inicial `not_received`/`unpaid`, que solo podrán mover las tasks de recepción y pago (métodos futuros del agregado). En esta task nada los modifica. Evita acoplar Compras con Inventario/Gastos ahora.
7. **Persistencia**: migración **`0003_purchase_lifecycle`** (aditiva) en `purchases_purchase`: `confirmed_at` (DateTime, null), `cancelled_at` (DateTime, null), `cancellation_reason` (Text, default `''`), `reception_status` (Char 20, default `not_received`), `payment_status` (Char 20, default `unpaid`). Las filas existentes quedan en `draft` con los valores iniciales. `status` conserva su columna (`max_length=20`).
8. **Contrato API** (aditivo; todos exigen `required_modules = ('purchases',)` y filtran por `company_id`):
   - `POST /api/purchases/{id}/confirm/` (sin cuerpo) → 200 con el detalle. 400 `{supplier_id:[…]}` y/o `{items:[…]}` si no cumple; 404 si no existe o es de otra empresa; 409 `{"detail": "Una compra cancelada no puede confirmarse."}`.
   - `POST /api/purchases/{id}/cancel/` con `{"reason": "<texto>"}` → 200 con el detalle. 400 `{reason:[…]}`; 404; 409 `{"detail": "No se puede cancelar: la compra ya tiene recepciones o pagos registrados."}`.
   - El **detalle** (`GET/PATCH /api/purchases/{id}/` y los dos anteriores) suma: `reference` (H-01 del TASK, `COM-XXXXXXXX`), `reception_status`, `payment_status`, `confirmed_at`, `cancelled_at`, `cancellation_reason` (`""` si no aplica) y `allowed_actions`: lista calculada por el agregado con valores de `edit`, `confirm`, `cancel` (`draft` → los tres; `confirmed` → `cancel` solo si no hay actividad; `cancelled` → vacía). Los botones «Registrar recepción/pago» no aparecen en `allowed_actions` hasta que existan sus endpoints.
   - La **lista** suma nada nuevo salvo que `status` puede ser `confirmed` o `cancelled`.
   - Cambios anteriores intactos: `editable`, `status`, `PATCH`, errores por línea.
9. **Sin efectos externos**: confirmar y cancelar no importan ni escriben en `inventory` ni `expenses`; una prueba cuenta `StockMovement`/`Expense` antes y después.

## Alternativas consideradas
- **Un solo `PATCH {status}`**: descartada, mezcla la edición con transiciones y dificulta validar cada regla; los endpoints de acción siguen el patrón de Pedidos.
- **409 al repetir confirmar/cancelar**: descartada, la historia pide que repetir no duplique; un 200 idempotente es más amable para dobles clics y reintentos de red. El estado se puede leer del cuerpo.
- **Calcular recepción/pago desde tablas de recepciones/pagos inexistentes**: descartada (especularía un modelo que pertenece a otras tasks). Atributos simples ahora; cuando existan, esas tasks los derivarán o actualizarán sin cambiar este contrato.
- **Numeración correlativa por empresa** para la referencia interna: descartada aquí (contador concurrente + migración + decisión de formato); se usa un código derivado del `id` y se deja la numeración para otra task.
- **Bloquear solo cantidades y precios al confirmar**: descartada; documento confirmado = solo lectura (H-05), más simple y auditable.
- **Cancelar solo desde borrador**: contradice la historia (cancelar confirmadas sin recepciones/pagos).

## Estrategia de rollback / mitigación
Migración aditiva con valores por defecto: `migrate purchases 0002` elimina las columnas (se pierden motivos/fechas de compras ya confirmadas/canceladas, aceptable antes de producción). Revertir el PR deja las compras en `draft`. Mitigación de datos: si una compra se confirmara por error, no hay «deshacer» (fuera de alcance); la cancelación es el camino. Las transiciones están cubiertas por pruebas de dominio, aplicación y API.

## Consecuencias
- `PurchaseStatus` y `Purchase` crecen; PB-COM recepción/pago deberán añadir métodos al agregado que muevan `reception_status`/`payment_status` y usar la regla de cancelación existente.
- La referencia interna es provisional y no es única garantizada (colisión de 8 hex improbable pero posible); la UI no la usa como clave.
- El frontend debe aceptar `confirmed` y `cancelled` en lista y detalle.
