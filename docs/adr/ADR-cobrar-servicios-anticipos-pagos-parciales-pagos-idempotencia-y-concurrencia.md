# ADR-cobrar-servicios-anticipos-pagos-parciales-pagos-idempotencia-y-concurrencia: Pagos, imputaciones, idempotencia y concurrencia

**Estado:** Propuesto
**Task relacionado:** TASK-cobrar-servicios-anticipos-pagos-parciales
**Fecha:** 2026-11-04

## Contexto
Un doble envío no debe duplicar el ingreso y dos pagos simultáneos sobre un mismo saldo no pueden sumar más que el saldo. COT-002 ya resolvió idempotencia con clave de cliente + hash (`quotations/application/proformas.py:140-181`) y bloqueo de cabecera.

## Decisión
1. **Tablas** (sin FK a otros módulos; `company_id` indexado): `receivables_obligation` (único `(company_id, source_kind, source_number)`; snapshot de `customer_id`/`customer_name`), `receivables_payment` (monto, `payment_method`, fecha, referencia, `recorded_by`/nombre, número de comprobante `CB-NNNNNN` por empresa, `idempotency_key`, `payload_hash`, `created_at`; único `(company_id, idempotency_key)`; `CheckConstraint` monto > 0), `receivables_allocation` (pago, `lineage_id`, `line_id` de la versión al pagar, descripción congelada, monto > 0; `CheckConstraint`), `receivables_counter` (contador por empresa, bloqueado). Los pagos y las imputaciones **nunca se editan ni se borran**.
2. **Registrar pago** (`RegisterPayment`, una transacción `atomic`): (a) buscar por `(company_id, idempotency_key)`: igual hash → devolver el pago existente (200, `replayed=true`); otro hash → 409; (b) obtener o crear la obligación (`get_or_create` con captura de `IntegrityError`) y **bloquearla** `select_for_update`; (c) bloquear la proforma y leer el snapshot fresco mediante la fachada de la fuente; (d) construir el agregado con imputaciones previas y llamar a `obligation.register_payment(...)`, que valida: monto > 0 y con 2 decimales, método válido, fecha no futura, referencia ≤ 100, ≥ 1 imputación, sin líneas repetidas, cada línea aceptada y cobrable, `Σ imputaciones = monto`, imputación ≤ saldo de la línea (y por tanto ≤ saldo de la obligación); (e) guardar pago + imputaciones, numerar el comprobante y llamar `mark_lines_collected`.
3. **Orden de bloqueo fijo** obligación → proforma, para evitar interbloqueos; dos pagos concurrentes se serializan en la obligación y el segundo revalida contra el saldo ya descontado (el segundo recibe 400/409 «supera el saldo»).
4. **Clave de idempotencia obligatoria** (`idempotency_key` UUID generado por la pantalla al abrir el formulario y conservado en reintentos), como en COT-002.
5. **Saldo y estado de cobro** se derivan siempre (nunca se asignan): `pending`/`partial`/`paid` sobre el exigible vigente; una obligación sin líneas aceptadas es `pending` con exigible 0.
6. **Sin reversión ni anulación** de pagos en esta tarea (no existe flujo en el producto): la UI no ofrece corregir y la documentación lo declara límite conocido.

## Alternativas consideradas
- **Solo `UniqueConstraint` y reintento:** no cubre la suma concurrente sobre el saldo.
- **`SERIALIZABLE`/optimista con versión:** más complejidad que el bloqueo de fila ya usado en el repo.
- **Idempotencia por cabecera HTTP:** distinto del patrón existente; se mantiene el campo en el cuerpo.

## Estrategia de rollback / mitigación
Migración aditiva. Si el bloqueo causara contención, el ámbito del bloqueo es una sola obligación/proforma. Rollback: deshabilitar el módulo; datos conservados.

## Consecuencias
Un cobro erróneo no se puede corregir todavía. Los comprobantes son números correlativos de empresa; no hay impresión en esta tarea (solo referencia en pantalla).
