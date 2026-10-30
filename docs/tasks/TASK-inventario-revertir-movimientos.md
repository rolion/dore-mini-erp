# TASK-inventario-revertir-movimientos: Revertir movimientos mediante contramovimientos (PB-INV-008)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-inventario-revertir-movimientos
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/40
**Fuente:** https://trello.com/c/94lEuUD5/21-pb-inv-008-revertir-movimientos-mediante-contramovimientos

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN | Veredicto NEEDS_ARCHITECTURE; diseño requerido | delivery-start |
| 2026-10-30 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-10-30 | ARCHITECTURE → PLANNING | ADR escrito | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR | delivery-start |
| 2026-10-30 | ENGINEERING → REVIEW | Implementación y pruebas escritas | delivery-build |
| 2026-10-30 | REVIEW → PUBLISH | Quality Gate ciclo 1: PASS; 3 hallazgos Low abiertos (REV-01..03); revisión visual en navegador no verificada | delivery-publish |

## Investigación

### Requerimiento
Fuente: https://trello.com/c/94lEuUD5 (tarjeta «PB-INV-008 · Revertir movimientos mediante contramovimientos», módulo Inventario, P1, dependencias PB-INV-004 y PB-INV-007). El contenido de la tarjeta es **insumo**, no una Specification aprobada.

Historia: como administrador, quiero corregir un movimiento confirmado mediante una reversión para conservar su historial.

- **Accesos:** detalle de movimiento o de ajuste → «Revertir» para orígenes manuales permitidos; detalle de recepción en Compras → «Revertir recepción» para los movimientos originados allí.
- **Diálogo:** referencia y tipo del movimiento original, producto, almacén, cantidad, efecto inverso previsto y **motivo obligatorio**. Para una recepción se muestran todas sus líneas y el impacto; **no hay reversión parcial** en esta fase.
- **Detalle posterior:** estado «Revertido», referencia del contramovimiento, usuario, fecha y motivo; original y corrección quedan consultables y vinculados.
- **Restricciones visibles:** no ofrecer una segunda reversión; no permitir revertir una salida de venta por esta vía (explicar que requiere devolución, fuera de alcance); revertir una recepción no ofrece devolver pagos.
- **Interfaz ante stock negativo bloqueado:** mostrar producto y saldo y no revertir ninguna línea; si procede, recalcular recepción y stock sin borrar historial.
- **Criterios de aceptación de la tarjeta:** (1) la reversión exige motivo, conserva el original y crea un contramovimiento vinculado, sin poder ejecutarse dos veces; (2) un movimiento de Ventas o Compras se corrige desde su documento de origen, no desde una edición aislada de inventario; (3) el MVP permite revertir recepciones desde Compras si la salida resultante cumple la política de stock, ajustando cantidades recibidas sin devolver pagos; devoluciones de clientes fuera de fase.

### Hechos encontrados
- `backend/modules/inventory/domain/movement.py:114-129` — `StockMovement.reverse()` ya existe: marca el original `reversed`, devuelve el contramovimiento opuesto vinculado por `reverses_id`, y falla con `already_reversed` / `cannot_reverse_reversal`. El motivo es **opcional** (por defecto «Reversión de movimiento») y el contramovimiento no repite el origen (`source=None`).
- `backend/modules/inventory/application/movement_use_cases.py:163-185` — `ReverseMovement` bloquea el almacén, genera el contramovimiento, revalida la política de stock negativo si el contramovimiento es una salida y lanza `InsufficientStock`. Maneja **un** movimiento; no hay variante por documento.
- `backend/modules/inventory/services.py:71-77` — `reverse_movement()` está en la fachada pero **ningún endpoint ni módulo la usa** (solo tests: `inventory/tests/test_movements.py:173-192`).
- `backend/modules/inventory/api/movement_views.py:96-107` y `movement_urls.py` — la API de movimientos es de solo lectura (lista y detalle); `reversed_by` se expone solo como `{id}` (línea 63). No hay endpoint de reversión.
- `backend/modules/inventory/infrastructure/django/models.py:28-65` — `StockMovementModel` con restricción única `inv_mov_one_reversal_uniq` sobre `reverses_id` (una sola reversión por movimiento, también bajo concurrencia) y `status`.
- `backend/modules/inventory/domain/movement.py:34-41` — `SOURCE_TYPES`: `sales_order`, `purchase_receipt`, `inventory_adjustment`, `inventory_opening`; un movimiento sin origen es manual.
- `backend/modules/inventory/infrastructure/django/adjustment_repository.py:14-18` — el `status` del ajuste sale del movimiento vinculado, de modo que revertir su movimiento deja el ajuste «revertido» sin cambios de esquema.
- `backend/modules/inventory/api/insufficient_stock.py` — `InsufficientStockConflict` ya serializa 409 `insufficient_stock` con producto, almacén, solicitado, disponible y `lines` (todas las faltantes).
- `backend/modules/purchases/domain/enums.py:29-31` — `ReceiptStatus.REVERTED` **ya existe**, y `purchases/infrastructure/django/receipt_repository.py:52-57` (`received_totals`) solo suma recepciones `confirmed`; pero **nada** transiciona una recepción a `reverted`, ni hay campos de reversión en `ReceiptModel` (`purchases/infrastructure/django/models.py:72-87`).
- `backend/modules/purchases/domain/receipt.py:20-47` — `Receipt` es inmutable tras crearse (sin método de reversión). `purchases/domain/purchase.py:153-160` (`compute_reception_status`) y `:334` (`can_receive`) ya derivan el estado de recepción de lo recibido.
- `backend/modules/purchases/application/receipt_commands.py:51-99` — `RegisterReception` bloquea la compra (`for_update`), registra la recepción y las entradas de stock vía `StockEntry` (puerto). El modo (`inventory`/`documental`) se fija al confirmar.
- `backend/modules/purchases/infrastructure/adapters.py:56-76` — `StockEntryAdapter` es el único lugar que conoce la fachada de Inventario; las entradas usan `source_type='purchase_receipt'`, `source_id=<receipt_id>`, `source_line=<product_id>`; `movements_for()` lee el libro por origen.
- `backend/modules/purchases/application/receipt_queries.py:97-123` y `purchases/api/receipt_serializers.py:35-` — el detalle de recepción devuelve movimientos (id, producto, almacén, cantidad, referencia) pero no su estado ni su contramovimiento.
- `backend/modules/accounts/models.py:31-41` — el único rol existente es `admin`; el permiso por defecto exige usuario con empresa activa y rol admin (`accounts/api/permissions.py:16`). No hace falta modelo de permisos nuevo.
- `frontend/panel_admin/src/app/features/inventory/models/movement.ts:3-7,29-34` — la UI ya conoce el estado `reversed`, y `SOURCE_ROUTES` enlaza `sales_order` y `inventory_adjustment`; `purchase_receipt` no tiene ruta porque falta el id de la compra.
- `frontend/panel_admin/src/app/features/inventory/pages/movement-detail/movement-detail.component.html:51-92` y `adjustment-detail/` — el detalle ya muestra «Contramovimientos» con enlaces, sin acción.
- `frontend/panel_admin/src/app/features/purchases/models/receipt.ts:1-11` y `pages/reception-detail/` — la UI ya tiene la etiqueta/color «Revertida»; no hay acción ni datos de reversión.
- `frontend/panel_admin/src/app/features/purchases/components/purchase-cancel-dialog/` — patrón existente de diálogo con motivo obligatorio (`NgbModal`, `maxlength`, botón deshabilitado mientras esté vacío).

### Hipótesis / supuestos no confirmados
- Revertir un movimiento de **apertura de existencias** (`inventory_opening`) se considera «origen manual permitido». La tarjeta no lo nombra; se decide permitirlo (queda anotado en el ADR).
- Revertir una recepción **documental** (sin movimientos) es posible y solo cambia el documento.
- Si el módulo Inventario fue deshabilitado después de una recepción en modo `inventory`, no se permite revertirla (habría que corregir un libro que no se puede operar).

### Módulos y dependencias relacionadas
Inventario (contexto principal: libro de movimientos, ajustes) y Compras (recepciones; depende de Inventario solo por `StockEntryAdapter` y la fachada `inventory/services.py`). Ventas queda como origen que se **rechaza** (devoluciones fuera de fase). Sin cambios en Catálogo, Clientes, Gastos ni Reportes.

### Implementaciones similares existentes
Ajustes de existencias (`adjustment_views.py`, `adjustment_use_cases.py`) para endpoints con motivo, 409 con código y `InsufficientStockConflict`; cancelación de compra (`purchase_views.py` `PurchaseCancelView`, `purchase-cancel-dialog`) para acción con motivo obligatorio en Compras; `RegisterReception`/`StockEntryAdapter` para la integración Compras → Inventario.

### Comportamiento actual
No existe forma de revertir desde la API ni la UI: solo hay la fachada sin consumidores. Una recepción registrada no puede deshacerse; el único camino es un ajuste de inventario, que no corrige las cantidades recibidas de la compra.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, módulos solo por fachada, estados por métodos del agregado, `Decimal` para cantidades, nunca editar migraciones aplicadas, sin dependencias nuevas sin avisar. `docs/architecture/ddd.md` (Reporting solo lee). Reglas de INV-07 ya implementadas en el dominio (una reversión por movimiento, el contramovimiento no se revierte).

### Riesgos identificados
- Reversión **multi-línea todo-o-nada** de una recepción: requiere una sola sección crítica en Inventario (bloqueo del almacén) y orden consistente de bloqueos (compra → almacén, igual que al recibir) para no provocar interbloqueos.
- Cambio de comportamiento de `reverse`: hacer el motivo obligatorio rompe tests existentes que lo omiten.
- Consistencia entre dos módulos: si la reversión del libro tiene éxito y falla el guardado de la recepción, todo debe deshacerse en la misma transacción.
- Concurrencia: dos reversiones simultáneas de la misma recepción o movimiento (cubierta por la restricción única y el bloqueo de la compra).
- Revertir una entrada ya consumida bajo política de stock negativo bloqueado debe fallar sin efectos parciales.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — toca dos bounded contexts (Inventario y Compras) con contrato API nuevo en ambos, migración en `purchases_receipt`, nueva transición de estado de dominio con integridad entre módulos (todo-o-nada transaccional) y reglas de finanzas/stock.

### Diseño requerido
**SI** — acciones y diálogos nuevos en el detalle de movimiento, de ajuste y de recepción, con estados de error de stock.

## Diseño
Ver [DDR-inventario-revertir-movimientos-dialogo-reversion](../design/DDR-inventario-revertir-movimientos-dialogo-reversion.md).

## Arquitectura
Ver [ADR-inventario-revertir-movimientos-contramovimientos](../adr/ADR-inventario-revertir-movimientos-contramovimientos.md).

## Plan
Ver [PLAN-2026-10-30-inventario-revertir-movimientos](../plans/PLAN-2026-10-30-inventario-revertir-movimientos.md) (v1, COMPLETO). **Specification readiness: READY.**

Decisiones tomadas sin consultar (constan en el PLAN/ADR, ninguna cambia un criterio de la tarjeta): apertura de existencias y movimientos sin origen son revertibles; recepción documental revertible sin efecto de stock; recepción en modo inventario con Inventario deshabilitado no es revertible (409 `inventory_unavailable`); sin permisos nuevos (solo existe el rol admin).

## Implementación

**Resumen.** Reversión de movimientos manuales en Inventario y reversión completa de recepciones en Compras, según PLAN v1.

**Backend Inventario** (INV-01..04, AC-01..05, AC-11..14): `StockMovement.reverse` exige motivo (≤200); `reversal_block` decide por origen/estado; `ReverseMovement(manual_only)`; nuevo `ReverseSourceMovements` (todo-o-nada, bloqueo por almacén en orden, política de stock sumada por producto/almacén); fachada `reverse_source_movements`; `POST /api/stock-movements/<id>/reverse/`; el detalle añade `reversal` y expande `reversed_by` (id, referencia, fecha, usuario, motivo). Tests: `inventory/tests/test_reversal.py` (+ ajustes a tests existentes para el motivo obligatorio).

**Backend Compras** (INV-05..07, AC-06..10, AC-13, AC-14): migración `0007_receipt_reversal` (aditiva); `Receipt.revert`/`moved_stock`; `Purchase.recompute_reception`; puerto `StockEntry.reverse_entries` y adaptador; caso de uso `RevertReception` (compra bloqueada → almacén bloqueado; documental sin stock; `inventory_unavailable`; 409 `insufficient_stock` con todas las líneas); `POST /api/purchases/<id>/receipts/<rid>/revert/`; el detalle añade `can_revert`, `reversal` y estado/contramovimiento por movimiento. Tests: `purchases/tests/test_receipt_revert.py` (dominio, aplicación, API, concurrencia, rollback entre módulos).

**Frontend** (AC-15, AC-16, UI-01..05): `MovementReverseDialogComponent` (movimiento y ajuste) y `ReceiptRevertDialogComponent`; botón «Revertir»/«Revertir recepción» según `reversal.allowed`/`can_revert`; bloque «Reversión»; columna «Estado» de movimientos en la recepción. Pantalla de referencia: detalle (`product-detail`) y diálogo de `purchase-cancel-dialog`; se reutilizó `app-insufficient-stock-alert`. `docs/design/design-system.md` documenta el patrón «Diálogo de acción irreversible con motivo».

**Verificación propia (no es el Quality Gate).** Backend `manage.py test`: 1233 tests OK con PostgreSQL. Karma (`features/`): mis specs pasan; 71 fallos `should create` de la plantilla Oreva (sin `ActivatedRoute`) y `app.component.spec.ts` (`title`) ya existían y no se tocaron (este último impide compilar `ng test` completo; se movió temporalmente para ejecutar). `ng lint` sin hallazgos en archivos del cambio.

**Desviaciones del plan.** (1) Motivo obligatorio también en la fachada `reverse_movement` (se actualizaron llamadas de tests). (2) El diálogo ejecuta la llamada a la API y se cierra con el resultado, para mostrar errores dentro del diálogo sin perder el motivo. (3) El detalle de ajuste ofrece «Revertir» siempre que esté confirmado; el servidor es la barrera. (4) Se eligió `RevertStockShortage` en Compras para llevar las líneas ya nombradas (nombre/unidad salen de las líneas de la recepción).

**Deuda técnica.** Sin enlace desde un movimiento de compra a su recepción (falta el id de compra). Suites de plantilla y `app.component.spec.ts` rotas de antes. Para correr tests en este worktree se copió `backend/.env` (ignorado por git, con autorización de la persona) y se enlazó `node_modules` del checkout principal; ninguno se versiona.

## Review

**Quality Gate ciclo 1 (subagente aislado): PASS.** Sin Critical/High/Medium. Evidencia: backend `manage.py test` 1233 tests OK; `makemigrations --check` sin cambios; `npm run lint` limpio; `npm run build` OK; Karma 940 OK / 71 FAILED, todos "should create" de la plantilla Oreva ajenos al diff (preexistentes); bandit sin hallazgos. No realizados: ruff (no instalado), `npm audit` (sin lockfile), **revisión visual en navegador (no verificada)**. Límites DDD, orden de bloqueos y atomicidad revisados sin hallazgos.

Hallazgos Low abiertos (no bloquean):
- [REV-01](../reviews/REV-2026-10-30-inventario-revertir-movimientos-01.md) SPECIFICATION: el PLAN cita `/api/inventory/movements/...` pero la ruta real es `/api/stock-movements/...`.
- [REV-02](../reviews/REV-2026-10-30-inventario-revertir-movimientos-02.md) IMPLEMENTATION: la concurrencia de `RevertReception` se prueba solo con stock documental y falta prueba de 403 por rol.
- [REV-03](../reviews/REV-2026-10-30-inventario-revertir-movimientos-03.md) DESIGN: el contramovimiento hereda la referencia del original.

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/40 listo para aprobación humana (no se mergea automáticamente). Cambio sensible: toca base de datos (migración `purchases/0007_receipt_reversal`, aditiva) y lógica de stock/finanzas respaldada por el ADR `ADR-inventario-revertir-movimientos-contramovimientos`; requiere aprobación humana del merge.
