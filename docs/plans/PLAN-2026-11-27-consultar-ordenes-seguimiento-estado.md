# PLAN-2026-11-27-consultar-ordenes-seguimiento-estado (v2)

**Task:** TASK-consultar-ordenes-seguimiento-estado · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-consultar-ordenes-seguimiento-estado-lista-y-detalle (parte Lista), DDR-consultar-ordenes-seguimiento-estado-detalle-orden-rediseno (parte Detalle) / Ninguno

## Objective
Que el encargado consulte las órdenes por etapa con lo elaborado y el saldo a granel, filtre por fecha, receta y estado, y vea en el detalle las existencias del lote, sin cambiar las acciones de producción ya existentes.

## Context
PROD-003/004/005 ya entregan lista, detalle, refrigeración y liberación (ver TASK). Falta el saldo del lote, y los filtros de fecha y receta. Base: rama `produccion`.

# Specification

## Domain context
Bounded context `production`; lee `inventory` solo vía `inventory.services` (ya usado por Producción).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Unidades previstas | `expected_output` (rendimiento × preparaciones) | `production_order.py` |
| Unidades elaboradas | `actual_output` registrado al pasar a refrigeración | `production_order.py` |
| Saldo disponible a granel | `available_quantity` del lote en Inventario: 0 en refrigeración; en lote liberado, físico menos empaques | `inventory/services.py` `LotRecord` |
| Saldo físico del lote | `physical_quantity` del lote | ídem |

## Current behavior
Lista filtra solo por estado y no muestra elaboradas ni saldo (`order_views.py` `OrderListCreateView.get`, `order-list.component.html`). Detalle no muestra existencias del lote.

## Expected behavior
Lista con columnas Número, Receta, Previstas, Elaboradas, Saldo a granel, Estado, Fecha y filtros Estado/Receta/Desde/Hasta combinables. Detalle con sección de existencias del lote. El saldo siempre se lee de Inventario, por lo que refleja los empaques parciales cuando existan.

## Domain rules / invariants
- INV-01 (nueva, solo lectura): el saldo disponible nunca se calcula en Producción; lo entrega Inventario.
- INV-02 (existente): el disponible de un lote en refrigeración es 0 aunque tenga físico.

## Acceptance criteria
- AC-01: `GET /api/production-orders/` acepta `date_from`, `date_to` (YYYY-MM-DD, sobre la fecha de creación, inclusivo) y `recipe_id`, combinables con `status`; todos filtrados por empresa.
- AC-02: cada orden devuelve `lot` con `physical_quantity`, `available_quantity` y `status` (`refrigerating|released`); `lot` es `null` sin lote.
- AC-03: una orden con 118 elaboradas en refrigeración muestra elaboradas 118 y saldo disponible 0; tras liberar, 118; si Inventario registra un empaque parcial de 60, el saldo visible es 58.
- AC-04: la lista muestra las columnas indicadas, «—» donde no aplica, y cuatro estados con etiqueta en es/en/pt.
- AC-05: la lista ofrece filtros Estado, Receta, Desde y Hasta; «Limpiar filtros»; vacío con filtros muestra los activos; los filtros se conservan al volver del detalle.
- AC-06: el detalle muestra ingredientes previstos y reales (con su diferencia), lote, ingreso/transcurrido/mínimo/primera hora y existencias del lote (físico, disponible, estado).
- AC-08 (v2): el detalle muestra la etapa actual de la orden (Borrador, En preparación, En refrigeración, Listo para empacar) y las fechas de las etapas alcanzadas.
- AC-07: las acciones por estado se habilitan solo en el estado correspondiente (Borrador: editar/iniciar; En preparación: registrar producción; En refrigeración: liberar; Listo para empacar: ninguna de producción).

## Edge cases / Error cases
- EDGE-01: `date_from` > `date_to` o fecha/uuid inválidos → 400 con el campo; la UI no consulta con rango inválido.
- EDGE-02: lote inexistente en Inventario → `physical/available` = `null`, sin error.
- EDGE-03: orden de otra empresa nunca aparece (aislamiento).
- EDGE-04: sin resultados → estado vacío distinto con y sin filtros.

## Authorization / permissions
Igual que hoy: módulo `production` habilitado y empresa del usuario. Solo lectura; sin permisos nuevos.

## API contract
- API-01: `GET /api/production-orders/?status&recipe_id&date_from&date_to&page&page_size` (parámetros nuevos opcionales; retrocompatible).
- API-02: `lot` ahora `{id, code, status, physical_quantity, available_quantity}` (campos añadidos; cantidades como cadena de 4 decimales).

## UI behavior
- UI-01: lista según DDR (plantilla «Lista de solo lectura con filtros»; tarjetas bajo 957 px).
- UI-02 (v2): detalle rediseñado según DDR `...-detalle-orden-rediseno`: cabecera con número, `app-status-badge` y receta·producto·almacén; línea de etapas con fechas; tarjetas de cifras clave (previstas, elaboradas, saldo físico, disponible para empaque, costo); tarjetas «Datos de la orden» y «Lote y refrigeración» con barra de progreso hacia la hora habilitada; motivo del botón «Liberar» visible y enlazado por `aria-describedby`; tabla de ingredientes con columna Diferencia (aritmética entera).
- UI-04 (v2): el detalle no repite datos (ingreso, previsto) y se adapta a móvil (rejilla 1 columna; ingredientes en tarjetas bajo 957 px).
- UI-03: sin texto hardcodeado; claves en es/en/pt.

## Non-functional requirements
Máx. 20 lecturas de lote por página; sin N+1 sobre ingredientes (ya hay `prefetch_related`).

## Out of scope
Empacar (PROD-007/008), consumos de empaque, cambios de estado, migraciones, reportes, migrar badges a `app-status-badge`.

## Open questions
Ninguna que bloquee; supuestos de fecha y saldo documentados en el TASK, confirmables en el PR.

# Test Specification

## Unit tests / Integration tests
- Backend API (`production/tests/test_order_api.py`): filtros fecha/receta/estado combinados y rango inválido; aislamiento por empresa; `lot` con saldos en refrigeración (físico 118, disponible 0), liberado (118) y tras `inventory.services.record_movement` de salida con lote de 60 (58); lote inexistente → null.
- Frontend (Karma): `orders-api.service.spec` (parámetros y mapeo de `lot`), `order-pages.spec` (columnas, «—», filtros, limpiar, rango inválido, acciones por estado, existencias en detalle).
- i18n: `npm run i18n:check` y prueba de claves iguales.
## E2E
NO — flujo cubierto por integración API y pruebas de componente; no es un flujo crítico nuevo.
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | test API filtros |
| AC-02 | test API lot |
| AC-03 | test API saldos (refrigeración/liberado/empaque parcial) |
| AC-04 | spec lista (columnas, «—», estados) |
| AC-05 | spec lista (filtros, limpiar, vacío, estado conservado) |
| AC-06 | spec detalle |
| AC-07 | spec detalle por estado + API existente |
| AC-08 | spec detalle (etapa actual y fechas por estado) |

# Implementation Plan

## Architecture considerations
Se añade un puerto de lectura `LotBalances` en `production/infrastructure/adapters.py` que llama a `inventory.services.get_lot`; el dominio no cambia.

## Files/components affected
Backend: `production/api/order_views.py`, `infrastructure/django/order_repository.py` (filtros), `infrastructure/adapters.py` (lectura de lote), `tests/test_order_api.py`. Frontend: `models/order.ts`, `services/orders-api.service.ts` (+spec), `pages/order-list/*`, `pages/order-detail/*`, `order-pages.spec.ts`, `assets/i18n/{es,en,pt}.json`. Docs: este PLAN, TASK, DDR.

## Implementation steps
1. Repositorio y vista: filtros `recipe_id`, `date_from`, `date_to` con validación (AC-01, EDGE-01/03).
2. Adapter de saldo de lote y `_serialize` con `lot` ampliado (AC-02, AC-03, EDGE-02, INV-01/02).
3. Pruebas backend.
4. Modelo/servicio del frontend: parámetros y mapeo (API-01/02).
5. Lista: columnas, filtros, estado en memoria, vacío, tarjetas (AC-04/05, UI-01).
6. Detalle: existencias del lote; verificar acciones por estado (AC-06/07, UI-02).
7. i18n es/en/pt y pruebas de frontend; lint (ruff/flake8 en lo cambiado, `npm run lint`, `i18n:check`).

## Database / migrations
Ninguna.

## Risks
Lecturas de lote por orden (ver Non-functional); zona horaria del filtro de fecha (se usa `created_at__date` con `TIME_ZONE` del proyecto).

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-27): [Specification] UI-02 reescrito, UI-04 y AC-08 añadidos y AC-06 ampliado (diferencia de ingredientes) tras la crítica de diseño del detalle; aprobado explícitamente por el usuario en el chat («hazlo en este mismo PR»). [Implementation Plan] Archivos: `order-detail.component.{html,scss,ts}`, `order-pages.spec.ts`, i18n es/en/pt, `design-system.md` (patrón de etapas). Sin cambios de backend.
