# PLAN-2026-10-30-valorar-recepciones-consumos-costo-historico (v1)

**Task:** TASK-valorar-recepciones-consumos-costo-historico · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-valorar-recepciones-consumos-costo-historico-seccion-valoracion-y-consulta · ADR-valorar-recepciones-consumos-costo-historico-puerto-modelo-y-contrato

## Objective
Con la valoración adoptada, valorar cada entrada y salida de inventario por promedio ponderado móvil, guardar un snapshot inmutable por movimiento y mostrarlo (recepción, movimiento, consulta), bloqueando lo que exigiría recalcular el pasado.

## Context
Tarjeta Trello PB-VAL-002 (https://trello.com/c/vlUMdnzZ). Decisiones del usuario en el TASK: la valoración sigue aplicándose con Costeo deshabilitado; ajuste positivo con valor total; backend + UI completa. Construye sobre PB-VAL-001 (adopción) y PB-INT-001 (entradas por recepción).

# Specification

## Domain context
**Costeo** (propietario del costo) recibe cada movimiento de **Inventario** por un puerto neutro; **Compras** aporta el precio de la recepción; **Ventas** no cambia de contrato (sus salidas se valoran por el puerto).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Inventario valorado | Empresa con adopción de valoración | Tarjeta / ADR |
| Promedio vigente | `valor total ÷ cantidad` del producto, 6 decimales `ROUND_HALF_UP` | PB-VAL-001 |
| Snapshot | Fila inmutable con cantidad, costo unitario, valor, promedio antes/después y origen del costo | Tarjeta |
| Origen del costo | `purchase_price`, `manual_adjustment`, `average_at_exit`, `reversal_snapshot` | ADR |
| Cubierto por la adopción | Movimiento anterior al corte, sin costo propio | Supuesto (TASK) |

## Current behavior
Los movimientos no tienen costo (`backend/modules/inventory/application/movement_use_cases.py:26,87,163`); la adopción solo guarda valores iniciales (`backend/modules/costing/application/use_cases.py:108`).

## Expected behavior
En empresa valorada, toda entrada o salida confirmada deja un snapshot y actualiza el estado corriente (cantidad y valor) del producto; las confirmaciones sin valoración válida, con saldo negativo o retroactivas se rechazan con un mensaje. En empresa no valorada nada cambia.

## Domain rules / invariants
- INV-01 (nueva): el estado corriente por producto es `quantity ≥ 0`, `total_value ≥ 0`, y `quantity` coincide con la suma de saldos del libro.
- INV-02 (nueva): entrada = `round2(cantidad × costo_unitario)`; salida = `round2(cantidad × promedio)`, salvo la que vacía el producto, que toma todo el valor.
- INV-03 (nueva): el snapshot es de solo inserción y no cambia ante compras o ajustes posteriores.
- INV-04 (nueva): en inventario valorado no hay saldo negativo por almacén, aunque la política de la empresa lo permita.
- INV-05 (nueva): un movimiento valorado no puede ocurrir antes del último valorado del producto ni del corte.
- INV-06: dinero siempre `Decimal`; sin `float`; aislamiento por `company_id`.

## Acceptance criteria
- AC-01: una recepción (parcial o completa) de un producto con stock crea entradas al `unit_price` de la compra; el valor y la cantidad del estado crecen y el promedio se recalcula (snapshot con promedio antes/después).
- AC-02: registrar pagos de la compra no crea snapshots ni cambia el estado de costo.
- AC-03: una salida (entrega de pedido o ajuste negativo) se valora al promedio vigente y su snapshot no cambia con compras posteriores.
- AC-04: la salida que deja el producto en cero toma todo el valor remanente (sin residuo de centavos).
- AC-05: un ajuste positivo exige `total_value` (400 `valuation_required` si falta); 0 solo con `declared_zero`; con valor > 0 y `declared_zero` es inválido.
- AC-06: un ajuste negativo no pide valor y consume el valor vigente.
- AC-07: una salida mayor que el saldo del almacén se rechaza aun con la política «permitir stock negativo».
- AC-08: un movimiento con `occurred_at` anterior al último valorado del producto o al corte se rechaza (409 `valuation_blocked`) con explicación.
- AC-09: revertir una entrada con movimientos valorados posteriores del producto se rechaza (409 `valuation_blocked`); revertir una salida entra al costo del snapshot original.
- AC-10: sin adopción, Inventario, Compras y Ventas se comportan exactamente como hoy (suite existente verde; ajuste sin campos de valor sigue válido).
- AC-11: si la valoración falla, no queda movimiento ni snapshot (atomicidad).
- AC-12: reintentar la misma operación de origen no duplica entrada, salida ni snapshot (idempotencia existente).
- AC-13: con Costeo deshabilitado la API de consulta responde 403 pero los movimientos siguen valorándose; la API aísla por empresa.
- AC-14: `GET /api/valuation/movements/` filtra por producto, origen y fecha y devuelve cantidad, costo unitario, valor, promedio antes/después, origen y estado; `GET /api/valuation/costs/` devuelve el costo corriente por producto.
- AC-15: no existe API ni caso de uso que edite o borre un snapshot.
- AC-16: adoptar inicializa el estado corriente; una migración de datos lo crea para adopciones ya existentes.
- AC-17: UI: sección «Valoración» en detalle de recepción y de movimiento (visible con Costeo y adopción), con estados cargando/vacío/error/éxito.
- AC-18: UI: consulta «Movimientos valorados» con filtros producto, origen y fecha.
- AC-19: UI: el formulario de ajuste muestra el campo de valor total y «Costo cero» solo con inventario valorado y diferencia positiva, y muestra los bloqueos del backend.

## Edge cases / Error cases
- EDGE-01: recepción de un producto que no controla stock → no hay movimiento ni snapshot.
- EDGE-02: precio de compra 0 → entrada a costo 0 (válida).
- EDGE-03: producto sin existencias previas (estado en cero) recibe su primera entrada: el promedio pasa a ser el precio de compra.
- EDGE-04: entradas de varias líneas del mismo producto y concurrencia en dos almacenes → serializadas por el bloqueo de la fila de costo.
- EDGE-05: apertura de existencias (`inventory_opening`) con inventario valorado → rechazada por falta de valor (la apertura ya exige que no haya historial).
- EDGE-06: movimiento anterior al corte se muestra «Cubierto por la adopción».

## Authorization / permissions
Consulta: usuario autenticado con empresa y módulo `costing` habilitado (permiso por módulo existente). La valoración de movimientos no depende del módulo. El frontend solo oculta secciones.

## API contract
- API-01 `GET /api/valuation/movements/?product_id&source_type&source_id&movement_id&date_from&date_to&page` → paginado `{id, movement_id, product_id, product_name, unit_abbreviation, kind, quantity, unit_cost, value, average_before, average_after, cost_origin, source_type, source_id, source_label, occurred_at, status}`.
- API-02 `GET /api/valuation/costs/` → `[{product_id, product_name, unit_abbreviation, quantity, total_value, average_cost}]`.
- API-03 `POST /api/stock-adjustments/` admite `total_value` (cadena decimal) y `declared_zero` opcionales; errores nuevos 400 `valuation_required`/`valuation_invalid` (campo `total_value`) y 409 `valuation_blocked`.
- API-04 Recepciones, entregas y reversiones devuelven 409 `valuation_blocked` / 400 `valuation_required` con mensaje accionable cuando corresponda. Sin cambios en respuestas actuales de éxito.

## UI behavior
UI-01 sección «Valoración» reutilizable (recepción, movimiento); UI-02 lista «Movimientos valorados» (plantilla «Lista de solo lectura con filtros»); UI-03 campo de valor en el ajuste con aviso de la regla; UI-04 enlace desde `valuation`; UI-05 mensajes de bloqueo en `alert alert-warning`. Derivado del DDR y de `design-system.md` §3–§5.

## Non-functional requirements
Atómico y bajo bloqueo (almacén + fila de costo, orden por `product_id`); consultas con `company_id` indexado y paginadas; textos en español.

## Out of scope
Entradas de producción (PB-CST-002), impuestos recuperables, fletes distribuidos, otras monedas, FIFO, valoración fiscal, corrección o revaluación de costos, reportes de valor, margen en ventas, valoración retroactiva de movimientos anteriores al corte.

## Open questions
- Si la persona espera movimientos «Pendiente» persistidos en vez de «Cubierto por la adopción» (supuesto del TASK; no bloquea).

# Test Specification

## Unit tests
Dominio de costeo (puro): entrada, salida, vaciado sin residuo, redondeo, reversión, retroactividad, valor requerido (INV-01..05, AC-01/03/04/05/08/09). Frontend: servicios y componente `movement-valuation`.

## Integration tests
Backend (`modules/costing/tests`, `inventory/tests`, `purchases/tests`, `sales/tests`): recepción parcial/completa, entrega, ajuste ±, saldo negativo con política activada, retroactividad, reversión, atomicidad (fallo a mitad), idempotencia, aislamiento, 403 por módulo con valoración activa, sin adopción sin cambios, concurrencia con dos almacenes, migración de datos. Frontend (Karma): detalle de recepción/movimiento, consulta, formulario de ajuste.

## E2E
**NO** — no es un flujo crítico de punta a punta y no se justifica instalar Playwright.

## Regression tests
Suites existentes de inventario (movimientos, ajustes, apertura), compras (recepciones, pagos), ventas (entrega) y costeo (adopción) siguen verdes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración compras→inventario→costeo + unit dominio |
| AC-02 | Integración: pago de compra sin snapshots nuevos |
| AC-03, AC-04 | Unit dominio + integración entrega y ajuste negativo |
| AC-05, AC-06 | Unit + integración API de ajustes |
| AC-07 | Integración con política de stock negativo permitida |
| AC-08, AC-09 | Unit dominio + integración 409 |
| AC-10 | Regresión de suites existentes |
| AC-11, AC-12 | Integración (rollback e idempotencia) |
| AC-13 | Integración: módulo deshabilitado y dos empresas |
| AC-14, AC-15 | Integración API + comprobación de que no hay rutas de escritura |
| AC-16 | Integración + prueba de migración |
| AC-17, AC-18, AC-19 | Specs Karma; revisión visual en `delivery-publish` |

# Implementation Plan

## Architecture considerations
Ver ADR: puerto `shared/stock_valuation.py` invocado en `RecordMovement`, `RecordOutputs` y `ReverseMovement`; Inventario no importa Costeo; `costing` sigue sus capas.

## Proposed solution
Dominio puro de costeo + modelos `costing_product_cost` y `costing_movement_valuation` + proveedor del puerto + extensión de las fachadas (`valuation` opcional) + lecturas API + UI.

## Files/components affected
- **Backend nuevo:** `backend/shared/stock_valuation.py`; `costing/domain/costing.py`, `application/` (casos de valoración y consultas), `infrastructure/django/` (modelos, repositorios, proveedor), `api/` (movimientos y costos), migración `costing/0002` (tablas + `RunPython` para adopciones existentes), tests.
- **Backend modificado:** `costing/application/use_cases.py` (la adopción inicializa el estado), `costing/apps.py` (registro del proveedor), `inventory/application/{movement_use_cases,adjustment_use_cases}.py`, `inventory/services.py` (DTO `valuation`), `inventory/infrastructure/adapters.py` (política de saldo negativo), `inventory/api/adjustment_views.py` y su serializer (campos de valor y errores), `purchases/infrastructure/adapters.py` y `application/receipt_commands.py` (precio por línea), `config/urls.py` si hace falta.
- **Frontend:** `features/inventory/components/movement-valuation/`, `services/valuation-api.service.ts` (consulta), modelos, `pages/valuation-movements/`, ruta + guardia `costing`, `movement-detail`, `adjustment-form`, `valuation`; `features/purchases/pages/receipt-detail` (reutilizar el componente; verificar la convención de imports entre features antes), specs.
- **Docs:** `docs/producto/modulos-implementados.md`, `docs/design/design-system.md` solo si se añade un patrón nuevo.

## Implementation steps
1. Dominio de costeo puro (entrada, salida, reversión, reglas) y sus pruebas (INV-01..05, AC-03/04/05/08/09).
2. Modelos, migración `costing/0002` con datos para adopciones existentes y repositorios (AC-15/16).
3. Puerto `shared/stock_valuation.py` y proveedor de Costeo; adopción inicializa el estado (AC-16).
4. Inventario: invocar el puerto en los tres casos de uso, DTO `valuation` en la fachada, política de saldo negativo y retroactividad (AC-07/08/11/12).
5. Compras: precio unitario por línea de recepción al registrar entradas (AC-01/02).
6. Ajustes: `total_value`/`declared_zero` en API y caso de uso (AC-05/06).
7. API de consulta `/api/valuation/movements/` y `/costs/` (AC-13/14).
8. Pruebas de integración y concurrencia (AC-01..16).
9. Frontend: servicio, componente `movement-valuation`, secciones en recepción y movimiento, consulta, campo en ajuste (AC-17..19).
10. Specs frontend, revisión de consistencia visual y actualización de documentos.

## Database / migrations
`costing/0002_product_cost_and_movement_valuation`: solo tablas nuevas y `RunPython` idempotente que crea el estado corriente desde las líneas de adopciones existentes (reversible). No se edita ninguna migración aplicada.

## Risks
Carreras entre almacenes (bloqueo de la fila de costo, orden por `product_id`); caminos que inserten movimientos sin el puerto (test que lo verifica); residuo de redondeo (regla de vaciado); coupling vía puerto (mismo patrón que `stock_history`); supuesto «Cubierto por la adopción» vs «Pendiente».

## New dependencies
Ninguna.
