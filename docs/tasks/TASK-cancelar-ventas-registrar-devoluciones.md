# TASK-cancelar-ventas-registrar-devoluciones: Cancelar ventas y registrar devoluciones con reversión contable

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-cancelar-ventas-registrar-devoluciones
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/119
**Fuente:** https://trello.com/c/xkhyFuVJ/22-cancelar-ventas-y-registrar-devoluciones-con-reversi%C3%B3n-contable

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-24 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello | delivery-start |
| 2026-11-24 | INVESTIGATION → DESIGN | NEEDS_ARCHITECTURE; diseño requerido | delivery-start |
| 2026-11-24 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-11-24 | ARCHITECTURE → PLANNING | ADR escrito; decisiones de negocio respondidas por el usuario | delivery-start |
| 2026-11-24 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR | delivery-start |
| 2026-11-24 | ENGINEERING → REVIEW | Implementación escrita; pruebas de integración con BD sin ejecutar (sin credenciales de PostgreSQL en esta sesión) | delivery-build |
| 2026-11-24 | REVIEW → REVIEW | Quality Gate ciclo 1 (subagente aislado): sin Critical/High; REV-01 (Medium), REV-02 y REV-03 (Low) corregidos; REV-04 (Specification, Low) abierto; pruebas con PostgreSQL y revisión visual NO realizadas, por lo que no se declara PASS | delivery-publish |

## Investigación

### Requerimiento
Fuente: https://trello.com/c/xkhyFuVJ (tarjeta «Cancelar ventas y registrar devoluciones con reversión contable»). Insumo, no Specification aprobada.

Historia: como responsable de Ventas, quiero cancelar un pedido o registrar una devolución desde su detalle para que existencias y contabilidad reflejen lo ocurrido.

- Antes de entregar: «Cancelar venta» con motivo; revertir los asientos aplicables; si nunca hubo salida de inventario, el stock no cambia.
- Después de entregar: «Registrar devolución» con motivo, mostrar productos/cantidades y efecto contable antes de confirmar; reingresar las unidades que salieron al almacén de origen; usar el costo registrado al vender; contrasientos de ingreso y costo de venta.
- Detalle: fecha, usuario, motivo, movimientos y asientos vinculados; conservar venta, salidas y asientos originales.
- AC de la tarjeta: cancelar sin salida deja el stock intacto; devolver repone en el almacén de origen y el reverso usa las cuentas originales en período abierto; todo en una transacción; reintentos/concurrencia no duplican; permisos y aislamiento por empresa.
- Decisiones pendientes de la tarjeta, **respondidas por el usuario (2026-11-24)**: (1) **solo devolución total** en la primera versión; (2) **cobros/anticipos: registrar el reembolso realizado fuera de PocketBiz** (se contabiliza como contrasiento del cobro).

### Hechos encontrados
- `backend/modules/sales/domain/order.py:30-39` — `OPEN_STATUSES` y `_ALLOWED_TRANSITIONS`: `DELIVERED` y `CANCELLED` no tienen transiciones; `cancel` solo en NEW/IN_PREPARATION/READY.
- `backend/modules/sales/domain/order.py:352-362` — `Order.cancel(reason, now)`: motivo obligatorio, guarda `cancellation_reason`/`cancelled_at`; sin usuario guardado. No existe devolución.
- `backend/modules/sales/domain/enums.py:15-24` — `PaymentStatus.REFUNDED` existe pero ningún flujo lo produce.
- `backend/modules/sales/application/commands.py:245-267` — `CancelOrder`: rechaza con 409 `order_has_payments_posted` si hay cobros contabilizados («hasta que exista el reembolso»); revierte solo el reconocimiento «al confirmar» (histórico, `SALE_RECOGNITION`).
- `backend/modules/sales/application/commands.py:198-243` — `DeliverOrder`: salida de inventario (`stock.register_outputs`), reconocimiento (`SALE_DELIVERY`), costo (`INVENTORY_SALE_COST`), todo en la transacción del llamante.
- `backend/modules/sales/infrastructure/adapters.py:225-300` — `SalesPostingAdapter`: cobros como `SALE_ADVANCE` (antes de entregar) o `SALE_PAYMENT` (tras reconocer) con `origin_id = payment.id`; cobros anteriores a la cobertura van al libro anterior (`record_entry`, `origin_kind='PRODUCT'`); `reverse_recognition` usa `reverse_automatic_entry`.
- `backend/modules/accounting/services.py:436-450` y `787-798` — `reverse_journal_entry` / `reverse_automatic_entry`: contrasiento con cuentas originales, fecha explícita en período abierto, idempotente por asiento (devuelve la existente), requiere transacción; devuelve `None` si el evento nunca se contabilizó. `services.py:281` `reverse_entry` hace lo propio con el libro anterior.
- `backend/modules/inventory/services.py:85-` — `reverse_source_movements(company_id, source_type, source_id, …)`: revierte todos los movimientos confirmados de un origen, todo o nada, con política de stock negativo; ya lo usa Compras (`backend/modules/purchases/infrastructure/adapters.py:107-125`), con traducción de `InsufficientStock`. Las salidas de Ventas se registran con `source_type='sales_order'` (`sales/infrastructure/adapters.py`, `StockOutputAdapter`), por lo que los movimientos originales quedan «revertidos» y enlazados.
- `backend/modules/inventory/domain/movement.py:114-129` y `infrastructure/django/models.py:28-65` — una sola reversión por movimiento (restricción única `inv_mov_one_reversal_uniq`), también bajo concurrencia.
- `backend/modules/costing/services.py:42-70` y `costing/domain/cost.py:18-21` — Costeo tiene `reverse_receipt_cost` (contra-evento al costo original) pero **no** reversa de salidas valorizadas (`CostKind` solo tiene `in`, `in_reversal`, salida); la devolución necesita su contra-evento de salida.
- `backend/modules/sales/infrastructure/django/read_queries.py:20` — «pedido válido» = no `CANCELLED` y con ítems: un estado nuevo debe excluirse aquí o las ventas devueltas seguirían sumando.
- `backend/modules/sales/api/views.py:262-292` — `OrderDeliverView`, `OrderDeliveryPreviewView` (vista previa solo lectura) y `OrderCancelView`: patrón para el endpoint de devolución y su vista previa.
- `frontend/panel_admin/src/app/features/sales/pages/order-detail/order-detail.component.ts:135-215,294-321` — `canCancel` por `allowedTransitions`, `askCancelReason` (SweetAlert con motivo obligatorio).
- `docs/design/design-system.md:216` — patrón «Diálogo de acción irreversible con motivo» (`movement-reverse-dialog`, `receipt-revert-dialog`); `:180` detalle de pedido en curso (DDR-pedido-pantalla-unica-creacion-detalle-pedido-en-curso).
- `backend/modules/accounts/api/permissions.py:16` — permiso por defecto: usuario con empresa activa y rol admin; no hay modelo de permisos nuevo.

### Hipótesis / supuestos no confirmados
- La fecha de los contrasientos y de la devolución es **hoy** (zona horaria de la empresa); si cae en un período cerrado se rechaza con mensaje accionable (el motor ya lo exige).
- Devolver un pedido cuya salida de inventario nunca existió (producto sin stock controlado, Inventario deshabilitado) no cambia existencias.
- Los cobros anteriores a la cobertura contable (libro anterior) también se reembolsan por `reverse_entry`.

### Módulos y dependencias relacionadas
Sales (principal); Inventory, Costing y Accounting solo por sus fachadas `services.py`; Reporting (lee ventas válidas); frontend `features/sales`.

### Implementaciones similares existentes
Reversión de recepciones en Compras (`purchases/infrastructure/adapters.py:107-125`, ADR-inventario-revertir-movimientos-contramovimientos); `CancelOrder`; reversión de asiento al anular gasto (`docs/plans/PLAN-2026-11-18-revertir-asiento-al-anular-gasto.md`).

### Comportamiento actual
Cancelar solo antes de entregar y solo sin cobros contabilizados; tras entregar no hay forma de deshacer la venta, su salida de stock ni sus asientos.

### Restricciones
`CLAUDE.md`: `Decimal`, `company_id`, estados por métodos del agregado, nunca editar migraciones aplicadas, módulos solo por fachada.

### Riesgos identificados
- Orquestación de cuatro contextos en una transacción (stock, costo, asientos, pedido); orden de bloqueos: pedido → empresa/costeo → almacén (igual que Compras).
- Cobros en tres formas (anticipo, cobro tras reconocer, libro anterior): el reembolso debe reversar cada una con su evento.
- Reportes que sumen ventas devueltas si el estado no se excluye.
- Stock negativo bloqueado no aplica al reingreso (es una entrada), pero sí hay que revalidar la entrada si el pedido se canceló antes de entregar (no hay salida).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — toca finanzas, cuatro módulos, un estado nuevo del agregado, migración y un contrato API nuevo.

### Diseño requerido
**SI** — nueva acción, diálogo con vista previa del efecto y sección de historial en el detalle.

## Diseño
Ver `docs/design/DDR-cancelar-ventas-registrar-devoluciones-acciones-y-vista-previa.md`.

## Arquitectura
Ver `docs/adr/ADR-cancelar-ventas-registrar-devoluciones-reversion-orquestada-y-registro.md`.

## Plan
`docs/plans/PLAN-2026-11-24-cancelar-ventas-registrar-devoluciones.md` (v1, COMPLETO).

## Implementación
**Backend (Sales + Costing).**
- Dominio: `OrderStatus.RETURNED`, campos `cancelled_by_name`, `returned_at/by`, `return_reason`, `refund_acknowledged`; `Order.register_return`, `ensure_returnable`; `cancel` ahora acepta `by_name` y `refund_acknowledged`; `payment_status` = `REFUNDED` con cobros y reembolso confirmado; transición `return` desde `DELIVERED` (INV-01, INV-02, INV-07).
- Costeo: `CostKind.OUT_REVERSAL`, `ReverseOutputCost` y `costing.services.reverse_output_cost` (contra-evento al costo de venta, promedio sin cambio, idempotente) (AC-05).
- Sales: `ReturnOrder` y `PreviewOrderReturn` (`application/returns.py`); `CancelOrder` ya no rechaza con cobros: exige la confirmación del reembolso y contrarresta los cobros; puertos y adaptadores nuevos (`reverse_outputs`, `reverse_cost`, `reverse_payments`, `reverse_delivery`, `reversal_entries`, `output_links`) (AC-01..07, 11).
- API: `POST …/return/`, `GET …/return-preview/`, `refund_acknowledged` en `cancel`, campos de auditoría y `reversal` en el pedido (API-01..04); «pedido válido» excluye `RETURNED` (AC-10); migración `sales/0005_order_return_and_refund`.

**Frontend (`features/sales`).** Botón «Registrar devolución» (acción `return` del servidor), `ReturnDialogComponent` (NgbModal con vista previa, motivo y reembolso), `OrderReversalCardComponent` (fecha, usuario, motivo, reembolso y vínculos), confirmación del reembolso al cancelar con cobros, estado «Devuelto», claves i18n es/en/pt (`SALES.ORDER_RETURN.*`). Pantalla de referencia: detalle de documento en curso y «Diálogo de acción irreversible con motivo» (design-system §5).

**Desviaciones respecto al plan.**
- Los contrasientos de reembolso/devolución usan `reverse_automatic_entry` (y `reverse_entry` para cobros del libro anterior); no se creó evento contable nuevo (como decidió el ADR).
- El diálogo de cancelar sigue siendo SweetAlert con una segunda confirmación cuando hay cobros (en vez de casilla dentro del mismo diálogo); el de devolución es NgbModal.
- `PaymentStatus.REFUNDED` se deriva de `refund_acknowledged` + cobros.

**Verificación propia (no es el Quality Gate).** Backend: pruebas de dominio/aplicación/costeo-dominio sin BD pasan (130 + 8); **las pruebas de integración con PostgreSQL** (`test_order_return.py`, ajustes en `test_sales_posting.py`, `test_api.py`, `test_cost_ledger.py`) **no se ejecutaron**: la sesión no tiene credenciales de la base. Frontend: `ng lint`, `tsc` de app y specs, `i18n:check` y 304 pruebas Karma de `sales` pasan; `ng build` no se ejecutó. `ruff`/`flake8`: sin avisos nuevos en lo cambiado (quedan los previos de `views.py` y `order.py`).

**Deuda técnica.** Los cobros de pedidos cancelados siguen apareciendo en `payments_between` (dinero recibido) aunque estén reembolsados; la devolución parcial y el saldo a favor quedan fuera de alcance. Sin pruebas de concurrencia simultánea reales (se confía en `select_for_update` + reversiones idempotentes).

## Review
**Resultado: sin Critical/High, pero NO se declara PASS** porque dos verificaciones aplicables no se ejecutaron: las pruebas con PostgreSQL (AC-01..09 y AC-11 dependen de ellas) y la revisión visual.

Ejecutado por el revisor aislado: pruebas sin BD (138 OK), `manage.py check`, `makemigrations --check` (sin cambios), `ruff`/`flake8`, `ng lint`, `tsc` app y specs, `i18n:check` (2505 claves, 0 faltantes), `ng test` de `features/sales` (285 OK) y `ng build` (solo avisos de CSS de la plantilla). Tras las correcciones: `ng test` sales+customers 385 OK, `ng lint` OK, pruebas backend sin BD OK.

No realizado: pruebas con PostgreSQL (`test_order_return`, `test_sales_posting`, `test_api`, `test_cost_ledger`), revisión visual (claro/oscuro, 390/1440 px), `bandit`/`npm audit`, concurrencia real.

Hallazgos:
- REV-01 (Medium, IMPLEMENTATION): el frontend trataba `RETURNED` como pedido válido (perfil del cliente y lista) → corregido (`isVoidedStatus`, `owes`, `showsBalance`).
- REV-02 (Low): 3 E501 nuevos → corregidos (queda el E501 previo de `commands.py`).
- REV-03 (Low, DESIGN): fecha ISO y enlaces «Ver» sin nombre accesible → corregidos; los HEX de `confirmRefund` siguen el patrón existente de `askCancelReason`.
- REV-04 (Low, SPECIFICATION): UI-02 y el DDR piden una casilla de reembolso dentro del diálogo de cancelar; se implementó una segunda confirmación. Abierto: requiere aprobación del usuario para aceptar la desviación o pedir la casilla.
- Observación: `reverse_entry` del libro anterior no traduce sus errores a 409.

## Publicación
_Pendiente_
