# TASK-pagos-ventas-libro-entradas: Integrar pagos de Ventas con el libro de entradas (PB-ACC-003)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-pagos-ventas-libro-entradas
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/69
**Fuente:** https://trello.com/c/kFAIOGr7/20-pb-acc-003-integrar-pagos-de-ventas-con-el-libro-de-entradas

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-14 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello; `main` al día (63dd4b9, incluye PB-ACC-001 y PB-ACC-002) | delivery-start |
| 2026-11-14 | INVESTIGATION → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (dinero, transacción entre dos módulos, migración sobre pagos); sin diseño visual nuevo | delivery-start |
| 2026-11-14 | PLANNING → ENGINEERING | Specification READY: la tarjeta cubre las reglas; decisiones técnicas abiertas resueltas en el ADR | delivery-start |

## Investigación

### Requerimiento
Insumo de la tarjeta PB-ACC-003 (P1; **no es una Specification aprobada**). Historia: como responsable de caja, cada pago de un pedido genera una entrada única por el dinero recibido. Esperado: con accounting habilitado, resolver método → cuenta y guardar pago, saldos y entrada en una misma transacción; mantener validaciones (monto > 0, método válido, pago ≤ saldo); completar la idempotencia del registro de pagos (la unicidad de la entrada no evita dos pagos distintos ante un reintento); pago parcial genera solo su monto; crear, registrar venta, entregar o cancelar no generan entradas; sin mapeo o con fallo contable se rechaza el pago sin persistencia parcial y con mensaje accionable; se conservan cuenta y fecha efectiva; cobrar no toca stock; con accounting deshabilitado, flujo actual; cobrar no exige permiso de edición contable, sí el permiso del flujo de Ventas; sin reversiones ni reembolsos. Criterios: pedido de Bs 300 con pagos 100 y 200 → dos entradas, total 300, saldo cero; sin pago nuevo no hay entradas y los pagos no desaparecen al cancelar; doble envío / reintento tras pérdida de respuesta → un pago y una entrada; pagos concurrentes distintos no exceden el saldo; fallo o mapeo ausente revierte todo; verificar destino, fecha, permisos, empresa y funcionamiento con accounting deshabilitado. Dependencias: PB-ACC-001 y PB-ACC-002 (ambas en `main`). Fuera: partida doble, fiscal, egresos, transferencias, saldos iniciales, reversiones; no tocar el reporte ventas − gastos.

### Hechos encontrados
- `backend/modules/sales/application/commands.py:211-220` — `RegisterPayment` bloquea el pedido (`get_for_update`), llama a `Order.register_payment` y guarda; no hay clave de idempotencia ni integración contable.
- `backend/modules/sales/domain/order.py:348-367` — `register_payment`: rechaza pedido cancelado (`order_cancelled`), valida monto > 0, método del enum, fecha no futura y monto ≤ saldo; `Payment` (`order.py:153-159`) no tiene clave de idempotencia ni usuario.
- `backend/modules/sales/infrastructure/django/models.py:58-73` — `PaymentModel` sin `company_id` (hereda del pedido), sin clave de idempotencia.
- `backend/modules/sales/infrastructure/django/repositories.py:36-69` — `get_for_update` bloquea la fila del pedido; `save` agrega pagos nuevos (`_append_new_payments`, solo inserta).
- `backend/modules/sales/api/views.py:68-80,263-269` — `_run` envuelve toda mutación en `transaction.atomic()`; `OrderPaymentView` devuelve 201 con el pedido; `_actor` (`:131`) da usuario y nombre. Serializer de entrada: `sales/api/serializers.py:47-51`.
- `backend/modules/sales/infrastructure/adapters.py:100-160` — patrón de integración opcional (`StockOutputAdapter`: `module_gate`, fachada de otro módulo, traducción de errores a `OrderRuleViolation`/`OrderValidationError`); puerto en `sales/application/ports.py`.
- `backend/modules/accounting/services.py` — `resolve_account(company_id, method)` (cuenta vigente o `None`) y `record_entry(company_id, EntryInput)` (exige transacción abierta; idempotente por `(empresa, origin_kind, origin_id)`; `EntryValidationError`, `EntryConflict`, `EntryContractError`). `origin_kind='PRODUCT'` y `origin_id` = id del pago están previstos (ADR del libro, decisiones 2 y 4).
- `backend/modules/sales/tests/test_boundaries.py:15-33` — dependencias permitidas: `sales` no incluye `accounting`; hay que añadirla (solo vía `services` desde infraestructura).
- `backend/modules/receivables/api/views.py:139-153`, `receivables/application/collections.py:62-104` — patrón de idempotencia ya existente: `idempotency_key` UUID, huella (digest) del contenido, replay 200 / alta 201, 409 si la misma clave llega con otros datos. Se imita.
- `backend/config/permissions.py` — el permiso por defecto de las vistas de Ventas (`CompanyModulePermission`) exige admin de empresa y `sales` habilitado; no hay permiso contable, y `record_entry` no es un endpoint, así que cobrar no exige nada contable.
- Frontend: `features/sales/components/order-payments/order-payments.component.ts` emite `PaymentInput` sin clave; `features/purchases/components/payment-dialog/payment-dialog.component.ts:24` ya genera un `paymentId` al abrir y lo reutiliza en reintentos (patrón a seguir).

### Hipótesis / supuestos no confirmados
- La clave de idempotencia es opcional en el contrato (compatibilidad con clientes y pruebas actuales); el frontend de Ventas siempre la envía. Sin clave no hay deduplicación (comportamiento previo).
- Moneda de los pagos de Ventas: `BOB`, única de los flujos (`quotations/domain/proforma.py:7`).

### Módulos y dependencias relacionadas
`sales` (dominio, comando, adaptador, API, migración), `accounting` (solo consumo vía `services`), `shared/module_gate`. Frontend `features/sales`.

### Implementaciones similares existentes
`receivables` (idempotencia y huella); `StockOutputAdapter` (integración opcional dentro de la transacción del comando).

### Comportamiento actual
Un pago de pedido se guarda sin cuenta ni entrada; reintentar el envío crea otro pago.

### Restricciones
`CLAUDE.md`: `Decimal`, `company_id` desde el usuario, no editar migraciones aplicadas (la nueva es aditiva), i18n es/en/pt, dominio sin Django, módulos solo por `services`.

### Riesgos identificados
- Reintento tras pérdida de respuesta o doble clic crea dos pagos (mitigado: clave de idempotencia).
- Rollback parcial si la entrada falla después de guardar el pago (mitigado: todo en el `atomic` de `_run`; prueba de rollback).
- Carrera entre pagos distintos (mitigado: bloqueo de la fila del pedido).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — dinero, nueva dependencia sales → accounting, migración sobre pagos y contrato de la API de pagos.

### Diseño requerido
**NO** — no hay pantallas nuevas; solo se envía la clave y se muestra el mensaje 409 accionable con el patrón de error existente.

## Diseño
No aplica.

## Arquitectura
`docs/adr/ADR-pagos-ventas-libro-entradas-integracion-e-idempotencia.md`

## Plan
`docs/plans/PLAN-2026-11-14-pagos-ventas-libro-entradas.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
