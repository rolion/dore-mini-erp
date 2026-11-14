# PLAN-2026-11-14-pagos-ventas-libro-entradas (v1)

**Task:** TASK-pagos-ventas-libro-entradas · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno / ADR-pagos-ventas-libro-entradas-integracion-e-idempotencia

## Objective
Que cada pago de un pedido de Ventas, con `accounting` habilitado, cree una única entrada en el libro por el monto recibido, en la misma transacción, con idempotencia real del registro de pagos; sin cambios con `accounting` deshabilitado.

## Context
Ver TASK (hechos con `archivo:línea`) y ADR. Insumo: tarjeta Trello PB-ACC-003. Depende de PB-ACC-001 y PB-ACC-002 (en `main`).

# Specification

## Domain context
`sales` (agregado `Order`/`Payment`) consume `accounting` solo por su fachada `services`. Cobros (PB-COB-002) queda fuera.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Entrada | Registro inmutable del dinero recibido por un pago | Trello / PB-ACC-002 |
| Cuenta destino | Cuenta que recibe el dinero del método (PB-ACC-001) | Trello |
| Fecha efectiva | `payment_date` del pago | Trello |
| Clave de idempotencia | UUID que identifica un intento de cobro y se reutiliza en reintentos | Trello / ADR |

## Current behavior
Ver TASK: el pago no genera entrada; un reintento crea otro pago.

## Expected behavior
Con `accounting` habilitado, `POST /api/orders/<id>/payments/` resuelve la cuenta del método en el servidor y guarda pago, saldos y entrada atómicamente; sin cuenta o con fallo contable responde 409 y no persiste nada. Reintentar con la misma clave y datos devuelve el pedido sin duplicar pago ni entrada. Crear, editar, preparar, entregar y cancelar no crean entradas; los pagos recibidos permanecen al cancelar. Con `accounting` deshabilitado el flujo es el actual.

## Domain rules / invariants
- INV-01 (existente) monto > 0, método válido, fecha no futura, pago ≤ saldo, pedido no cancelado.
- INV-02 Con accounting habilitado, un pago existe si y solo si existe su entrada (`origin_kind=PRODUCT`, `origin_id`=pago).
- INV-03 La entrada guarda la cuenta resuelta al cobrar, la moneda `BOB`, el monto y la fecha efectiva del pago; no se recalcula.
- INV-04 Misma `idempotency_key` en el mismo pedido y mismos datos → el pago existente (sin nuevo pago ni entrada); otros datos → conflicto.
- INV-05 Sin reversiones: ninguna acción borra pagos ni entradas.

## Acceptance criteria
- AC-01 Pedido de Bs 300 con pagos 100 y 200 con accounting habilitado → dos entradas (100 y 200), total del libro 300, saldo del pedido 0, estado de pago `PAID`.
- AC-02 Pago parcial crea una sola entrada por su monto.
- AC-03 Crear, agregar ítems, preparar, marcar listo, entregar y cancelar un pedido sin pagos nuevos no crea entradas; cancelar un pedido con pagos conserva pagos y entradas.
- AC-04 Doble envío (secuencial y concurrente) y reintento tras pérdida de respuesta con la misma clave → un pago y una entrada, respuesta 200 en el replay; misma clave con otro monto/método/fecha/referencia → 409 `idempotency_key_reused`.
- AC-05 Pagos distintos concurrentes (claves distintas) no superan el saldo: el excedente recibe 400 y quedan solo los pagos válidos con sus entradas.
- AC-06 Método sin mapeo, mapeo inactivo o cuenta inactiva/no compatible → 409 `payment_method_without_account` con mensaje accionable; no se crean pago ni entrada ni cambia el saldo.
- AC-07 Si `record_entry` falla (validación, conflicto o excepción), el pago, el saldo y el estado de pago se revierten.
- AC-08 La entrada tiene la cuenta del mapeo vigente al cobrar (tras cambiar el mapeo, entradas previas conservan su cuenta y la siguiente usa la nueva), la fecha efectiva del pago, el usuario y `origin_document_ref` = id del pedido.
- AC-09 Con `accounting` deshabilitado (o nunca habilitado) los pagos se registran como antes, sin cuenta ni entrada y sin necesidad de clave; el módulo accounting no se consulta.
- AC-10 Aislamiento y permisos: un pedido o cuenta de otra empresa no se usa (404 / cuenta ajena imposible); usuarios sin permiso de Ventas (o con `sales` deshabilitado) siguen rechazados; registrar un cobro no exige acceso a pantallas contables.
- AC-11 Cobrar no genera movimientos de inventario.
- AC-12 Frontend: la pantalla de pago envía `idempotency_key` generada al abrir el formulario y reutilizada en reintentos (se renueva tras un pago exitoso); el 409 muestra el mensaje del servidor.

## Edge cases / Error cases
- EDGE-01 Replay sobre pedido ya saldado o cancelado → 200 con el pedido (no 409 de saldo/cancelado).
- EDGE-02 Clave idéntica en otro pedido → es un pago nuevo (clave por pedido).
- EDGE-03 `idempotency_key` mal formada → 400.
- EDGE-04 Pedido cancelado y clave nueva → 409 `order_cancelled` sin entrada (comportamiento actual).
- EDGE-05 Accounting habilitado pero método `OTHER` sin mapeo → AC-06.

## Authorization / permissions
Sin cambios: permiso de Ventas (`CompanyModulePermission` + `required_modules=('sales',)`). `record_entry` no es endpoint ni exige permiso contable. Empresa desde el usuario autenticado.

## API contract
- API-01 `POST /api/orders/<id>/payments/`: body existente + `idempotency_key` (UUID, opcional). 201 pago nuevo; **200** replay (mismo cuerpo `OrderSerializer`, sin claves nuevas); 409 `{code, detail}` con `payment_method_without_account`, `ledger_rejected`, `ledger_conflict`, `idempotency_key_reused`. Compatible hacia atrás: sin clave, igual que hoy.

## UI behavior
- UI-01 Sin pantallas nuevas. Detalle del pedido, formulario de pago existente: clave oculta; el error 409 aparece en el aviso de error ya usado por la acción de pago; sin texto hardcodeado (mensajes del servidor + claves i18n existentes).

## Non-functional requirements
Dinero en `Decimal`; operación única en una transacción; sin consulta contable cuando `accounting` está deshabilitado.

## Out of scope
Reversiones, reembolsos, Cobros/proformas, partida doble, saldos iniciales, reporte ventas − gastos, entradas retroactivas de pagos previos.

# Test Specification

## Unit tests
- Dominio: `register_payment` con clave (guarda `idempotency_key`/digest), `find_payment_by_key`, validaciones previas sin cambios (INV-01, INV-04).
- Aplicación con fakes (`sales/tests/fakes.py`): orden idempotencia → pago → entrada; sin cuenta → violación; fallo del ledger propaga; ledger no disponible → sin llamada (AC-06, AC-07, AC-09).

## Integration tests
- `sales/tests/test_payment_ledger.py` (API, BD real): AC-01..AC-11 incluyendo rollback con `record_entry` parcheado para fallar, cambio de mapeo, empresa B, accounting deshabilitado, sin movimientos de inventario.
- Concurrencia (`TransactionTestCase`, patrón de `accounting/tests/test_entry_concurrency.py`): mismo envío ×2 en hilos y dos pagos distintos que juntos exceden el saldo (AC-04, AC-05).
- `test_boundaries.py`: `sales` → `accounting` permitido solo vía `services` desde infraestructura.

## E2E
NO — flujo crítico cubierto por pruebas de API con BD real; no se instala Playwright.

## Regression tests
Suite de Ventas existente sin clave (AC-09), suite de `accounting`, `receivables`, `reporting` y frontend de Ventas.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02, AC-08 | API integración (`test_payment_ledger.py`) |
| AC-03 | API integración (acciones sin pago) |
| AC-04 | API integración + concurrencia |
| AC-05 | Concurrencia |
| AC-06, AC-07 | Aplicación con fakes + API integración |
| AC-09 | Regresión suite Ventas + test con accounting deshabilitado |
| AC-10 | API integración (empresa B, permisos) + regresión del gate |
| AC-11 | API integración (sin movimientos de inventario) |
| AC-12 | Specs de `order-payments.component` y `orders-api.service` |

# Implementation Plan

## Architecture considerations
Ver ADR. Puerto `PaymentLedger` en Ventas; adaptador por fachada; idempotencia replicando Cobros pero opcional.

## Files/components affected
- Backend: `sales/domain/order.py` (Payment, `find_payment_by_key`, `register_payment`), `sales/application/ports.py`, `sales/application/commands.py` (`RegisterPayment`), `sales/infrastructure/adapters.py` (`PaymentLedgerAdapter`), `sales/infrastructure/django/{models,mappers,repositories}.py`, migración `sales/0003_payment_idempotency.py`, `sales/api/{serializers,views}.py`, `sales/tests/test_boundaries.py`, `sales/tests/fakes.py`, tests nuevos.
- Frontend: `features/sales/components/order-payments/*`, `models/order.ts`, `services/orders-api.service.ts` + specs.
- Docs: TASK/ADR/PLAN; `docs/architecture/ddd.md` solo si cambia el mapa de dependencias.

## Implementation steps
1. Dominio: campos en `Payment`, `find_payment_by_key`, `register_payment(..., idempotency_key, request_digest)` (INV-01, INV-04).
2. Migración `0003` aditiva y mapper/repositorio (`PaymentModel.idempotency_key`, `request_digest`, índice único parcial por pedido).
3. Puerto y adaptador del libro; permitir `sales → accounting` en el test de fronteras (INV-02, INV-03, AC-08).
4. `RegisterPayment`: replay → pago → guardar → entrada; traducción de errores (AC-04, AC-06, AC-07, AC-09).
5. API: campo `idempotency_key`, 200/201, 409 con códigos (API-01).
6. Pruebas backend (unidad, integración, concurrencia, regresión) y ejecución de la suite completa.
7. Frontend: clave por intento, envío y manejo del 409 + specs; `npm run lint`, `i18n:check`, Karma acotado, build (AC-12).

## Database / migrations
`sales/0003`: `AddField` ×2 nullable + `UniqueConstraint(order, idempotency_key, condition=idempotency_key IS NOT NULL)`. No se editan migraciones aplicadas.

## Risks
- El 409 sin mapeo puede bloquear cobros tras habilitar accounting si la configuración cambió: mensaje guía a Contabilidad.
- Clientes que no envían clave no tienen deduplicación (documentado; el frontend propio sí).

## New dependencies
Ninguna.
