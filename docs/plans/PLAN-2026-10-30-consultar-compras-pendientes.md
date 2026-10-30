# PLAN-2026-10-30-consultar-compras-pendientes (v1)

**Task:** TASK-consultar-compras-pendientes · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-consultar-compras-pendientes-lista-con-filtros-y-estados · Ninguno (ADR)

## Objective
Que la lista de compras permita dar seguimiento: mostrar referencia interna, estado de recepción, estado de pago y saldo, y filtrar/buscar por proveedor, fechas, estados y referencia; y que el detalle muestre juntos totales, pagado y saldo.

## Context
PB-COM-004 (recepciones) y PB-COM-005 (pagos) ya están en `main`; el detalle ya consolida Resumen/Recepciones/Pagos. Falta la lista (ver Investigación en el TASK). Sin migración, sin módulos cruzados.

# Specification

## Domain context
Bounded context Compras. Sin cambios en dominio: `reception_status`, `payment_status` y `status` ya están persistidos; el saldo se deriva de pagos confirmados.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Estado documental | `draft/confirmed/cancelled` (Borrador/Confirmada/Cancelada) | `domain/enums.py` |
| Estado de recepción | `not_received/partial/received` | `domain/enums.py` |
| Estado de pago | `unpaid/partial/paid` | `domain/enums.py` |
| Pago pendiente | `unpaid` o `partial` (saldo > 0) | H-02 del TASK |
| Saldo | total − pagos confirmados | PB-COM-005 |
| Referencia interna | `COM-` + 8 hex mayúsculos del id | `Purchase.reference` |

## Current behavior
Lista con Fecha, Proveedor, Referencia externa, Total, Estado y Acciones; solo filtra por `supplier_id` (`purchase_views.py`, `PurchaseListCreateView.get`; `purchase-list.component.html:55-90`).

## Expected behavior
- La lista devuelve y muestra, por compra: referencia interna, estados de recepción y pago y saldo (solo confirmadas; en las demás, nulos/«—»).
- La lista acepta filtros combinables (AND): proveedor, `date_from`/`date_to`, `status`, `reception_status`, `payment_status` (incl. «pendiente») y `q`.
- Sin resultados con filtros: se muestran los filtros aplicados, «Limpiar filtros» y acceso a Nueva compra.
- El detalle (Resumen) muestra Total pagado y Saldo junto a los tres estados separados.

## Domain rules / invariants
- INV-01 (nueva) Recepción, pago y saldo de la lista solo se informan para compras confirmadas; borrador y cancelada devuelven `null` en esos tres campos.
- INV-02 (nueva) Filtrar por `reception_status` o `payment_status` implica compras confirmadas.
- INV-03 (existente) Toda consulta filtra por `company_id`; el saldo suma solo pagos de la misma empresa y compra.
- INV-04 (existente) Dinero en `Decimal`, serializado como texto con 2 decimales.

## Acceptance criteria
- AC-01 `GET /api/purchases/` incluye por fila `reference`, `reception_status`, `payment_status`, `paid_total` y `balance` (texto decimal), con `null` en borrador/cancelada; los campos actuales no cambian (compatible hacia atrás).
- AC-02 Filtra por `supplier_id`, `date_from`/`date_to` (inclusivo, sobre `purchase_date`), `status`, `reception_status` y `payment_status`; los filtros se combinan con AND y no hay resultados de otra empresa.
- AC-03 `payment_status=pending` devuelve confirmadas `unpaid`+`partial`; combinado con `reception_status=received` devuelve compras recibidas aún por pagar.
- AC-04 `q` busca por referencia externa (parcial, sin distinguir mayúsculas) y por referencia interna (prefijo, con o sin `COM-`).
- AC-05 Valores inválidos (UUID, fecha, estado desconocido) y `date_from > date_to` responden 400 con el campo señalado.
- AC-06 El saldo de una compra con pagos parciales es total − pagado; una compra recibida e impaga y una pagada pendiente de recibir se distinguen en columnas separadas.
- AC-07 La lista muestra las columnas del DDR, con badges de texto, y «—» donde no aplica.
- AC-08 La barra de filtros y el buscador actualizan la lista (primera página), se reflejan en la URL y se restauran al volver; «Limpiar filtros» los quita.
- AC-09 Sin resultados: sin filtros → mensaje actual; con filtros → filtros aplicados + «Limpiar filtros» + «Nueva compra».
- AC-10 El detalle (Resumen) muestra Total pagado y Saldo; las pestañas Recepciones y Pagos siguen igual.
- AC-11 Error de servidor visible con «Reintentar»; rango Desde > Hasta bloquea la consulta con mensaje.

## Edge cases / Error cases
- EDGE-01 Confirmada con total 0: saldo 0,00, estado `unpaid` (H-09 de PB-COM-005).
- EDGE-02 `q` con solo espacios = sin búsqueda; `q` que no es hex solo busca en la externa.
- EDGE-03 Proveedor inactivo o eliminado: se muestra su nombre como hoy (`''` → «—»).
- EDGE-04 Paginación con filtros: el conteo corresponde al conjunto filtrado.

## Authorization / permissions
Sin cambios: `required_modules=('purchases',)`, empresa del usuario autenticado (`company_id_from`). La UI no es la barrera.

## API contract
- API-01 `GET /api/purchases/?supplier_id=&date_from=&date_to=&status=&reception_status=&payment_status=&q=&page=&page_size=` — todos opcionales. `payment_status` acepta `unpaid|partial|paid|pending`.
- API-02 Cada fila añade: `reference` (str), `reception_status` (str|null), `payment_status` (str|null), `paid_total` (str|null), `balance` (str|null). Compatible hacia atrás (solo agrega).
- API-03 400 con `{campo: [mensajes]}` para parámetros inválidos.
- Detalle (`GET /api/purchases/<id>/`): sin cambios (ya trae `paid_total` y `balance`).

## UI behavior
- UI-01 Plantilla «Lista de solo lectura con filtros» (design-system sección 5) con el detalle del DDR: buscador, fila de filtros (Proveedor `ng-select`, Desde, Hasta, Estado, Recepción, Pago, Limpiar), columnas, badges.
- UI-02 Estados cargando / vacío / vacío con filtros / error según el DDR.
- UI-03 Resumen del detalle con Total pagado y Saldo.

## Non-functional requirements
Sin N+1: saldo y conteo en una sola consulta con subconsulta/agregado; búsqueda acotada por `company_id`.

## Out of scope
Cantidades recibidas/pendientes agregadas en la lista; exportación; ordenamiento por columna; filtros guardados; atajos; cambios en recepciones, pagos o inventario; migraciones.

## Open questions
Ninguna bloqueante (H-01…H-08 del TASK quedan como supuestos reversibles).

# Test Specification

## Unit tests
Parser de filtros (valores válidos, inválidos, rango invertido, `pending`, `q`); función pura de filtros del frontend (formulario ↔ query params ↔ parámetros API).

## Integration tests
Backend con PostgreSQL (`python manage.py test modules.purchases`): lista con compras de borrador/confirmada/cancelada, pagos y recepciones; cada filtro y su combinación; aislamiento por empresa; saldo; búsqueda; paginación con filtros; 400s. Frontend (Karma): componente de lista (columnas, filtros, vacío con filtros, error, restauración desde URL) y `purchases-api.service` (mapeo de campos y parámetros); detalle (filas Total pagado/Saldo).

## E2E
**NO** — no es un flujo crítico de punta a punta; la verificación visual en navegador queda para `delivery-publish`.

## Regression tests
Las pruebas existentes de lista, detalle, cancelación y de límites entre módulos (`test_boundaries`) deben seguir pasando.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-06 | Integración backend (serializer + saldo) |
| AC-02, AC-03 | Integración backend (filtros, combinaciones, aislamiento) |
| AC-04 | Integración backend (búsqueda externa/interna) |
| AC-05 | Unitaria del parser + integración 400 |
| AC-07, AC-09 | Karma: componente de lista |
| AC-08, AC-11 | Karma: componente de lista + función pura de filtros |
| AC-10 | Karma: detalle de compra |

# Implementation Plan

## Architecture considerations
Se mantiene el patrón vigente: el repositorio devuelve una vista perezosa sobre un queryset; los filtros viajan como un objeto de valor de la capa de aplicación, que el parser de la API construye y valida (como `parse_order_filters` en Ventas). Sin ADR.

## Proposed solution
Backend: `PurchaseFilters` (dataclass) + `parse_purchase_filters` en `api/`; `PurchaseRepository.list(filters)` aplica filtros y anota `paid_total` con `Coalesce(Subquery(Sum de pagos confirmados), 0)`; `PurchaseSummary` suma `reference`, `reception_status`, `payment_status`, `paid_total`, `balance`; `summary_representation` los emite (nulos si no confirmada). Frontend: modelo/servicio extendidos, `purchase-list-filters.ts` (funciones puras), lista con formulario de filtros, columnas y vacío, y filas nuevas en el Resumen del detalle.

## Files/components affected
- Backend: `purchases/domain/repositories.py` (`PurchaseSummary`, firma `list`), `application/purchase_queries.py` (`ListPurchases`), `api/purchase_views.py`, nuevo `api/purchase_filters.py`, `api/purchase_serializers.py`, `infrastructure/django/purchase_repository.py`; tests en `purchases/tests/`.
- Frontend: `features/purchases/models/purchase.ts`, `services/purchases-api.service.ts` (+spec), nuevo `pages/purchase-list/purchase-list-filters.ts` (+spec), `purchase-list.component.{ts,html,scss,spec.ts}`, `purchase-detail.component.html` (+spec), `testing/purchase-fixtures.ts`.
- Docs: `docs/design/design-system.md` (patrón «vacío con filtros aplicados»), TASK, PR.
- Migraciones: ninguna.

## Implementation steps
1. Backend: `PurchaseFilters` + parser con validaciones y 400 (AC-05).
2. Repositorio: filtros por proveedor, fechas, estados, `q` (externa `icontains`; interna por prefijo sobre `Cast(id→texto)`), y anotación de pagado; ajustar `PurchaseList` para poblar los campos nuevos (AC-02…AC-04, AC-06; INV-01…03).
3. Vista y serializer: leer filtros, emitir campos nuevos (AC-01, API-01/02).
4. Pruebas backend (AC-01…AC-06) con PostgreSQL.
5. Frontend: modelo, DTO y servicio con parámetros nuevos (AC-01, AC-02).
6. Frontend: funciones puras de filtros y estado en URL (AC-08, AC-11).
7. Frontend: lista con filtros, columnas, badges y vacío con filtros (AC-07, AC-09, UI-01/02).
8. Frontend: filas Total pagado y Saldo en el Resumen del detalle (AC-10).
9. Pruebas Karma y lint; actualizar `design-system.md`.

## Database / migrations
Sin migraciones. Índices existentes suficientes para el volumen del MVP; no se agregan.

## Risks
- Rendimiento de la subconsulta de pagos y de la búsqueda por `id::text` en empresas con muchas compras (mitigado por `company_id`; revisar con `EXPLAIN` si hay dudas).
- Filtros de recepción/pago excluyen borradores (INV-02): explicarlo en la interfaz.

## New dependencies
Ninguna.
