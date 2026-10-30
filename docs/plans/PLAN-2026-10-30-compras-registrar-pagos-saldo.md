# PLAN-2026-10-30-compras-registrar-pagos-saldo (v1)

**Task:** TASK-compras-registrar-pagos-saldo · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR pestaña y diálogo de pago](../design/DDR-compras-registrar-pagos-saldo-pestana-y-dialogo-pago.md) · [ADR modelo, saldo y contrato](../adr/ADR-compras-registrar-pagos-saldo-modelo-saldo-y-contrato.md)

> COMPLETO por dos ejes: lógica financiera nueva (saldo, sobrepago, estado de pago) y contrato API/migración/ADR/DDR.

## Objective
Permitir que un administrador registre pagos parciales o completos de una compra confirmada, con fecha, monto y método, y conozca el saldo y el estado de pago calculados desde los pagos confirmados, sin sobrepagos (ni con solicitudes simultáneas) y sin tocar inventario ni gastos.

## Context
Ver `docs/tasks/TASK-compras-registrar-pagos-saldo.md` (supuestos H-01…H-10). Parte de `main` en `e4948d8` con PB-COM-003 y PB-COM-004 integrados.

# Specification

## Domain context
**Bounded Context:** Purchases (único). Sin Inventario, Gastos ni Catálogo.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Pago (`Payment`) | Documento inmutable que registra un monto pagado a un proveedor por una compra | PB-COM-005 |
| Estado del pago | `confirmed` («Confirmado»); `voided` reservado sin acción | PB-COM-005 (H-05) |
| Total pagado | Suma de pagos `confirmed` de la compra | PB-COM-005 |
| Saldo | Total de la compra − total pagado | PB-COM-005 |
| Estado de pago de la compra | `unpaid` («Sin pagar»), `partial` («Pago parcial»), `paid` («Pagada») | PB-COM-003 |
| Referencia de pago | `PAG-` + 8 hex mayúsculos del id | H-01 |
| `pay` | Acción en `allowed_actions` para registrar un pago | ADR |

## Current behavior
No hay pagos. `payment_status` siempre es `unpaid` y nada lo mueve (`purchase.py`, campo `payment_status`). La cancelación ya se bloquea con pagos (`has_activity`). El detalle del frontend muestra el estado de pago pero no ofrece pagar.

## Expected behavior
Desde el detalle de una compra confirmada con saldo, la pestaña «Pagos» permite «Registrar pago»: la persona indica fecha, monto y método viendo el saldo actual; el pago queda registrado, el total pagado, el saldo y el estado de pago (parcial o pagada) se actualizan, y la compra deja de poder cancelarse. Se puede pagar antes o después de recibir. Se listan los pagos. Pagar no modifica inventario ni crea gastos.

## Domain rules / invariants
Existentes: `has_activity` bloquea cancelar con pagos (INV-05 de PB-COM-003); estados solo por métodos del agregado; `company_id` en toda consulta; dinero en `Decimal`.
Nuevas:
- INV-01: solo una compra `confirmed` admite pagos (si no, 409).
- INV-02: monto > 0, con 2 decimales como máximo y ≤ `MONEY_MAX`.
- INV-03: monto ≤ saldo vigente (total − Σ pagos `confirmed`); no se permite sobrepago.
- INV-04: método ∈ {CASH, QR, BANK_TRANSFER, CARD, OTHER}.
- INV-05: fecha obligatoria, válida y no futura.
- INV-06: `payment_status` = `paid` si Σ pagos = total; `partial` si 0 < Σ < total; `unpaid` si no hay pagos. No depende de `reception_status`.
- INV-07: el pago confirmado es inmutable; no hay acción de anular, borrar ni reembolsar.
- INV-08: repetir `POST` con el mismo `payment_id` (misma compra) devuelve el pago existente sin otro efecto.
- INV-09: dos pagos simultáneos de la misma compra no superan el saldo (bloqueo de la compra).
- INV-10: pagar no crea gastos ni movimientos de inventario ni cambia total, líneas o recepciones.
- INV-11: una compra con total 0,00 tiene saldo 0 y no admite pagos (`pay` ausente).

## Acceptance criteria
Backend:
- AC-01: `POST /api/purchases/{id}/payments/` sobre una compra confirmada con datos válidos → 201 con el pago (referencia `PAG-…`, monto, método, fecha, estado `confirmed`, usuario) y el detalle de la compra muestra `paid_total`, `balance` y `payment_status` actualizados.
- AC-02: varios pagos acumulan; `payment_status` = `partial` mientras quede saldo y `paid` cuando el saldo llega a 0,00; `reception_status` no cambia.
- AC-03: monto ausente, no numérico, cero o negativo → 400 `amount`; con más de 2 decimales o sobre el máximo → 400; monto mayor al saldo → 400 `amount` indicando el saldo; no se guarda nada.
- AC-04: método ausente o fuera del catálogo → 400 `payment_method`; fecha ausente, inválida o futura → 400 `payment_date`; todos los errores de campos se devuelven juntos.
- AC-05: compra en borrador o cancelada → 409 «Solo una compra confirmada admite pagos.» sin cambios.
- AC-06: compra con saldo 0 (pagada o total 0) → 400 `amount` (sin saldo) y sin `pay` en `allowed_actions`.
- AC-07: se puede pagar con la compra sin recibir, parcialmente recibida o recibida; el pago no altera recepciones, inventario ni gastos (conteos de `StockMovement` y `Expense` iguales).
- AC-08: idempotencia: repetir el mismo `payment_id` → 200 con el mismo pago y el mismo acumulado; ese id en otra compra → 409 `payment_conflict`; `payment_id` no UUID → 400.
- AC-09: tras el primer pago la compra no puede cancelarse (409 con el mensaje existente) y `allowed_actions` no incluye `cancel`; incluye `pay` para `confirmed` con saldo y no para `draft`, `cancelled`, ni pagada.
- AC-10: `GET …/payments/` lista paginada (fecha desc, creación desc) con fecha, referencia, monto, método y usuario; otra compra u otra empresa → 404.
- AC-11: el detalle de compra expone `paid_total` y `balance` como texto con 2 decimales; para borrador/cancelada son `0.00` y total respectivamente sin pagos.
- AC-12: aislamiento y acceso: otra empresa → 404; sin token → 401; módulo `purchases` deshabilitado → 403 `module_disabled`; métodos no soportados → 405.
- AC-13: dos pagos simultáneos que juntos exceden el saldo → uno se registra y el otro falla con 400 (verificado en PostgreSQL real).
- AC-14: el monto del pago y el saldo son `Decimal` en todo el camino (sin `float`) y el `CheckConstraint` impide montos ≤ 0 en BD.
Interfaz:
- AC-15: el detalle de la compra tiene la pestaña «Pagos» con resumen (Total, Pagado, Saldo, Estado) y tabla (fecha, referencia, monto, método, usuario) con vacío explicado; sin entrada nueva en el menú.
- AC-16: «Registrar pago» sale solo con `pay` en `allowed_actions`; con saldo cero se muestra «Pagado» y no hay botón; borrador/cancelada se explican; no hay borrar, reembolso ni cobro por QR.
- AC-17: el diálogo muestra el saldo actual junto al monto; valida fecha obligatoria no futura, monto > 0 y método obligatorio; no deja pagar más que el saldo; «Pagar el saldo completo» rellena el monto.
- AC-18: «Registrar pago» se deshabilita mientras envía y reutiliza `payment_id` en reintentos; los errores del servidor se muestran en el diálogo sin cerrarlo ni borrar lo escrito.
- AC-19: tras registrar: toast, diálogo cerrado, pestaña y detalle actualizados (saldo, estado, tabla; `cancel` desaparece).
- AC-20: el Resumen de una compra confirmada muestra Total pagado, Saldo y el estado de pago con badge y texto.

## Edge cases / Error cases
- EDGE-01: pago exacto del saldo → `paid`; último pago parcial que lo completa → `paid`.
- EDGE-02: compra cancelada mientras se llenaba el diálogo → 409 al confirmar.
- EDGE-03: otro pago reduce el saldo antes de confirmar → 400 con el saldo vigente; el diálogo conserva lo escrito.
- EDGE-04: monto con decimales (`10.005`) → 400; `"abc"`, `float` o booleano → 400.
- EDGE-05: `payment_id` o id de compra no UUID → 400 / 404.
- EDGE-06: compra con total 0,00 confirmada → sin pagos, estado `unpaid` (INV-11, H-09).
- EDGE-07: proveedor desactivado o producto desactivado después de confirmar → se puede pagar.
- EDGE-08: compras confirmadas antes de esta task → `paid_total 0.00`, `balance = total`, `payment_status unpaid`.

## Authorization / permissions
Igual que PB-COM-002/003/004: usuario autenticado con empresa y módulo `purchases` habilitado (`required_modules = ('purchases',)`); solo existe el rol administrador. La empresa sale del usuario autenticado.

## API contract
API-01 `POST …/payments/`; API-02 `GET …/payments/`; API-03 campos nuevos del detalle de compra (`paid_total`, `balance`; `pay` en `allowed_actions`). Aditivo y compatible hacia atrás (detalle en el ADR).

## UI behavior
UI-01 pestaña «Pagos» en el detalle (plantilla «Detalle con pestañas…»); UI-02 diálogo «Registrar pago» con `NgbModal`; UI-03 Resumen con Total pagado/Saldo/badge. Detalle en el DDR.

## Non-functional requirements
Operación atómica con bloqueo de fila de la compra; lista sin N+1; sin dependencias nuevas; migración aditiva; importes como texto con 2 decimales.

## Out of scope
Anular o borrar pagos, reembolsos, cobro automático por QR, conciliación, configuración de métodos o método predeterminado de Compras, notas o referencia externa del pago, numeración correlativa, adjuntos, pagos en moneda distinta, creación de gastos, impacto en reportes, pantalla de detalle de un pago, filtros por estado de pago en la lista de compras, E2E.

## Open questions
Ninguna bloquea. Supuestos H-01…H-10 del TASK, reversibles con aprobación.

# Test Specification

## Unit tests
- `purchases/tests/test_payment_domain.py` (sin BD): `Purchase.register_payment` — INV-01…06, 11; errores juntos; cálculo de `payment_status`; `allowed_actions`/`can_pay`; inmutabilidad de total y líneas; sobrepago por 0,01.
- `purchases/tests/test_payment_application.py` (repositorios falsos): `RegisterPayment` — alta, idempotencia, conflicto de otra compra, acumulado leído tras el bloqueo, compra inexistente, consulta de lista.
- Frontend (Karma): `payments-api.service.spec.ts`, `purchase-payments-tab.component.spec.ts`, `payment-dialog.component.spec.ts` (validaciones, saldo, «pagar saldo», envío con `payment_id`, errores sin borrar), `purchase-detail.component.spec.ts` (pestaña, Resumen), utilidades de importes si se extraen.

## Integration tests
- `purchases/tests/test_payment_api.py` (BD): AC-01…AC-12, AC-14 con recepciones en distintos estados y conteos de `StockMovement`/`Expense`.
- `purchases/tests/test_payment_repository.py` (BD): ida y vuelta, `paid_total` solo `confirmed`, aislamiento por empresa, `CheckConstraint`.
- `makemigrations --check` (migración `0006`).
- `purchases/tests/test_payment_concurrency.py` (BD, PostgreSQL real; `skipUnless` como `test_receipt_concurrency`): AC-13.
- Guardas: `accounts/test_guards` (tabla `purchases_payment` con `company_id`) y `modularity/tests/test_enforcement` (rutas con `required_modules`).

## E2E
**NO.** El flujo se cubre con API y pruebas de componentes; no hay Playwright ni dependencia que lo justifique. Revisión visual manual en `delivery-publish`.

## Regression tests
Suite completa de backend (incluye cancelación PB-COM-003 y recepciones PB-COM-004); `ng lint`, `ng build` y Karma de `features/purchases`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | `test_payment_domain`, `test_payment_application`, `test_payment_api` |
| AC-03, AC-04 | `test_payment_domain`, `test_payment_api` |
| AC-05, AC-06 | `test_payment_domain`, `test_payment_api` |
| AC-07 | `test_payment_api` (conteos de movimientos y gastos, recepciones en distintos estados) |
| AC-08 | `test_payment_application`, `test_payment_api` |
| AC-09 | `test_payment_domain`, `test_payment_api` |
| AC-10, AC-11 | `test_payment_api`, `test_payment_repository`, `payments-api.service.spec.ts` |
| AC-12 | `test_payment_api`, `test_enforcement`, `test_guards` |
| AC-13 | `test_payment_concurrency` (PostgreSQL) y revisión del `select_for_update` |
| AC-14 | `test_payment_domain` (`Decimal`), `test_payment_repository` (constraint) |
| AC-15, AC-16, AC-20 | `purchase-detail.component.spec.ts`, `purchase-payments-tab.component.spec.ts` |
| AC-17, AC-18, AC-19 | `payment-dialog.component.spec.ts`, `payments-api.service.spec.ts` |

# Implementation Plan

## Architecture considerations
`docs/architecture/ddd.md` y el ADR. Estado y reglas en el agregado; idempotencia y lectura del acumulado en `application`; mapeo de errores en la vista (`_run`). Sin importaciones nuevas entre módulos.

## Proposed solution
`PaymentMethod`, `PaymentRecordStatus`, `Payment`, `Purchase.register_payment`/`can_pay`/`PurchaseNotPayable`/`PaymentConflict` en el dominio; `PaymentRepository`; casos de uso `RegisterPayment` y `ListPayments`; `DjangoPaymentRepository`; vistas, serializers y rutas. En Angular: modelo y servicio de pagos, `PurchasePaymentsTabComponent`, `PaymentDialogComponent` y cambios en `purchase-detail`.

## Files/components affected
- **Backend** (`backend/modules/purchases/`): `domain/{enums,exceptions,purchase,payment,repositories}.py`; `application/{payment_commands,payment_queries,purchase_queries}.py`; `infrastructure/django/{models,mappers,payment_repository}.py`; `migrations/0006_payments.py` (por `makemigrations`); `api/{payment_views,payment_serializers,purchase_serializers,purchase_views,purchase_urls}.py`; pruebas listadas.
- **Frontend** (`frontend/panel_admin/src/app/features/purchases/`): `models/{purchase,payment}.ts`, `services/payments-api.service.ts`, `components/{purchase-payments-tab,payment-dialog}/*`, `pages/purchase-detail/*`, `testing/payment-fixtures.ts`.
- **Docs**: `docs/producto/modulos-implementados.md`, `docs/architecture/ddd.md` (pagos de compra), notas en `docs/design/design-system.md` (pestañas de documentos relacionados con diálogo de alta).

## Implementation steps
1. **Dominio**: enums, `Payment`, `Purchase.register_payment`/`can_pay`/`allowed_actions`, excepciones + pruebas (INV-01…07, 11; AC-01…06, 09).
2. **Infraestructura**: modelo, migración `0006`, mapper, `DjangoPaymentRepository` (`paid_total`, `list_for_purchase`) + prueba (AC-14).
3. **Aplicación**: `RegisterPayment` (bloqueo, acumulado, idempotencia), `ListPayments`, `GetPurchase` con `paid_total`/`balance` + pruebas con falsos (INV-08, 09; AC-08, 11).
4. **API**: serializers, vistas, rutas, campos del detalle y guardas (AC-01…AC-12) con pruebas de API reales.
5. **Concurrencia**: `test_payment_concurrency` (AC-13).
6. **Frontend base**: modelo, servicio y fixtures + pruebas (AC-10, 11).
7. **Pestaña «Pagos» y Resumen** (AC-15, 16, 20).
8. **Diálogo «Registrar pago»** (AC-17…19).
9. **Documentación** y verificación local: `manage.py test`, `makemigrations --check`, `ng lint`, `ng build`, Karma de `features/purchases`.

## Database / migrations
`purchases/migrations/0006_payments.py` por `makemigrations`: crea `purchases_payment` con `CheckConstraint(amount > 0)` e índice `(company_id, purchase_id)`. No se editan `0001`…`0005`. Rollback: ver ADR (`migrate purchases 0005`, tras devolver `payment_status` a `unpaid`).

## Risks
- Sobrepago concurrente: bloqueo de la compra + acumulado tras el bloqueo; verificado con PostgreSQL real en publish.
- `payment_status` persistido puede divergir de los pagos si algo escribe fuera del agregado: solo `register_payment` lo cambia; prueba de repositorio y de API lo cubren.
- Compra con total 0 (H-09): documentado.
- Estado `voided` sin acción: solo `confirmed` suma; deuda explícita.

## New dependencies
Ninguna.
