# TASK-valorar-recepciones-consumos-costo-historico: Valorar recepciones y consumos con costo histórico (PB-VAL-002)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-valorar-recepciones-consumos-costo-historico
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/42
**Fuente:** https://trello.com/c/vlUMdnzZ

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta Trello PB-VAL-002 | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Cruza Inventario, Compras, Ventas y Costeo; tablas nuevas; pantallas nuevas | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY, PR abierto | delivery-start |
| 2026-10-30 | ENGINEERING → REVIEW | Implementación completa según el PLAN v1 | delivery-build |

## Investigación

### Requerimiento
Tarjeta Trello https://trello.com/c/vlUMdnzZ — **PB-VAL-002 · Valorar recepciones y consumos con costo histórico** (P2, módulo Inventario y valoración; dependencias PB-VAL-001 y PB-INT-001). Insumo, no Specification aprobada.

Como administrador, valorar entradas y salidas para conocer el costo aplicado a materiales e intermedios. Vistas: sección «Valoración» en Detalle de Recepción y en Movimientos; consulta por producto, origen y fecha, visible con la capacidad habilitada. Datos: cantidad, costo unitario, valor del movimiento, promedio anterior/nuevo, origen del costo y estado valorado/pendiente. Las recepciones usan el precio unitario de la compra (independiente del precio de venta). Acciones: consultar la fuente del costo; las correcciones requieren validar su impacto; sin edición directa del costo de un movimiento ya consumido.

Criterios de la tarjeta:
1. Cada recepción parcial incrementa cantidad y valor al precio de compra acordado; pagar al proveedor no revalora stock.
2. Las salidas fijan el costo promedio vigente al confirmarse y no cambian ante compras posteriores; el detalle conserva su snapshot.
3. Entradas de producción se valoran con PB-CST-002. Ajustes positivos requieren valor explícito y los negativos consumen el valor vigente; restringir confirmaciones sin valoración válida.
4. En inventario valorado no se admiten saldos negativos ni operaciones retroactivas que exijan recalcular consumos (bloquear y explicar). La reversión de una recepción se bloquea si exige revalorar salidas posteriores.
5. Fuera de alcance: impuestos recuperables, fletes distribuidos, otras monedas, FIFO, valoración fiscal.

Decisiones del usuario (2026-10-30, `AskUserQuestion`): (a) tras adoptar, la valoración **sigue aplicándose aunque Costeo se deshabilite** (el módulo solo controla pantallas y API de consulta); (b) el ajuste positivo se valora con **valor total en BOB** (costo unitario derivado); (c) alcance **backend + UI completa**.

### Hechos encontrados
- `backend/modules/costing/domain/valuation.py:149` — `ValuationAdoption` inmutable; `compute_unit_cost` a 6 decimales `ROUND_HALF_UP` (`:28`); `ValuationLine.create` valida Pendiente/costo cero (`:86`). Método `weighted_moving_average` (`:14`).
- `backend/modules/costing/infrastructure/django/models.py:6,22` — tablas `costing_valuation_adoption` (única por empresa) y `costing_valuation_line`; migración `costing/0001`.
- `backend/modules/costing/application/use_cases.py:108` — `AdoptValuation` toma `stock.locked()` (bloqueo de todos los almacenes) y compara con `snapshot()`.
- `backend/modules/inventory/services.py:204` — `lock_company_stock`, `get_company_stock`: fachada que Costeo ya consume.
- `backend/modules/inventory/application/movement_use_cases.py:26,87,163` — `RecordMovement`, `RecordOutputs` y `ReverseMovement` son la única vía que inserta movimientos; todas toman `repository.locked(warehouse_id)` y consultan `InventoryPolicy.allow_negative_stock()` (`:70,:147,:177`).
- `backend/modules/inventory/application/adjustment_use_cases.py:73` — `ConfirmAdjustment` registra el movimiento de ajuste (entrada o salida según el signo de la diferencia) vía `RecordMovement`.
- `backend/modules/inventory/domain/movement.py:34` — `SOURCE_TYPES`: `sales_order`, `purchase_receipt`, `inventory_adjustment`, `inventory_opening`. No existe tipo de origen de producción.
- `backend/modules/purchases/infrastructure/adapters.py:60` — `StockEntryAdapter.register_entries` registra una entrada por línea de recepción (`source_type='purchase_receipt'`, `source_id=receipt_id`, `source_line=product_id`) sin precio; las líneas de compra tienen `unit_price` Decimal y moneda fija `BOB` (`backend/modules/purchases/domain/purchase.py:22,137`).
- `backend/modules/purchases/application/receipt_commands.py:85` — `_enter_stock` solo con Inventario habilitado; la recepción guarda su `inventory_mode`.
- `backend/modules/sales/infrastructure/adapters.py:145` — Ventas obtiene salidas por `record_outputs` al entregar un pedido.
- `backend/modules/inventory/services.py:72` — `reverse_movement` existe en la fachada; ningún módulo de negocio lo llama hoy.
- `backend/shared/stock_history.py` — patrón de **puerto neutro con proveedor registrado al arrancar**, usado para que Catálogo no importe Inventario.
- `backend/modules/modularity/domain/modules.py:26` — `costing` requiere `inventory`; deshabilitar `inventory` queda bloqueado por dependientes.
- `docs/adr/ADR-iniciar-valoracion-inventario-costeo-modulo-costeo-y-adopcion.md` — decisión previa: no guardar costo en `StockMovementModel`, Costeo lee Inventario solo por `services.py`.
- Frontend: `frontend/panel_admin/src/app/features/inventory/pages/{valuation,movement-detail,movement-list,adjustment-form}`; la recepción vive en `features/purchases`.

### Hipótesis / supuestos no confirmados
- «Pendiente» de la tarjeta: con la restricción de confirmar sin valoración válida, ningún movimiento posterior a la adopción puede quedar pendiente. Se interpreta que los movimientos anteriores al corte quedan **«Cubierto por la adopción»** (sin costo propio) y que `pending` no se persiste. Si la persona espera otra cosa, se ajusta en la revisión.
- Una recepción con precio unitario 0 se acepta como costo 0 (el precio 0 de la compra ya es una declaración explícita en Compras).
- «Operación retroactiva»: movimiento valorado con `occurred_at` anterior al último movimiento valorado del producto o al corte. Hoy solo la apertura de existencias pasa `occurred_at`.
- PB-CST-002 (costo de producción) no existe: las entradas de producción quedan fuera, con punto de extensión documentado.

### Módulos y dependencias relacionadas
Costeo (propietario), Inventario (movimientos y puerto), Compras (precio de recepción), Ventas (salidas, sin cambios de contrato), Modularidad (estado del módulo, sin cambios).

### Implementaciones similares existentes
Puerto neutro `shared/stock_history.py`; saldo bajo bloqueo en `RecordMovement._check_balance`; réplica idempotente de `AdoptValuation._replay`; sección dentro de detalle en `movement-detail` y `valuation`.

### Comportamiento actual
Inventario solo maneja cantidades; las recepciones crean entradas sin costo y las ventas salidas sin costo. Existe una adopción de valores iniciales por producto y nada más (sin promedio móvil, sin valor por movimiento).

### Restricciones
`Decimal` para dinero; aislamiento por `company_id`; no editar migraciones aplicadas (migración nueva `costing/0002`); los módulos solo se importan por `services.py`/puertos; Inventario no importa Costeo; sin dependencias nuevas.

### Riesgos identificados
- Carrera entre movimientos del mismo producto en almacenes distintos al actualizar el promedio (mitigación: bloqueo de la fila de costo del producto).
- Que algún camino inserte movimientos sin pasar por el puerto (mitigación: el puerto se invoca desde los tres casos de uso que insertan y se prueba que no hay otro `insert`).
- Redondeo de la salida total que deja residuo en el valor remanente (mitigación: la salida que vacía el producto toma todo el valor).
- Productos con saldo en el libro que no estaban en la adopción: imposible por el corte conciliado, pero se prueba.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambio financiero transversal a tres módulos, tablas nuevas, nuevo puerto entre módulos y contrato de ajustes modificado; con cálculo de dinero y bloqueo concurrente.

### Diseño requerido
**SI** — secciones nuevas en detalle de recepción y de movimiento, consulta con filtros y un campo nuevo en el formulario de ajuste.

## Diseño
Ver `docs/design/DDR-valorar-recepciones-consumos-costo-historico-seccion-valoracion-y-consulta.md`.

## Arquitectura
Ver `docs/adr/ADR-valorar-recepciones-consumos-costo-historico-puerto-modelo-y-contrato.md`.

## Plan
Ver `docs/plans/PLAN-2026-10-30-valorar-recepciones-consumos-costo-historico.md` (v1, COMPLETO).

## Implementación

**Resumen.** Con la valoración adoptada, Inventario invoca el puerto neutro `shared/stock_valuation.py` dentro de la sección crítica de `RecordMovement`, `RecordOutputs`, `ReverseMovement` y `ReverseSourceMovements`; Costeo (proveedor registrado en `CostingConfig.ready`) calcula el promedio móvil, guarda el snapshot inmutable y actualiza el estado corriente por producto.

**Backend.**
- Dominio puro `costing/domain/costing.py` (entrada, salida, vaciado sin residuo, redondeo): INV-01..03, AC-01/03/04/05.
- Modelos `ProductCostModel` y `MovementValuationModel` y migración `costing/0002` con `RunPython` idempotente para adopciones existentes: AC-15/16. La adopción ahora también inicializa el estado corriente (`DjangoAdoptionRepository.save`).
- Caso de uso `ValueMovement` (retroactividad, reversión, origen del costo): INV-05, AC-08/09. Proveedor `CostingValuationProvider`.
- Inventario: `apply_valuation` en los cuatro casos de uso, `ModularityInventoryPolicy.value_movement` y `allow_negative_stock()` en `False` con inventario valorado (INV-04, AC-07/11/12); `valuation` en `inventory.services.record_movement`; ajustes con `total_value`/`declared_zero` (AC-05/06).
- Compras: el precio unitario de la línea de compra viaja a la entrada (`purchase_price`): AC-01/02.
- API de lectura `/api/valuation/movements/` y `/costs/` con módulo `costing` y aislamiento por empresa: AC-13/14.

**Frontend** (pantallas de referencia: `movement-list` para la consulta, `product-form` «sección condicionada por módulo», `adjustment-form`; sin componentes nuevos en `shared/`): feature nueva `features/costing` con el componente `app-movement-valuation-section` (usado en detalle de recepción y de movimiento), la página `valuation-movements` (ruta `inventory/valuation/movements`, guardia `costing`) y el servicio; enlace en la página de valoración; campo «Valor total del ajuste (BOB)» y «Costo cero» en el formulario de ajuste: AC-17/18/19.

**Desviaciones del plan.**
- La URL del ajuste es `/api/stock-adjustments/` (el PLAN decía `/api/inventory/adjustments/`); PLAN y ADR corregidos, no cambia la Specification.
- El caso de uso `ReverseSourceMovements` (reversión de recepciones, posterior al diseño del ADR) también pasa por el puerto; el ADR lo cubría como «ReverseMovement» y ahora son cuatro puntos de inserción.
- La sección de recepción solo aparece si la recepción generó movimientos (`r.movements?.length`).
- El campo de valor del ajuste se muestra con Costeo habilitado y adopción, o cuando el servidor lo exige (400 `total_value`) aunque Costeo esté deshabilitado (decisión del usuario: la valoración sigue aplicándose).

**Pruebas.** Backend (PostgreSQL local): suite completa `python manage.py test`, 1313 pruebas (OK), incluidas 28 nuevas en `modules/costing/tests/test_movement_valuation.py` (dominio, recepciones, consumos, ajustes, saldo negativo con política activa, retroactividad, reversiones, atomicidad, idempotencia, aislamiento, 403 con valoración activa, migración de datos). Frontend: Karma de `features/**` (con un tsconfig temporal porque `app.component.spec.ts` ya no compila en `main`: `title` inexistente, preexistente) 983/984 — falla `FooterComponent should create` (angular-feather), preexistente y ajeno; `ng build` OK. `npm run lint` no es utilizable (no hay `eslint.config.js`). Esto es verificación propia, no el Quality Gate.

**Deuda técnica / no cubierto.**
- Falta una prueba de concurrencia de dos almacenes sobre el mismo producto (EDGE-04, prevista en el plan); el bloqueo es `select_for_update` de la fila de costo más el del almacén.
- Entradas de producción (PB-CST-002) quedan fuera; el punto de extensión es `cost_origin` en `MovementValue`.
- `app.component.spec.ts` y `FooterComponent` rotos en `main`.
- La apertura de existencias (`inventory_opening`) con inventario valorado se rechaza por falta de valor (EDGE-05); no se agregó campo de valor en esa pantalla.
- Sin revisión visual en navegador (corresponde a `delivery-publish`).

## Review
_Pendiente_

## Publicación
_Pendiente_
