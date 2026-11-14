# ADR-pagos-ventas-libro-entradas-integracion-e-idempotencia: Integración de pagos de Ventas con el libro y clave de idempotencia

**Estado:** Propuesto
**Task relacionado:** TASK-pagos-ventas-libro-entradas
**Fecha:** 2026-11-14

## Contexto
Con `accounting` habilitado, cada pago de un pedido debe crear exactamente una entrada del libro (ADR-libro-entradas-filtros-totales, decisiones 3, 4 y 8) en la misma transacción. Hoy el pago no tiene clave de idempotencia: un reintento crea otro pago, y la unicidad de la entrada por origen no lo evita porque el origen sería el nuevo pago. Ventas no puede importar infraestructura de `accounting`; solo su fachada `services`.

## Decisión
1. **Puerto `PaymentLedger`** en `sales/application/ports.py` (`is_available()`, `record(order, payment, actor)`), implementado por `PaymentLedgerAdapter` en `sales/infrastructure/adapters.py`, que usa `module_gate` (`accounting`) y `accounting.services` (`resolve_account`, `record_entry`). Con el módulo deshabilitado o sin puerto, el comando no hace nada nuevo.
2. **Orden dentro del comando `RegisterPayment`** (ya dentro del `atomic` de `_run`, con la fila del pedido bloqueada): idempotencia (replay) → `Order.register_payment` (validaciones existentes) → `repository.save` → `ledger.record`. Cualquier excepción deshace pedido, pago y entrada.
3. **La cuenta se resuelve en el servidor** con `resolve_account(company, método)` justo al cobrar y se pasa a `record_entry` (no se recalcula luego). Sin cuenta (método sin mapeo, inactivo o cuenta no compatible) → `OrderRuleViolation('payment_method_without_account', …)` → 409 con mensaje accionable («Configura la cuenta destino del método … en Contabilidad → Cuentas y Métodos de pago»). `EntryValidationError` → 409 `ledger_rejected`; `EntryConflict` → 409 `ledger_conflict`; ninguno persiste nada.
4. **Datos de la entrada:** `origin_kind='PRODUCT'`, `origin_id` = id del pago, `origin_document_ref` = id del pedido, `currency='BOB'`, `amount`, `payment_date` (fecha efectiva), método, usuario (id y nombre) y sin comprobante ni referencia libre del pago.
5. **Idempotencia del pago:** campo opcional `idempotency_key` (UUID) en el body de `POST /api/orders/<id>/payments/`. Nueva columna `PaymentModel.idempotency_key` (nullable) y huella `request_digest` (SHA-256 de monto, método, fecha y referencia normalizados), con `UniqueConstraint(order, idempotency_key)` condicionada a clave no nula. Si la clave ya existe en ese pedido: misma huella → se devuelve el pedido actual con **200** y no se crea nada (ni cuenta ni entrada, aunque el pedido ya esté saldado o cancelado); otra huella → 409 `idempotency_key_reused`. Se comprueba antes de validar saldo/estado, con el pedido ya bloqueado, de modo que un doble envío concurrente se serializa y el segundo ve el pago del primero. Sin clave, comportamiento actual.
6. **Dominio:** `Payment` gana `idempotency_key` y `request_digest` (opcionales); `Order.find_payment_by_key(key)` y `Order.register_payment(..., idempotency_key=None)`. Sin Django en el dominio.
7. **Frontend:** `OrderPaymentsComponent` genera la clave al abrir el formulario y la reutiliza en cada reintento hasta que el pago se confirma; el servicio la envía como `idempotency_key`. El 409 se muestra con el patrón de errores del detalle del pedido.
8. **Dependencias:** `ALLOWED_DEPENDENCIES['sales']` añade `accounting` (solo desde infraestructura, vía `services`); `accounting` sigue sin importar `sales`.

## Alternativas consideradas
- **Clave obligatoria** (como Cobros): rompería clientes y pruebas actuales y el «funcionamiento previo»; descartado (opcional, el frontend siempre la envía).
- **Evento/señal tras guardar el pago**: pierde la atomicidad exigida; descartado.
- **Idempotencia solo por unicidad de la entrada**: no evita dos pagos; descartado por la tarjeta.
- **Clave global por empresa** (índice sobre `company_id`): `PaymentModel` no tiene `company_id`; por pedido basta, porque el replay se resuelve dentro del pedido bloqueado.

## Estrategia de rollback / mitigación
Migración aditiva (dos columnas nullable y un índice único parcial); revertir = desplegar la versión anterior (las columnas quedan sin uso) o `migrate sales 0002`. Las entradas creadas permanecen en el libro (no hay reversiones en esta entrega; ver PB-ACC-006). Con `accounting` deshabilitado nada cambia. Las entradas no se crean para pagos anteriores (cobertura del libro ya lo declara).

## Consecuencias
- Habilitar `accounting` convierte la falta de mapeo en un rechazo del cobro, con el mensaje que guía a configurarlo.
- Deshabilitar `accounting` más tarde deja pagos sin entrada (cobertura parcial, ya declarada en el libro).
- Cobros (PB-COB-002) seguirá el mismo contrato para `SERVICE`.
