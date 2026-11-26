# PLAN-2026-11-26-registrar-produccion-refrigeracion (v1)

**Task:** TASK-registrar-produccion-refrigeracion · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-registrar-produccion-refrigeracion-pasar-a-refrigeracion.md`, `docs/adr/ADR-registrar-produccion-refrigeracion-transaccion-y-costo.md`

## Objective
Desde una orden En preparación, registrar el consumo real, la cantidad elaborada y la fecha/hora de ingreso, descontar los ingredientes, ingresar el granel con su lote (en refrigeración, bloqueado para empaque) con el costo de lo consumido, y pasar la orden a En refrigeración, todo en una transacción idempotente.

## Context
Base: rama `produccion` (recetas, órdenes y lotes integrados). Hechos en el TASK.

# Specification

## Domain context
Bounded context **Producción**; relacionados: Inventario (movimientos y lotes), Costeo (promedio), Catálogo (solo lectura previa).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Consumo real | Cantidad realmente usada de un ingrediente | tarjeta |
| Cantidad elaborada / rendimiento real | Unidades que salieron en total | tarjeta |
| Pasar a refrigeración | Acción que cierra la elaboración e ingresa el lote | tarjeta |
| Lote | Granel identificado en Inventario (`L-YYYYMMDD-NNNN`), en refrigeración hasta liberarse | `inventory/domain/lot.py` |
| Disponible | Saldo para empaque: 0 mientras el lote está en refrigeración | ADR lotes |

## Current behavior
La orden llega a En preparación y no avanza (`production_order.py:106-111`).

## Expected behavior
`POST …/refrigerate/` con consumos reales, cantidad elaborada y fecha/hora ingresa el lote y deja la orden En refrigeración, con movimientos de Inventario y costo registrados una sola vez.

## Domain rules / invariants
- INV-01: solo `IN_PREPARATION → REFRIGERATING` (método `refrigerate`); otro estado de origen falla (409).
- INV-02: consumo real de cada ingrediente ≥ 0 (4 decimales; las líneas son las de la copia de la orden; se rechazan ids ajenos o faltantes); cantidad elaborada > 0 (máx. 9 dígitos enteros); se respetan `allows_fractions` de unidades enteras.
- INV-03: `entered_at` ≥ `started_at` y no futura (tolerancia 5 min por reloj).
- INV-04: todo o nada: salidas, lote, entrada, costo y estado en una transacción; con faltante no cambia nada.
- INV-05: idempotencia: reintento/doble clic no duplica movimientos, lote ni costo (orden bloqueada + idempotencia por `(production_order, orden)`).
- INV-06: el lote nace en refrigeración: saldo físico = cantidad elaborada, disponible = 0 (reglas de Inventario).
- INV-07: el costo unitario de la entrada = costo total consumido / cantidad elaborada, calculado con `Decimal`; sin valoración o sin promedio → se registra sin costo y no se bloquea.
- INV-08: los movimientos de origen `production_order` no se revierten manualmente desde Inventario.

## Acceptance criteria
- AC-01: el formulario/la API propone y acepta consumos y rendimiento reales; 120 previstos y 118 reales → el lote ingresa con 118 (físico 118, disponible 0).
- AC-02: una llamada exitosa descuenta cada ingrediente consumido, crea el lote con la entrada en el almacén de la orden y pasa la orden a `refrigerating`, guardando consumos, rendimiento real, fecha de ingreso, lote (id y código).
- AC-03: con un ingrediente insuficiente responde 409 `insufficient_stock` con la lista de faltantes (producto, requerido, disponible, faltante); la orden sigue En preparación y no hay movimientos ni lote.
- AC-04: reintento o doble envío no duplica movimientos ni lote (segunda llamada 409 `order_state`; saldos iguales a tras la primera).
- AC-05: con Costeo habilitado y valorado, el promedio del producto resultante se actualiza con costo unitario = costo consumido / elaborada y la orden muestra el costo total; sin valoración/costo, la operación procede y el costo queda vacío.
- AC-06: validaciones: consumo negativo/no numérico, elaborada ≤ 0, fecha anterior al inicio o futura, ingredientes ajenos/faltantes → 400 con error por campo; orden en borrador o ya refrigerada → 409.
- AC-07: sin período fiscal abierto para la fecha del lote → 409 con código `fiscal_period_missing/closed`; no cambia nada.
- AC-08: aislamiento por empresa (404 entre empresas) y módulo `production` deshabilitado → 403 `module_disabled`.
- AC-09: la API de detalle/lista expone estado `refrigerating`, producción real, fecha de ingreso, consumo real por ingrediente, lote y costo; el filtro `status=refrigerating` funciona.
- AC-10: Inventario rechaza revertir manualmente movimientos de origen `production_order` (`reverse_from_origin`).
- AC-11: UI: acción en el detalle, pantalla de registro con previstos precargados, faltantes por fila, estados cargando/enviando/error/éxito, sección «Producción registrada», badge y filtro; i18n es/en/pt.

## Edge cases / Error cases
- EDGE-01: consumo 0 de un ingrediente → no genera salida para esa línea.
- EDGE-02: todos los consumos en 0 → permitido (S3), el lote entra con costo total 0 / sin costo.
- EDGE-03: dos envíos concurrentes → uno gana (bloqueo de la orden), el otro 409.
- EDGE-04: almacén desactivado tras iniciar → la operación procede solo si el almacén existe en la empresa (S5).
- EDGE-05: producto/ingrediente que ya no controla stock → error por línea (lo informa Inventario).

## Authorization / permissions
Usuario autenticado de la empresa con `production` habilitado; `company_id` del usuario (`shared/tenancy.py`); el usuario actual queda como autor de movimientos y lote.

## API contract
- API-01: `POST /api/production-orders/<id>/refrigerate/` body `{entered_at, actual_output, ingredients: [{product_id, actual_quantity}]}` → 200 con el detalle de la orden.
- API-02: errores 400 por campo; 409 `order_state`, `insufficient_stock` (`shortages`), `fiscal_period_missing|closed`.
- API-03: el detalle suma (aditivo) `status: 'refrigerating'`, `actual_output`, `entered_at`, `refrigerated_at`, `lot {id, code}|null`, `cost_total|null`, `ingredients[].actual_quantity|null`. Cantidades string 4 decimales.

## UI behavior
UI-01..UI-04 según el DDR: detalle (acción + sección registrada), pantalla de registro, lista (badge/filtro), faltantes por fila.

## Non-functional requirements
`Decimal` siempre; sin `any`; i18n; Reactive Forms; lint en lo cambiado; una sola transacción corta.

## Out of scope
Liberar el lote, empaque, deshacer/cancelar la producción, asientos contables, mermas/subproductos, edición posterior del registro.

## Supuestos (decididos por defecto; revertibles sin cambiar la Specification mayor)
- S1: la política de stock negativo de la empresa decide si falta stock (Inventario es la fuente).
- S2: sin Costeo/valoración o sin promedio no se bloquea; costo vacío.
- S3: se permiten consumos 0 y rendimiento real distinto al previsto sin justificación.
- S4: fecha de ingreso ≥ inicio y no futura (tolerancia 5 min).
- S5: el almacén solo debe existir en la empresa al pasar a refrigeración.
- S6: el lote toma la fecha local de `entered_at`; requiere período fiscal abierto.
- S7: no se generan asientos contables.

## Open questions
Confirmar S1-S7 con negocio (no bloquean).

# Test Specification

## Unit tests
Dominio: `refrigerate` (INV-01..03, transición única, costo unitario).
## Integration tests
API (`APITestCase`) con Inventario real: AC-01..AC-10, EDGE-01..03; comparan saldos físicos/disponibles antes y después; idempotencia con doble llamada; faltante con múltiples ingredientes; costeo adoptado y no adoptado; guardas de límites (`test_boundaries`, `test_guards`) y reversa bloqueada.
Frontend (Karma): servicio, formulario (precarga, validación, faltantes por fila, doble clic), detalle por estado, lista, paridad i18n (`npm run i18n:check`).
## E2E
**NO** — se cubre con API y componentes; sin Playwright en el proyecto.
## Regression tests
Suites de `production`, `inventory`, `costing`, `modularity`, límites.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | API (saldos, lote, entrada) + dominio + spec del formulario |
| AC-03, AC-04 | API (faltante, doble llamada) |
| AC-05 | API con y sin valoración |
| AC-06, AC-07, AC-08 | API |
| AC-09 | API (lista/detalle/filtro) |
| AC-10 | prueba de Inventario (reversa bloqueada) |
| AC-11 | specs de componentes + i18n:check |

# Implementation Plan

## Architecture considerations
Ver ADR: caso de uso en Producción, fachadas de Inventario y Costeo, una transacción, bloqueo de la orden.

## Proposed solution
`domain/production_order.py` (estado, campos reales, `refrigerate`); `application/orders.py` (`RefrigerateOrder` + puertos `StockGateway` y `CostGateway`); `infrastructure/adapters.py` (adaptadores a `inventory.services` y `costing.services`); `infrastructure/django/models.py` + `order_repository.py` + migración `0003`; `api/order_views.py` (`OrderRefrigerateView`, serializer, mapeo de errores); `inventory/domain/movement.py` (`_BLOCKED_SOURCES`).

## Files/components affected
- Backend: archivos anteriores; `production/api/order_urls.py`; `sales/tests/test_boundaries.py` (`production → costing`); `modules/accounts/test_guards.py` si aplica; tests en `production/tests/` e `inventory/tests/`.
- Frontend: `features/production/{models,services,pages/order-refrigerate (nuevo), order-detail, order-list}`, `production.routes.ts`, `assets/i18n/{es,en,pt}.json`, specs.
- Docs: `docs/architecture/ddd.md` (nota Producción).

## Implementation steps
1. Dominio + pruebas unitarias (INV-01..03).
2. Modelos, migración `0003`, repositorio (AC-02, AC-09).
3. Caso de uso y adaptadores; límites entre módulos (AC-02..AC-07).
4. API, errores y pruebas de integración (AC-01..AC-09).
5. Bloqueo de reversa en Inventario + prueba (AC-10).
6. Frontend: modelo, servicio, pantalla de registro, detalle, lista, rutas, i18n (AC-11).
7. Documentación, lint (`ruff`, `flake8`, `npm run lint`), suites completas.

## Database / migrations
`production/0003_…` aditiva: columnas nulas en `production_order` y `production_order_ingredient`; se reemplaza la restricción estado↔`started_at` por una que contemple `refrigerating`. No se edita `0001`/`0002`.

## Risks
Atomicidad multi-módulo (mitigada con `transaction.atomic` y bloqueo); carrera de doble clic; empresas sin Costeo; dependencia nueva `production → costing`.

## New dependencies
Ninguna.
