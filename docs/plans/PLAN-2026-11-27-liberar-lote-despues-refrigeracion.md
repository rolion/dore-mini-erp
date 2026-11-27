# PLAN-2026-11-27-liberar-lote-despues-refrigeracion (v1)

**Task:** TASK-liberar-lote-despues-refrigeracion · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-liberar-lote-despues-refrigeracion-panel-liberacion · ADR-liberar-lote-despues-refrigeracion-minimo-y-liberacion

## Objective
Permitir que el encargado libere un lote en refrigeración solo cuando se cumpla el mínimo de horas configurado, registrando quién y cuándo, pasando la orden a «Listo para empacar» y el lote a disponible, sin duplicar stock.

## Context
Fuente: tarjeta DORE-PROD-005; base `produccion` (incluye PROD-004). Ver TASK.

# Specification

## Domain context
Producción (orden, regla del mínimo); Inventario (lote: estado y disponible); Modularidad (ajuste por empresa).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Ingreso a refrigeración | `entered_at` registrado en PROD-004 | `production_order.py` |
| Mínimo de refrigeración | Horas enteras configuradas por empresa (`production.min_refrigeration_hours`) | ADR |
| Primera hora habilitada | `entered_at + mínimo` | Tarjeta |
| Liberar | Orden `refrigerating → ready_to_pack` y lote `released` | Tarjeta / ADR lotes |
| Disponible | Saldo para empacar: 0 en refrigeración, físico si liberado | ADR lotes |

## Current behavior
Sin liberación: la orden queda En refrigeración y el lote bloqueado (`order_views.py:147`, `inventory/services.py:353`).

## Expected behavior
La orden En refrigeración muestra ingreso, tiempo transcurrido y primera hora habilitada. Antes de esa hora el backend rechaza liberar; después, el encargado confirma y se registra quién/cuándo, la orden queda Listo para empacar y las unidades ingresadas (p. ej. 118) pasan a disponibles sin nuevos movimientos. Repetir la solicitud no cambia nada.

## Domain rules / invariants
- INV-01: solo se libera desde `refrigerating`.
- INV-02: `now(servidor) ≥ entered_at + min_hours`; el reloj del cliente no cuenta.
- INV-03: liberar no crea movimientos: físico del lote sin cambio; disponible = físico.
- INV-04: orden y lote cambian en una transacción (todo o nada).
- INV-05: idempotente: repetir sobre `ready_to_pack` devuelve la orden sin cambios.
- INV-06: se guardan `released_at` (reloj del servidor) y la persona que liberó.

## Acceptance criteria
- AC-01: con mínimo 12 h y ingreso 08:00, el detalle muestra ingreso, tiempo transcurrido y «liberable desde 20:00».
- AC-02: liberar antes de las 20:00 (UI o API) responde 409 `release_too_early` con la hora habilitada; nada cambia.
- AC-03: liberar a las 20:00 o después deja la orden `ready_to_pack` y el lote `released`; el físico sigue 118 y el disponible pasa de 0 a 118.
- AC-04: la orden registra quién y cuándo liberó y el detalle lo muestra.
- AC-05: repetir la liberación (o doble clic) responde 200 con la misma orden; sin movimientos nuevos ni stock duplicado.
- AC-06: liberar una orden en `draft`/`in_preparation` → 409 de estado.
- AC-07: el mínimo se configura en Ajustes → Producción (entero 0–720, inicial 12); sin valor guardado rige 12; con 0 se puede liberar de inmediato.
- AC-08: la lista filtra y muestra «Listo para empacar»; textos en es/en/pt.
- AC-09: aislamiento por empresa y módulo `production` requerido (otra empresa → 404).

## Edge cases / Error cases
- EDGE-01: el ajuste cambia con lotes ya en refrigeración → rige el vigente al liberar/consultar.
- EDGE-02: ingreso en el futuro lejano no es posible (PROD-004 lo valida); si `entered_at` falta en una orden `refrigerating` (datos anteriores) → 409 de estado sin liberar.
- EDGE-03: lote ya liberado en Inventario pero la orden no (inconsistencia) → la orden pasa a `ready_to_pack` (release idempotente).

## Authorization / permissions
Mismo acceso que el resto de acciones de Producción (módulo `production` habilitado y usuario con empresa); la empresa sale del usuario autenticado. El frontend no es la barrera.

## API contract
- API-01: `POST /api/production-orders/<id>/release/` sin cuerpo → 200 con la orden.
- API-02: detalle/lista de orden suman `status: 'ready_to_pack'`, `release: {min_hours, releasable_from, can_release}`, `released_at`, `released_by` (aditivo, compatible hacia atrás).
- API-03: 409 `{detail, code: 'release_too_early', releasable_from, min_hours}`; 409 de estado existente para otros estados.
- API-04: ajustes: nuevo tipo `integer` y clave `production.min_refrigeration_hours` en `GET/PUT` de ajustes por módulo.

## UI behavior
- UI-01: sección «Liberación» en `order-detail` (plantilla Detalle) con ingreso, transcurrido, mínimo, hora habilitada y quién/cuándo si ya liberó (DDR).
- UI-02: botón «Liberar lote» con confirmación; deshabilitado con «Disponible desde …» antes de tiempo; botón deshabilitado mientras envía.
- UI-03: badge/filtro «Listo para empacar» en la lista.
- UI-04: campo numérico del ajuste en Ajustes → Producción.

## Non-functional requirements
Sin dependencias nuevas; migración aditiva; i18n es/en/pt con las mismas claves.

## Out of scope
Empaque (PROD-007), deshacer una liberación, liberación parcial, notificaciones al cumplirse la hora, asientos contables, roles específicos de producción.

## Open questions
Confirmar con negocio S1-S6 (no bloquean).

## Supuestos (decididos por defecto, revertibles)
- S1: el mínimo es por empresa, entero de horas, inicial 12 (valor del ejemplo de la tarjeta).
- S2: se evalúa con el valor vigente, no el de cuando ingresó el lote.
- S3: el tiempo se mide desde `entered_at` (hora declarada del ingreso), no desde que se registró.
- S4: cualquier usuario con acceso a Producción puede liberar.
- S5: la liberación no es deshacible.
- S6: sin asiento contable ni movimiento de costo.

# Test Specification

## Unit tests
Dominio: `releasable_from`, `release` (estado, mínimo, límites exactos, 0 h, idempotencia). Ajustes: validación del tipo `integer` y valor inicial.

## Integration tests
API con Inventario real: AC-02..AC-06, AC-09, EDGE-01..03 (saldo físico/disponible antes y después, sin movimientos nuevos, doble llamada). Ajuste vía API de ajustes (AC-07). Karma: detalle (sección, botón, deshabilitado, confirmación, error 409), lista (badge/filtro), formulario de ajustes (campo entero), i18n.

## E2E
NO — flujo cubierto por pruebas de API con Inventario real y Karma; no es un flujo crítico transversal nuevo.

## Regression tests
`test_boundaries` (`production → modularity`), `test_guards`, ajustes existentes (`percent/boolean/choice`), PROD-004 (`refrigerate`).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Karma detalle + API (campo `release`) |
| AC-02 | Dominio + API 409 |
| AC-03 | API con Inventario real (físico/disponible) |
| AC-04 | API + Karma detalle |
| AC-05 | API doble llamada |
| AC-06 | Dominio + API |
| AC-07 | Unit validación + API ajustes + Karma ajustes |
| AC-08 | Karma lista + prueba de claves i18n |
| AC-09 | API (otra empresa, módulo deshabilitado) |

# Implementation Plan

## Architecture considerations
Ver ADR: regla en el agregado, puerto `StockGateway.release_lot` y `ReleasePolicy`, fachada de lectura de Modularidad.

## Proposed solution
Agregado + caso de uso + vista `release/`; ajuste con tipo `integer`; UI en detalle, lista y ajustes.

## Files/components affected
- Backend: `production/domain/production_order.py`, `application/orders.py`, `infrastructure/adapters.py`, `infrastructure/django/{models,order_repository}.py`, `api/{order_views,order_urls,order_serializers}.py`, migración `0004`; `modularity/domain/settings.py` (tipo `integer`, clave), `modularity/services.py`; `sales/tests/test_boundaries.py`; `docs/architecture/ddd.md`; snapshot de defaults si lista ajustes.
- Frontend: `features/production/{models,services,pages/order-detail,pages/order-list}`, `features/settings/{models/setting.ts,pages/module-settings,services}`, `assets/i18n/{es,en,pt}.json`.
- Tests: dominio, API, ajustes, Karma.

## Implementation steps
1. Dominio: estado `ready_to_pack`, `releasable_from`, `release`, `ReleaseTooEarly` (INV-01, INV-02, INV-05, INV-06).
2. Ajuste `integer` + clave + fachada `get_production_settings` (AC-07).
3. Puertos/adaptadores y `ProductionOrders.release` con transacción (INV-03, INV-04, AC-03, AC-05).
4. Migración `0004`, repositorio, serializers y vista `release/` (API-01..03).
5. Frontend: modelos/servicio, sección y acción en detalle, lista, ajustes (UI-01..04, AC-08).
6. i18n es/en/pt, `test_boundaries`, `ddd.md`.
7. Pruebas por el mapeo de AC.

## Database / migrations
`production/0004` aditiva (3 columnas nulas/vacías; estado en choices). No se edita ninguna migración aplicada.

## Risks
Reloj: solo servidor. Zona horaria: API en ISO UTC, UI en hora local. Tipo nuevo de ajuste debe mantener la UI de Ajustes de otros módulos intacta (prueba de regresión).

## New dependencies
Ninguna.
