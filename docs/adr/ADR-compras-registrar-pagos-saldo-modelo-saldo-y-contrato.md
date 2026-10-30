# ADR-compras-registrar-pagos-saldo-modelo-saldo-y-contrato: Modelo de pago, cálculo del saldo, concurrencia y contrato API

**Estado:** Propuesto
**Task relacionado:** TASK-compras-registrar-pagos-saldo
**Fecha:** 2026-10-30

## Contexto
PB-COM-005 exige pagos parciales o completos con saldo y estado derivados de pagos confirmados y sobrepago bloqueado incluso con solicitudes simultáneas. `Purchase.payment_status` ya existe sin escritor; Recepciones (PB-COM-004) resolvió el mismo problema de «documento hijo inmutable + acumulado + bloqueo + idempotencia».

## Decisión
1. **Dominio** (`purchases/domain`): entidad `Payment` (id, purchase_id, amount `Decimal` > 0 con 2 decimales, `PaymentMethod`, payment_date, user_id, user_name, `PaymentRecordStatus` = `confirmed|voided`, created_at; referencia `PAG-` + 8 hex mayúsculos derivada del id). Enums propios del módulo (`PaymentMethod` con los códigos `CASH, QR, BANK_TRANSFER, CARD, OTHER`, no importados de otro módulo). Solo `confirmed` suma al saldo; no hay acción que produzca `voided` en esta task.
2. **Regla en el agregado:** `Purchase.register_payment(payment_id, amount, method, payment_date, today, paid_before, user_id, user_name) -> Payment`. Valida todo junto (errores por campo): compra `confirmed` (si no, `PurchaseNotPayable` → 409); monto positivo y ≤ 2 decimales y ≤ `MONEY_MAX` vía `shared.domain.money`; método válido; fecha obligatoria y no futura; `amount <= total − paid_before` (si no, error en `amount` con el saldo vigente). Tras validar recalcula `payment_status` (`unpaid`/`partial`/`paid`) y no cambia nada si algo falla. Propiedad `can_pay` (confirmada y saldo > 0) y `pay` en `allowed_actions`. `paid_before` lo lee quien llama bajo el bloqueo; el saldo es siempre derivado, no se persiste.
3. **Persistencia:** tabla `purchases_payment` (`id` UUID PK, `company_id` indexado, `purchase_id` UUID sin FK —igual que `purchases_receipt`—, `amount` decimal(12,2) con `CheckConstraint(amount > 0)`, `payment_method`, `payment_date`, `status`, `user_id`, `user_name`, `created_at`; índice `(company_id, purchase_id)`). Migración **`0006_payments`** por `makemigrations`, aditiva; `0001…0005` no se tocan. `DjangoPaymentRepository(company_id)` con `get`, `save` (inserción en savepoint; `IntegrityError` → `PaymentConflict`), `list_for_purchase` y `paid_total(purchase_id)` (suma de `confirmed`).
4. **Caso de uso** `RegisterPayment` (`application/payment_commands.py`): `purchases.get(id, for_update=True)` → 404 si no existe; si `payment_id` ya existe de la misma compra devuelve ese pago (`created=False`), de otra → `PaymentConflict`; lee `paid_total` tras el bloqueo; `purchase.register_payment(...)`; guarda pago y compra (`payment_status`). Todo en la `transaction.atomic` de `_run`. Consultas `ListPayments` y el resumen de pagos dentro de `GetPurchase` (`paid_total`, `balance`).
5. **Concurrencia:** el bloqueo de fila de la compra (`select_for_update`) serializa los pagos de una misma compra; el acumulado se lee después del bloqueo, por lo que dos pagos simultáneos que juntos exceden el saldo → uno se registra y el otro falla con 400. No se agregan restricciones de BD adicionales sobre la suma.
6. **Contrato API** (aditivo): 
   - `POST /api/purchases/{id}/payments/` body `{payment_id, amount, payment_method, payment_date}` → 201 con el pago (`id`, `reference`, `amount`, `payment_method`, `payment_date`, `status`, `user`, `created_at`); 200 si es repetición; 400 por campo; 404; 409 compra no confirmada («Solo una compra confirmada admite pagos.») o `payment_conflict`.
   - `GET /api/purchases/{id}/payments/` lista paginada (fecha desc, creación desc).
   - `GET /api/purchases/{id}/` añade `paid_total`, `balance` (texto con 2 decimales) y `pay` en `allowed_actions`; `payment_status` ahora cambia. El resto del contrato no cambia.
   - Todas con `required_modules = ('purchases',)` y empresa del usuario autenticado.
7. **Sin integración:** pagar no llama a Inventario ni a Gastos y no crea movimientos ni gastos; no hay dependencia nueva entre módulos.

## Alternativas consideradas
1. **Saldo almacenado y actualizado con `F()`** en `purchases_purchase`: expone a deriva entre columna y pagos; descartada: se deriva de los pagos y solo se persiste el estado ya existente.
2. **Restricción en BD (trigger/exclusion) contra sobrepago**: complejidad y migración riesgosa; el bloqueo de fila ya cumple el requisito y es el patrón de Recepciones.
3. **Importar `Payment` de Ventas o de Gastos**: acopla módulos; se copian los códigos en Compras (patrón de `expenses/domain/enums.py`).
4. **Reutilizar `Receipt` genérico**: conceptos distintos; descartada.

## Estrategia de rollback / mitigación
Migración aditiva (tabla nueva). Rollback: `manage.py migrate purchases 0005`, tras devolver `payment_status` a `unpaid` en las compras con pagos (los datos de pagos se pierden: solo en entornos sin uso real). Mitigación: operación atómica; si falla nada se guarda; los pagos son inmutables y el saldo se recalcula siempre de ellos.

## Consecuencias
Compras gana un segundo documento hijo con el mismo patrón que Recepciones. La anulación/reembolso de pagos queda fuera y requerirá una acción que produzca `voided` y recalcule el estado. La referencia `PAG-` es provisional hasta una task de numeración. Las compras con total 0 no admiten pagos (H-09).
