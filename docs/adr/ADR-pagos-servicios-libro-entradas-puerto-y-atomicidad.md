# ADR-pagos-servicios-libro-entradas-puerto-y-atomicidad: Integración de pagos de servicios con el libro

**Estado:** Propuesto
**Task relacionado:** TASK-pagos-servicios-libro-entradas
**Fecha:** 2026-11-14

## Contexto
Con `accounting` habilitado, cada pago de una proforma de servicios debe crear una entrada (`origin_kind='SERVICE'`) en la misma transacción (ADR del libro, decisiones 3, 4 y 8). Cobros ya tiene idempotencia por `idempotency_key` + huella y bloquea obligación → proforma. PB-ACC-003 fijó el patrón para Ventas.

## Decisión
1. **Puerto `PaymentLedger`** (`is_available()`, `record(kind, number, payment, actor)`) inyectado opcionalmente en `CollectionService` (`receivables/application/`), implementado por `PaymentLedgerAdapter` en `receivables/infrastructure/adapters.py` con `module_gate` (`accounting`) y `accounting.services`. Sin puerto o módulo deshabilitado no ocurre nada nuevo.
2. **Orden en `register_payment`:** replay (sin tocar el libro: el pago ya está) → bloquear obligación → replay → bloquear proforma → `Obligation.register_payment` → `add_payment` → `ledger.record` → `mark_collected`. Todo dentro del `atomic` de `_run`; cualquier excepción revierte pago, imputaciones, comprobante y entrada. La cuenta se bloquea al final (`record_entry`), después de obligación y proforma.
3. **Cuenta en el servidor:** `resolve_account(company, método)` al cobrar; `None` → `ObligationStateError` con código `payment_method_without_account` (409, mensaje: «Configura la cuenta destino del método en Contabilidad → Cuentas y Métodos de pago»). `EntryValidationError` → 409 `ledger_rejected`; `EntryConflict` → 409 `ledger_conflict`. `ObligationStateError` gana un `code` opcional que `Conflict` expone como `code` en la respuesta (compatible: sin código sigue igual).
4. **Datos de la entrada:** `origin_kind='SERVICE'`, `origin_id` = id del pago, `origin_document_ref` = número de proforma, `receipt_number` = CB-NNNNNN, `currency='BOB'`, monto total del pago (una entrada aunque haya varias imputaciones), fecha efectiva, método, usuario. Sin `reference` ni descripciones de tratamientos (no se filtran datos clínicos).
5. **Idempotencia:** se reutiliza la de Cobros sin cambios; el libro aporta una segunda barrera (`(empresa, SERVICE, pago)` único). Los reintentos tras un fallo contable no encuentran pago previo (transacción revertida) y producen una sola pareja.
6. **Dependencias:** `ALLOWED_DEPENDENCIES['receivables']` añade `accounting` (solo desde infraestructura, por `services`); `accounting` no importa `receivables`.
7. **Sin migraciones ni cambios de modelo.** Sin cambios de frontend (el mensaje del 409 ya se muestra).

## Alternativas consideradas
- **Señal/evento tras guardar:** pierde atomicidad; descartado.
- **Registrar la entrada antes del pago:** el id del pago y el CB se conocen después de `register_payment`; descartado.
- **Exigir `accounting` para poder cobrar:** rompería el comportamiento previo; descartado.

## Estrategia de rollback / mitigación
Sin migraciones: revertir = desplegar la versión anterior. Las entradas creadas permanecen en el libro (reversiones en PB-ACC-006). Deshabilitar `accounting` devuelve el comportamiento previo; los pagos hechos sin accounting no tienen entrada (cobertura del libro ya declarada).

## Consecuencias
- Con `accounting` habilitado, un método sin cuenta bloquea el cobro hasta configurarlo.
- Cobros depende de la fachada de Contabilidad; Contabilidad sigue sin conocer Cobros.
