# TASK-registrar-produccion-refrigeracion: Registrar producción real y pasar el lote a refrigeración

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-registrar-produccion-refrigeracion (base: `produccion`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/134 (base `produccion`)
**Fuente:** https://trello.com/c/4reKLdFV/4-dore-prod-004-registrar-producci%C3%B3n-real-y-pasar-el-lote-a-refrigeraci%C3%B3n

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado desde DORE-PROD-004 | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE: transacción entre Producción, Inventario y Costeo | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR abiertos | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa; pruebas de API del backend pendientes de BD | delivery-build |

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
**Backend (Producción):** dominio `ProductionOrder.validate_refrigeration/refrigerate` y estado `refrigerating` (INV-01..03, AC-02, AC-06); caso de uso `ProductionOrders.refrigerate` con puertos `StockGateway`/`CostGateway` y adaptadores `InventoryStock`/`CostingGateway` (INV-04, INV-05, INV-07, AC-03..AC-05, AC-07); migración `0003` aditiva; API `POST …/refrigerate/` con 409 `insufficient_stock` (lista de faltantes) y códigos de período fiscal (API-01..03, AC-09); `inventory/domain/movement.py` bloquea la reversa manual de `production_order` (INV-08, AC-10); `inventory.services.record_outputs` acepta `occurred_at` (aditivo); `production → costing` en `test_boundaries`; nota en `ddd.md`.
**Frontend:** pantalla `order-refrigerate` (formulario con consumo real por línea, cantidad elaborada y fecha/hora; faltantes por fila; botón deshabilitado mientras envía), sección «Producción registrada» y acción en el detalle, badge/filtro «En refrigeración» en la lista, servicio y modelos, i18n es/en/pt (AC-11). Pantallas de referencia: `purchase-form`/`order-detail` (DDR). Sin componentes compartidos nuevos.
**Pruebas escritas:** dominio (`test_order_domain.py`), API (`test_order_api.py`: AC-01..AC-10, EDGE-01/03) y Karma (servicio, detalle, pantalla). **Ejecutadas:** dominio (9 OK), Karma de `production` (73 OK), `npm run lint` e `i18n:check` OK, `ruff`/`flake8` limpios en lo cambiado. **No ejecutadas:** las pruebas de API del backend y las suites de `inventory`/`costing` — el entorno no tiene `DATABASE_URL` y no se leen credenciales (`.env`); quedan pendientes para `delivery-publish`/el usuario.
**Desviaciones:** ninguna de alcance. Detalle: el estado/campos se guardan por el repositorio existente; `entered_at` exige zona horaria (el formulario envía ISO UTC).
**Deuda técnica:** `test_order_api.py` crece (no se separó la clase para no duplicar el `setUp`).

## Review
_Pendiente_

## Publicación
_Pendiente_
