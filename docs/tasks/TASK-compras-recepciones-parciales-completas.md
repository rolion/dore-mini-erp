# TASK-compras-recepciones-parciales-completas: Registrar recepciones parciales o completas de compras (PB-COM-004)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-compras-recepciones-parciales-completas
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/33

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN | Veredicto NEEDS_ARCHITECTURE; diseño requerido | delivery-start |
| 2026-10-30 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-10-30 | ARCHITECTURE → PLANNING | ADR escritos | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |
| 2026-10-30 | ENGINEERING → REVIEW | Implementación y pruebas escritas | delivery-build |
| 2026-10-30 | REVIEW → PUBLISH | Quality Gate ciclo 1: PASS condicionado (sin PostgreSQL ni revisión visual); REV-01 (Low) corregido (skipUnless PostgreSQL) | delivery-publish |

## Investigación

### Requerimiento
PB-COM-004 · Registrar recepciones parciales o completas (Módulo Compras, P1, dependencia PB-COM-003). Como administrador, quiero registrar las cantidades recibidas para distinguir lo comprado de lo entregado por el proveedor.

- **Acceso y vistas:** detalle de Compra → pestaña «Recepciones» → «Registrar recepción»; formulario y detalle de cada recepción. No se añade un menú lateral.
- **Tabla de recepciones:** referencia, fecha, estado confirmada/revertida y usuario. El detalle muestra productos, cantidades recibidas, almacén cuando aplique y movimientos vinculados.
- **Formulario:** fecha y líneas con producto de solo lectura, cantidad comprada, recibida acumulada, pendiente y cantidad a recibir. Con Inventario activo, almacén para los productos controlados; sin él, no se exige ni se muestra.
- **Acciones:** completar cantidades, revisar y «Confirmar recepción». Se admite recibir solo parte de las líneas; las de cantidad cero se omiten y debe haber al menos una positiva.
- **Interfaz:** no permitir exceder pendientes; mostrar pendientes actualizados tras confirmar. El estado pasa a parcial o completa según el acumulado y no depende del pago.
- **AC:** (1) una compra confirmada admite varias recepciones con fecha y cantidades por ítem; (2) no se acepta cantidad negativa, cero ni acumulada superior a la comprada, y el estado de recepción se calcula (pendiente, parcial, completa); (3) sin Inventario la recepción es documental; con Inventario, los ítems controlados requieren un almacén activo y su entrada se confirma junto con la recepción.

### Hechos encontrados
- PB-COM-003 está en `main` (PR #31). `Purchase` ya tiene `reception_status: ReceptionStatus` (`not_received|partial|received`) y `payment_status`, preparatorios y sin escritor (`backend/modules/purchases/domain/purchase.py:217-219`, `domain/enums.py:10-13`); columna `reception_status` ya existe en `purchases_purchase` (migración `0003_purchase_lifecycle`, `infrastructure/django/models.py:40`).
- La cancelación ya se bloquea con actividad: `has_activity` y `cancel()` lanzan `PurchaseCancellationBlocked` si `reception_status != not_received` (`purchase.py:254-257,294-295`); `allowed_actions` hoy es `edit/confirm/cancel` (`purchase.py:265-269`). El ADR de confirmar/cancelar dejó dicho que recepción «deberá añadir métodos al agregado que muevan `reception_status`» (`docs/adr/ADR-confirmar-cancelar-compras-ciclo-de-vida-y-contrato.md`, Consecuencias).
- No existen recepciones: ni tabla, ni agregado, ni endpoints. La migración más reciente de Compras es `0003`. El detalle del frontend tiene una sola pestaña «Resumen» y el botón «Registrar recepción» deshabilitado con «próximamente» (`frontend/panel_admin/src/app/features/purchases/pages/purchase-detail/purchase-detail.component.html:21-25,114-116`).
- `PurchaseRepository.save` borra y recrea las líneas conservando sus `id` (`infrastructure/django/purchase_repository.py:63-73`); una compra confirmada no cambia de líneas, pero **no puede haber FK desde otra tabla a `PurchaseItemModel`**: se referencia por UUID.
- Un producto aparece una sola vez por compra (`build_items` rechaza duplicados, `purchase.py:180-181`), por lo que `purchase_item_id` identifica unívocamente la línea.
- Inventario ya contempla el origen: `SOURCE_TYPES['purchase_receipt']` («Recepción de compra», módulo `purchases`) en `backend/modules/inventory/domain/movement.py:37`, y la fachada `inventory/services.py` expone `record_movement` (entrada `in`, idempotente por `(source_type, source_id, source_line)`; `services.py:52-68`), `get_stock_products`, `list_active_warehouses` y `list_movements_for_source` (`services.py:126-179`).
- Patrón a seguir: Ventas entrega con salida de stock. `DeliverOrder` orquesta, `StockOutputAdapter` (`sales/infrastructure/adapters.py:95-147`) llama a la fachada solo si `module_gate.is_enabled(company, 'inventory')`; un solo almacén por entrega; vista previa `delivery-preview`; todo dentro de la `transaction.atomic` de `_run`; no se persiste nada del movimiento en Ventas (se lee del libro). Ver `docs/adr/ADR-ventas-inventario-salida-al-entregar-orquestacion-y-contrato.md`.
- Frontera de módulos: `purchases` solo depende de `catalog` (`sales/tests/test_boundaries.py:17`); Ventas añadió `inventory` en su entrada (línea 18) y se haría igual para Compras. `RecordMovement` valida producto controlado, fracciones y almacén activo bajo el bloqueo del almacén (`inventory/application/movement_use_cases.py:36-66`).
- Idempotencia por identificador del cliente ya usada en Inventario (`adjustment_id`, `inventory/api/adjustment_views.py:126-140`) y en el formulario de apertura (clave generada al abrir; `design-system.md` §5).
- Frontend: detalle de compra con `ngbNav` simple (pestaña «Resumen» fija), diálogos `NgbModal` de confirmar/cancelar, `purchases.routes.ts` con `:id` al final, `purchases-api.service.ts` y `testing/purchase-fixtures.ts` (`features/purchases/…`). Pantalla de referencia para formulario con líneas y resumen: `features/inventory/pages/stock-opening`; para detalle con pestañas: `purchase-detail`; para tarjeta de movimientos del documento: `features/sales/components/stock-output-card`.
- La lista de Movimientos filtra por `source_type` y `source_id` (ADR salida al entregar, decisión 8) y la etiqueta «Salida por venta» es presentación en el frontend.

### Hipótesis / supuestos no confirmados
Reversibles con aprobación del usuario; ninguno bloquea:
- **H-01** La referencia de la recepción es provisional y derivada del id, `REC-` + 8 hex mayúsculos (igual que `COM-` en la compra); la numeración correlativa es otra task.
- **H-02** Un único almacén por recepción, que aplica a todos los productos controlados (como en la entrega de Ventas). La recepción de cada producto en almacenes distintos se hace con recepciones distintas.
- **H-03** «Revertida» existe como estado de la recepción para el contrato y la tabla, pero **esta task no incluye la acción de revertir**. Solo las recepciones `confirmed` suman al acumulado. Revertir (que genera el contramovimiento) queda para una task futura.
- **H-04** La fecha de recepción es obligatoria y no puede ser futura; no tiene cota inferior (los pedidos pueden registrarse después de recibirse). Por defecto, hoy.
- **H-05** La fecha del movimiento de inventario es el instante del registro (`now`); la fecha de recepción del documento puede ser anterior y se muestra por separado.
- **H-06** Solo se reciben compras `confirmed`; en borrador o cancelada → 409. No hay recepción sobre compras cuyo producto fue desactivado después: se valida solo contra el snapshot y el catálogo para fracciones.
- **H-07** Con Inventario habilitado, los productos que controlan stock (`tracks_stock`) generan entrada; los demás solo reciben documentalmente. Con Inventario deshabilitado no se generan movimientos y activar luego el módulo no los genera retroactivamente (igual que Ventas).
- **H-08** El API rechaza cantidad 0 en una línea enviada (AC «no se acepta cero»); es la interfaz la que omite las líneas con cantidad cero antes de enviar.
- **H-09** Idempotencia: el cliente envía un `receipt_id` (UUID) generado al abrir el formulario; repetir la petición con ese id devuelve la misma recepción sin duplicar acumulados ni movimientos.
- **H-10** Sin notas libres en la recepción (no pedidas); se pueden añadir después.

### Módulos y dependencias relacionadas
Compras (propietario). Inventario (integración opcional, solo por `inventory.services`). Catálogo (fracciones y unidad por el puerto ya existente). Modularity (`module_gate`) para saber si Inventario está habilitado. Sin cambios en Gastos ni Pagos (el estado de pago no se toca).

### Implementaciones similares existentes
Entrega de pedidos con salida de stock (Ventas) y su diálogo/`stock-output-card`; apertura de existencias iniciales (formulario con líneas y resumen, idempotencia por clave); ajustes de inventario (`adjustment_id` del cliente).

### Comportamiento actual
No se puede registrar ninguna recepción. Una compra confirmada solo muestra «Sin recibir» y un botón deshabilitado. Cancelarla siempre es posible porque `reception_status` no se mueve.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, dinero/cantidades en `Decimal`, no editar migraciones aplicadas, dominio sin Django, módulos entre sí solo por fachada, estados por métodos del agregado, frontend por feature con Reactive Forms y tipos explícitos, sin dependencias nuevas sin aviso. Sistema de diseño de `docs/design/design-system.md`.

### Riesgos identificados
- Atomicidad entre dos módulos: la recepción y sus entradas de stock deben confirmarse o fallar juntas (mitigado por la transacción de `_run` y el bloqueo de filas).
- Concurrencia: dos recepciones simultáneas no deben superar lo comprado (bloqueo de la compra con `select_for_update`).
- Primera dependencia `purchases → inventory`: actualizar `test_boundaries.py` y `ddd.md`.
- Doble envío del formulario: cubierto por `receipt_id` idempotente.
- Referencia por UUID a líneas de la compra sin FK (la compra recrea sus líneas al guardar): se mantiene el `id` de cada línea, probado en el repositorio.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo agregado con persistencia propia (tablas y migración), primera dependencia `purchases → inventory` con una transacción que cruza dos módulos, transiciones del estado de recepción y un contrato API nuevo.

### Diseño requerido
**SI** — pantallas nuevas (pestaña «Recepciones», formulario con resumen, detalle de recepción) y un flujo de varios pasos.

## Diseño
`docs/design/DDR-compras-recepciones-parciales-completas-formulario-y-detalle-recepcion.md` (Propuesto). Parte de las plantillas «Detalle con pestañas», «Formulario con líneas y paso de resumen» y «Lista de solo lectura» de `docs/design/design-system.md`; sin componente compartido nuevo.

## Arquitectura
- `docs/adr/ADR-compras-recepciones-parciales-completas-modelo-y-persistencia.md` — agregado `Receipt`, regla de acumulado y estado, tablas y migración `0004`.
- `docs/adr/ADR-compras-recepciones-parciales-completas-integracion-inventario-y-contrato.md` — orquestación Compras→Inventario, atomicidad, idempotencia y contrato API.

## Plan
`docs/plans/PLAN-2026-10-30-compras-recepciones-parciales-completas.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación
**Backend** (`backend/modules/purchases/`): `domain/receipt.py`, `Purchase.receive`/`can_receive`/`compute_reception_status`, `ReceiptStatus` y excepciones (INV-01…07, 12; AC-01…06, 12); `infrastructure/django/{models,mappers,receipt_repository}.py` y migración `0004_receipts` (INV-02, 07); `application/receipt_commands.py` (`RegisterReception`: bloqueo, entradas de stock, idempotencia; INV-08…11), `receipt_queries.py` (formulario, lista, detalle) y puertos; `infrastructure/adapters.py` (`StockEntryAdapter` sobre `inventory.services`); `api/receipt_{views,serializers}.py` y rutas (AC-13…16). Detalle de compra con `received_quantity`/`pending_quantity`. `test_boundaries` (`purchases → inventory`) y `test_enforcement` actualizados.
**Frontend** (`features/purchases/`): `models/receipt.ts`, `receipts-api.service.ts`, `reception-quantities.ts`, componente `purchase-receipts-tab`, páginas `reception-form` (dos pasos) y `reception-detail`, pestañas y columnas Recibida/Pendiente en `purchase-detail`, rutas; en `features/inventory` la etiqueta «Entrada por compra» y el filtro por recepción (AC-18…25). Pantallas de referencia: Formulario con líneas y paso de resumen, Detalle con pestañas, `stock-output-card`; sin componente compartido nuevo.
**Docs:** `ddd.md`, `modulos-implementados.md` y notas en `design-system.md`.
**Verificación local:** pruebas de dominio/aplicación de Compras y `test_boundaries` pasan; Karma de `features/purchases` y `features/inventory` (274) pasa; `ng lint` y `ng build` pasan. **No ejecutado:** pruebas de backend con BD (API, repositorio, concurrencia, `test_enforcement`): no había credenciales de PostgreSQL. `app.component.spec.ts` falla al compilar en `main` (`title`), ajeno a esta task; se excluyó temporalmente para correr Karma.
**Desviaciones del plan:** la lista de recepciones no incluye `warehouse` (solo el detalle); `GetPurchase` recibe opcionalmente el repositorio de recepciones. **Deuda:** revertir recepciones (H-03); `ListReceipts` no pagina en BD (pocas por compra).

## Review
Ciclo 1 (subagente aislado): **PASS condicionado**. Ejecutado: 95 pruebas de dominio/aplicación/límites OK, `check`, `makemigrations --check`, `bandit` sin hallazgos, `ng lint`, `ng build`, Karma 274 OK. No ejecutado: pruebas con PostgreSQL y revisión visual. Hallazgo: [REV-01](../reviews/REV-2026-10-30-compras-recepciones-parciales-completas-01.md) (Low, IMPLEMENTATION, corregido con `skipUnless`): falta `skipUnless` de PostgreSQL en `test_receipt_concurrency.py`.

## Verificación posterior (PostgreSQL y visual)
Suite completa del backend con PostgreSQL real: 1124 pruebas OK (incluye concurrencia AC-17). Destapó un fallo real: `accounts/test_guards.py` no conocía `ReceiptItemModel` como tabla hija; corregido. Revisión visual en el navegador (escritorio y móvil) del flujo completo con Inventario: sin hallazgos; observación menor: la columna Origen en Movimientos muestra el id de la recepción sin enlace.

## Publicación
PR #33 con descripción completa. Cambios sensibles: base de datos (migración `0004`) y dependencia `purchases → inventory` (ADR de integración). Falta de parte humana: correr las pruebas con PostgreSQL, revisión visual y aprobar el merge. No se mergea.
