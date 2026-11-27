# TASK-consultar-ordenes-seguimiento-estado: Consultar órdenes de producción y seguir su estado

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-consultar-ordenes-seguimiento-estado (base: `produccion`)
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/fGrIBXUO/6-dore-prod-006-consultar-%C3%B3rdenes-y-seguir-su-estado

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado desde Trello DORE-PROD-006 | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN | NEEDS_PLAN, diseño requerido | delivery-start |
| 2026-11-27 | DESIGN → PLANNING | DDR escrito | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | PLAN v1 READY | delivery-start |

## Investigación

### Requerimiento
Tarjeta Trello **DORE-PROD-006 · Consultar órdenes y seguir su estado** (insumo, no Specification aprobada). Historia: como encargado de DORE, consultar las órdenes por etapa y abrir su detalle para saber qué se está preparando, qué sigue en refrigeración y qué puedo empacar.

Comportamiento esperado de la tarjeta:
- Listado: número de orden, receta, unidades previstas, unidades elaboradas, estado y saldo disponible a granel; filtros por fecha, receta y estado.
- Detalle: ingredientes previstos y reales, datos del lote, tiempos de refrigeración y existencias disponibles.
- Estados visibles: Borrador, En preparación, En refrigeración, Listo para empacar; las acciones de producción y liberación se habilitan según el estado.
- El saldo disponible refleja los consumos de empaque cuando se registran; los empaques parciales actualizan el saldo visible del lote.
- Dependencias: DORE-PROD-003 (crear/iniciar), DORE-PROD-005 (liberar lote).

Aclaración del usuario (chat): «usa la rama de producción» → base y PR contra `produccion` (donde viven PROD-001..005; `main` aún no tiene el módulo).

### Hechos encontrados
- `origin/produccion` (`27ca9602`) ya contiene el módulo `backend/modules/production` (recetas, órdenes, refrigeración, liberación) y `frontend/panel_admin/src/app/features/production/`; `main` no lo tiene. Los PR #127/#128/#131/#134/#139 apuntan a `produccion`.
- Lista: `OrderListCreateView.get` solo filtra por `status` (`backend/modules/production/api/order_views.py:~125`); `DjangoProductionOrderRepository.list(status=)` (`infrastructure/django/order_repository.py:104`) ordena por `-number`.
- La respuesta (`_serialize`, `order_views.py:~70`) ya trae `expected_output`, `actual_output`, `lot {id, code}`, `entered_at`, `release {min_hours, releasable_from, can_release}`, `released_at/by`, ingredientes con `expected_quantity`/`actual_quantity`. **No trae saldo del lote** (físico/disponible).
- Inventario ya expone el saldo por lote: `inventory.services.get_lot(company_id, lot_id) -> LotRecord` con `physical_quantity` y `available_quantity` (disponible = físico solo si el lote está liberado; 0 en refrigeración) (`backend/modules/inventory/services.py:304-370`; `domain/lot.py` `StockLot.available`). Producción ya importa esa fachada (`production/infrastructure/adapters.py:95-113`). Los movimientos futuros de empaque con lote (PROD-007/008) alteran ese físico, así que leerlo de ahí refleja los consumos de empaque sin lógica propia.
- Frontend lista: `pages/order-list/order-list.component.{ts,html}` — columnas Número, Receta, Almacén, Preparaciones, Salida prevista, Estado, Fecha; filtro solo por estado; tarjetas bajo 957 px; filtros guardados en `OrderFiltersState` (`services/orders-api.service.ts:152`). Faltan: unidades elaboradas, saldo a granel, filtros fecha y receta.
- Frontend detalle: `pages/order-detail/order-detail.component.html` muestra ingredientes previstos/reales, bloque «registrado» (salida real, ingreso, código de lote, costo) y bloque de liberación (ingreso, transcurrido, mínimo, primera hora, liberado por/en); botón «Liberar» solo en refrigeración. Falta: existencias del lote (físico/disponible).
- `RecipesApiService.list` (`services/recipes-api.service.ts:78`) permite poblar el filtro de receta.
- Referencia visual: plantilla «Lista de solo lectura con filtros» y «Variante con seguimiento de estados» de `docs/design/design-system.md:168-173`; filtro de fechas en `features/inventory/pages/movement-list` (`filter-from`/`filter-to`).

### Hipótesis / supuestos no confirmados
- «Fecha» del filtro = fecha de creación de la orden (la columna Fecha ya muestra `created_at`), día calendario en la zona horaria de la empresa/servidor; rango inclusivo.
- «Saldo disponible a granel» = `available_quantity` del lote de la orden (0 mientras refrigera; el remanente tras empaques cuando está liberado). Sin lote (borrador/en preparación) se muestra «—».
- El empaque (PROD-007/008) no existe aún; esta tarea no lo implementa. Cuando exista, el saldo ya se actualiza porque se lee del lote.
- Acciones por estado: Borrador → editar/iniciar; En preparación → registrar producción; En refrigeración → liberar; Listo para empacar → sin acción de producción (empacar es PROD-007). Ya implementado; se verifica con pruebas.

### Módulos y dependencias relacionadas
`production` (api, infraestructura, frontend), lectura de `inventory.services` (fachada existente). Sin migraciones.

### Implementaciones similares existentes
`movement-list` (filtros de fecha), `purchase-list` (lista con estados y saldo), `stock-detail` (existencias).

### Restricciones
Aislamiento por `company_id`, cantidades como cadena decimal con 4 decimales, textos en `translate` es/en/pt, sin dependencias nuevas.

### Riesgos identificados
- Consulta de saldo por orden (hasta 20 por página) → N lecturas a Inventario; aceptable por el tamaño de página, a revisar si crece.
- Lote borrado en Inventario → saldo `null`, no error.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado y aditivo (filtros + dos campos de lectura + UI) sin decisión arquitectónica nueva ni migración.

### Diseño requerido
**SI** — cambia columnas, filtros y detalle de pantallas existentes (DDR corto).

## Diseño
DDR: `docs/design/DDR-consultar-ordenes-seguimiento-estado-lista-y-detalle.md`.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-27-consultar-ordenes-seguimiento-estado.md` (v1, COMPLETO, READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
