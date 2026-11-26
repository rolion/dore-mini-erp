# TASK-registrar-produccion-refrigeracion: Registrar producción real y pasar el lote a refrigeración

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-registrar-produccion-refrigeracion (base: `produccion`)
**Pull Request:** _se enlaza al abrirlo (base `produccion`)_
**Fuente:** https://trello.com/c/4reKLdFV/4-dore-prod-004-registrar-producci%C3%B3n-real-y-pasar-el-lote-a-refrigeraci%C3%B3n

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado desde DORE-PROD-004 | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE: transacción entre Producción, Inventario y Costeo | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |

## Investigación

### Requerimiento
Tarjeta DORE-PROD-004 (insumo, no Specification aprobada). Historia: como operario de DORE quiero registrar cuánto consumí y cuánto produje al ingresar un lote a refrigeración para que Inventario refleje lo que ocurrió. Desde la orden **En preparación**, la acción **Pasar a refrigeración** captura consumo real, cantidad elaborada y fecha y hora de ingreso; vincula la orden a su lote y registra los movimientos en el Inventario existente.
Comportamiento esperado de la tarjeta:
1. El formulario propone las cantidades previstas y permite corregir consumo y rendimiento reales (120 planificados, 118 reales → el lote ingresa con 118).
2. Una sola transacción: descuenta ingredientes, ingresa las unidades a granel al almacén con su lote y pasa la orden a **En refrigeración**.
3. Si falta un ingrediente, la pantalla muestra el faltante y la orden sigue En preparación. Reintento o doble clic no duplican movimientos.
4. La entrada conserva el costo de los insumos realmente consumidos según la valoración de Inventario; el lote tiene saldo físico y queda bloqueado para empaque.
Dependencias: DORE-PROD-002 (lotes, ya integrado) y DORE-PROD-003 (órdenes, ya integrado).
Aclaración del usuario: «usa la rama produccion» → el trabajo parte de `origin/produccion` y el PR apunta a `produccion`.

### Hechos encontrados
- Base `origin/produccion` (d1ec6e90) ya trae recetas, órdenes (`production/domain/production_order.py:44-114`, estados `draft`/`in_preparation`) y lotes de Inventario.
- `ProductionOrder.start` solo cambia estado y `started_at`; no hay consumo ni lote (`production_order.py:106-111`). `application/orders.py:111` (`ProductionOrders.start`) lo orquesta y valida almacén activo.
- La API de órdenes es `api/production-orders/` con `required_modules=('production',)` (`api/order_views.py:77-120`); el repositorio usa `select_for_update` y contador por empresa.
- Inventario expone por fachada `create_lot` (lote en refrigeración + entrada inicial, un solo `commit`, idempotente por `(source_type, source_id)`, lanza `LotNumberingRejected` sin período fiscal abierto), `record_outputs` (salidas de un documento, todas o ninguna, idempotentes por `(source_type, source_id, producto)`, lanzan `InsufficientStock` con `shortages`), `get_balances`, `allow_negative_stock`, `lock_company_stock` (`inventory/services.py:98-371`).
- `production_order` ya es un `SOURCE_TYPES` válido (`inventory/domain/movement.py:40`) y `_BLOCKED_SOURCES` solo bloquea la reversión manual de ventas y compras (`movement.py:146-151`); el ADR de lotes dejó a PROD-004 decidir las reversiones del origen `production_order` (`ADR-lotes…:consecuencias`).
- Costeo (`costing/services.py:44-99`): `cost_outputs` valoriza salidas al promedio vigente (lanza `CostUnavailable` sin valoración adoptada o sin promedio; no genera asiento) y `cost_receipt` actualiza el promedio con `(producto, cantidad, costo unitario)` ya registrada en stock. Ventas lo usa tolerando `CostUnavailable` salvo que haya cobertura contable (`sales/infrastructure/adapters.py:420-440`); Compras llama `cost_receipt` (`purchases/infrastructure/adapters.py:113`).
- Mapa de dependencias: `production → {catalog, inventory}` (`sales/tests/test_boundaries.py:23`); Costeo depende de Inventario.
- Frontend: `features/production/pages/order-{list,form,detail}` con acción Iniciar en el detalle (DDR de PROD-003); patrón de pantalla de referencia `purchase-detail` + formularios con líneas.

### Hipótesis / supuestos no confirmados
Ver «Supuestos» del PLAN (S1-S7); se dejan como decisiones por defecto que el usuario puede revertir sin tocar Specification.

### Módulos y dependencias relacionadas
Producción (agregado, caso de uso, API, UI), Inventario (`create_lot`, `record_outputs`, `reversal_block`), Costeo (`cost_outputs`, `cost_receipt`), Modularidad (`production` requiere `inventory`; Costeo es opcional).

### Implementaciones similares existentes
Entrega de ventas: salidas + costeo en una transacción (`sales/infrastructure/adapters.py`); recepción de compras: entrada + `cost_receipt`.

### Comportamiento actual
Una orden En preparación no puede avanzar: no hay consumo, lote ni estado «En refrigeración».

### Restricciones
`Decimal` para cantidades y dinero; no editar migraciones aplicadas; módulos solo por `services`; aislamiento por `company_id`; sin texto hardcodeado (i18n es/en/pt); sin dependencias nuevas.

### Riesgos identificados
Atomicidad entre tres módulos (todo en un `transaction.atomic`); doble clic/reintento (bloqueo de la orden + idempotencia por origen); lote sin período fiscal abierto (error accionable); costo cero o ausente; reversión manual de los movimientos desde Inventario rompería la trazabilidad (se bloquea).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — orquesta una transacción entre tres módulos, agrega estado y datos reales a la orden (migración), y fija la política de reversión y costeo de producción.

### Diseño requerido
**SI** — nuevo formulario con líneas editables (consumo real), panel de faltantes y nuevos estados en lista y detalle.

## Diseño
`docs/design/DDR-registrar-produccion-refrigeracion-pasar-a-refrigeracion.md`.

## Arquitectura
`docs/adr/ADR-registrar-produccion-refrigeracion-transaccion-y-costo.md`.

## Plan
`docs/plans/PLAN-2026-11-26-registrar-produccion-refrigeracion.md` (v1, COMPLETO, READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
