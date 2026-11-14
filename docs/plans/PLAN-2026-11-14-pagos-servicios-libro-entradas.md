# PLAN-2026-11-14-pagos-servicios-libro-entradas (v1)

**Task:** TASK-pagos-servicios-libro-entradas · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno / ADR-pagos-servicios-libro-entradas-puerto-y-atomicidad

## Objective
Que cada pago de una proforma de servicios (Cobros), con `accounting` habilitado, cree una única entrada `SERVICE` en el libro por el monto recibido, en la misma transacción, reutilizando la idempotencia actual; sin cambios con `accounting` deshabilitado.

## Context
Ver TASK (hechos con `archivo:línea`) y ADR. Insumo: tarjeta PB-COB-002. Depende de PB-ACC-001/002 (en `main`); sigue el patrón de PB-ACC-003.

# Specification

## Domain context
`receivables` (agregado `Obligation`/`Payment`) consume `accounting` solo por su fachada `services`. Ventas, reversiones y regularización quedan fuera.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Entrada | Registro inmutable del dinero recibido por un pago | PB-ACC-002 |
| Comprobante CB | `CB-NNNNNN`, número del pago en Cobros | `receivables` |
| Cuenta destino | Cuenta que recibe el dinero del método | PB-ACC-001 |
| Fecha efectiva | `payment_date` del pago | Trello |

## Current behavior
Ver TASK: el pago no genera entrada.

## Expected behavior
Con `accounting` habilitado, `POST /api/receivables/commitments/<kind>/<number>/payments/` resuelve la cuenta del método en el servidor y guarda pago, imputaciones, comprobante, marca de líneas y entrada atómicamente; sin cuenta o con fallo contable responde 409 y no persiste nada. El replay idempotente devuelve el pago sin crear otra entrada. Crear, presentar, aceptar y versionar la proforma no crean entradas; cancelar no elimina pagos ni entradas. Con `accounting` deshabilitado el flujo es el actual.

## Domain rules / invariants
- INV-01 (existente) validaciones de línea aceptada, monto, método, fecha, imputaciones y saldo.
- INV-02 Con accounting habilitado, un pago existe si y solo si existe su entrada (`SERVICE`, `origin_id` = pago).
- INV-03 La entrada guarda la cuenta resuelta al cobrar, `BOB`, monto total, fecha efectiva, método, CB, número de proforma y usuario; no se recalcula.
- INV-04 (existente) misma clave y datos → mismo pago; otra huella → 409.
- INV-05 Un pago con varias imputaciones genera una sola entrada.
- INV-06 Sin reversiones.

## Acceptance criteria
- AC-01 Proforma aceptada de Bs 300: anticipo 100, abono 50 y final 150 → tres entradas (100, 50, 150), total 300, saldo 0, estado `paid`; aceptarla no crea entradas.
- AC-02 Pago distribuido entre dos tratamientos → un CB y una entrada por el monto total (cuenta de proforma `quotation` y `dental`).
- AC-03 Doble envío, replay tras pérdida de respuesta y envíos concurrentes con la misma clave → un pago, un CB, imputaciones únicas y una entrada (201 una vez, 200 en replay); misma clave con datos distintos → 409.
- AC-04 Pagos distintos concurrentes no superan el saldo; los válidos tienen su entrada.
- AC-05 Método sin mapeo, inactivo o con cuenta inactiva → 409 `payment_method_without_account`; no se crean pago, imputaciones, CB consumido ni entrada, ni cambia el saldo.
- AC-06 Fallo de `record_entry` (validación, conflicto, excepción) revierte todo; el reintento correcto produce una única pareja pago/entrada.
- AC-07 La entrada coincide con el pago: cuenta del mapeo vigente, moneda, fecha, método, CB, `origin_document_ref` = proforma, usuario; tras cambiar el mapeo, las entradas previas conservan su cuenta y la siguiente usa la nueva.
- AC-08 Empresa ajena no puede cobrar ni ve entradas ajenas en el libro; la entrada no contiene notas clínicas ni referencia libre.
- AC-09 Con `accounting` deshabilitado o nunca habilitado los pagos se registran como antes, sin cuenta ni entrada; con Ventas deshabilitado el cobro funciona y no crea ventas ni stock.
- AC-10 Recorrido proforma → pago → `GET /api/accounting/entries/`: la entrada aparece con origen `SERVICE`, `source.receipt_number` y totales correctos.

## Edge cases / Error cases
- EDGE-01 Replay de un pago anterior a habilitar accounting → 200 sin crear entrada.
- EDGE-02 Cancelar/rechazar proforma tras pagos: pagos y entradas permanecen.
- EDGE-03 Accounting habilitado y método `OTHER` sin mapeo → AC-05.

## Authorization / permissions
Sin cambios: `_authorize` de Cobros. `record_entry` no es endpoint ni exige permiso contable. Empresa desde el usuario autenticado.

## API contract
- API-01 `POST …/payments/`: request sin cambios; 201/200 como hoy; 409 gana `code` (`payment_method_without_account`, `ledger_rejected`, `ledger_conflict`) además de `detail`. Los 409 existentes no cambian de forma (sin `code`). Compatible hacia atrás.

## UI behavior
- UI-01 Sin cambios: el detalle del compromiso muestra `failure.message` del 409.

## Non-functional requirements
`Decimal`; una sola transacción; sin consulta a Contabilidad cuando está deshabilitado.

## Out of scope
Reversiones/reembolsos, Ventas, regularización de pagos previos, reporting, cambios de frontend.

# Test Specification

## Unit tests
- Aplicación con fakes (`CollectionService` + ledger falso): orden replay → pago → entrada; sin cuenta → conflicto con código; fallo propaga; ledger no disponible → sin llamada; replay no llama al ledger (AC-03, AC-05, AC-06, EDGE-01).

## Integration tests
- `receivables/tests/test_payment_ledger.py` (API, BD real, `TransactionTestCase`): AC-01…AC-10, incluyendo rollback con `record_entry` parcheado, cambio de mapeo, empresa B, accounting deshabilitado, Ventas deshabilitado.
- Concurrencia con hilos: mismo envío ×2 y dos pagos que exceden el saldo (AC-03, AC-04).
- `test_boundaries.py`: `receivables → accounting` permitido solo por `services` desde infraestructura.

## E2E
NO — cubierto por pruebas de API con BD real.

## Regression tests
Suites `receivables`, `accounting`, `sales`, `quotations`, `dentistry` y `reporting`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02, AC-07, AC-10 | API integración |
| AC-03, AC-04 | API integración + concurrencia |
| AC-05, AC-06 | Fakes + API integración |
| AC-08 | API integración (empresa B, campos de la entrada) |
| AC-09 | API integración + regresión receivables |

# Implementation Plan

## Architecture considerations
Ver ADR.

## Files/components affected
- Backend: `receivables/application/collections.py` (puerto `PaymentLedger` opcional, llamada tras `add_payment`), `receivables/domain/obligation.py` (`ObligationStateError.code`), `receivables/infrastructure/adapters.py` (`PaymentLedgerAdapter`), `receivables/api/views.py` (inyección, `code` en el 409), `sales/tests/test_boundaries.py` (dependencia permitida), tests nuevos.
- Docs: nota en `docs/architecture/ddd.md`.
- Migraciones y frontend: ninguno.

## Implementation steps
1. Dominio: `code` opcional en `ObligationStateError` (API-01).
2. Puerto + llamada en `register_payment` (INV-02, INV-05, AC-03).
3. Adaptador con `module_gate`, `resolve_account`, `record_entry` y traducción de errores (INV-03, AC-05, AC-06, AC-07).
4. Vista: inyección del adaptador y `code` en la respuesta 409.
5. Fronteras: permitir `receivables → accounting`.
6. Pruebas (unidad, integración, concurrencia, regresión) y suite completa.
7. Nota en `ddd.md`.

## Database / migrations
Ninguna.

## Risks
- Habilitar accounting bloquea cobros de métodos sin cuenta (mensaje accionable).
- Orden de bloqueos obligación → proforma → cuenta (verificado con la prueba de concurrencia).

## New dependencies
Ninguna.
