# PLAN-2026-10-27-inventario-stock-almacenes-unidades (v1)

**Task:** TASK-inventario-stock-almacenes-unidades · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-inventario-stock-almacenes-unidades-pantallas-inventario · ADR-inventario-stock-almacenes-unidades-propiedad-y-fronteras

## Objective
Permitir marcar productos que controlan stock con una unidad base (PB-INV-001) y administrar unidades y almacenes por empresa (PB-INV-002), dejando listos los bloqueos que dependen de movimientos, saldos y recepciones futuros.

## Context
Ver TASK. Decisiones del usuario: empresas sin unidades iniciales; bloqueos como puertos sin datos reales hoy; unidad en uso solo activable/desactivable.

# Specification

## Domain context
`catalog` (producto y unidad de medida), `inventory` (almacén, nuevo). `modularity` solo vía `shared.module_gate`. Sin dependencias entre módulos de negocio.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Controla stock (`tracks_stock`) | El producto lleva existencias | PB-INV-001 |
| Unidad base | Unidad de medida única del producto | PB-INV-001/002 |
| Unidad de medida | Nombre, abreviatura, admite fracciones, activa | PB-INV-002 |
| Almacén | Lugar de existencias; uno predeterminado por empresa | PB-INV-002 |
| Regularización | Procedimiento futuro para cambiar unidad/control con historial | PB-INV-001 |

## Current behavior
Productos sin stock ni unidad (`catalog/domain/product.py:46-88`); sin unidades ni almacenes; `inventory` solo existe como clave de módulo (`modularity/domain/modules.py:24`).

## Expected behavior
Productos con `tracks_stock` (false por defecto) y `base_unit`; CRUD de unidades en catálogo y de almacenes en inventario; almacén predeterminado sembrado; bloqueos con mensajes.

## Domain rules / invariants
- INV-01 `tracks_stock=true` exige unidad base activa de la misma empresa; `false` deja `base_unit=null`.
- INV-02 Con historial (`shared.stock_history.has_history`), cambiar `tracks_stock` o la unidad base se rechaza; un valor igual al actual no cuenta como cambio.
- INV-03 Unidad: nombre y abreviatura obligatorios, únicos por empresa sin distinguir mayúsculas; sin eliminación.
- INV-04 Unidad asignada a algún producto: solo cambia `active`.
- INV-05 Una unidad inactiva no se asigna a productos; los que ya la tienen la conservan.
- INV-06 Almacén: nombre obligatorio y único por empresa; exactamente un predeterminado por empresa (índice único parcial); el predeterminado debe estar activo y no se desactiva hasta designar otro.
- INV-07 No se desactiva un almacén con saldo ≠ 0 o recepciones pendientes (puerto `WarehouseActivity`; hoy responde no).
- INV-08 Campos de inventario del producto solo se escriben con Inventario habilitado.
- INV-09 Todo con `company_id` de la sesión; recursos ajenos responden 404.

## Acceptance criteria
- AC-01 Se puede activar «controla stock» y asignar unidad base por producto (crear y editar).
- AC-02 Productos existentes quedan `tracks_stock=false`, sin unidad (migración).
- AC-03 Con historial, cambiar unidad o control devuelve 409 `stock_history_locked` con mensaje que remite a la regularización; no se recalcula nada.
- AC-04 Activar stock sin unidad se rechaza (400, campo `base_unit_id`).
- AC-05 Lista/detalle/formulario muestran los datos de inventario solo con Inventario habilitado; sin costo ni valor.
- AC-06 Producto sin control de stock se crea, se vende y se compra sin pedir existencias (sin cambios en Ventas).
- AC-07 Unidades: crear, editar, activar/desactivar, buscar por nombre, filtrar por estado (inicial activos); unidad en uso no cambia significado ni se elimina.
- AC-08 Almacenes: la empresa tiene uno predeterminado (sembrado «Almacén principal»), puede crear otros, definir predeterminado y no ve los de otra empresa.
- AC-09 Desactivar un almacén con saldo o recepción pendiente se bloquea con motivo (409); el predeterminado tampoco se desactiva.

## Edge cases / Error cases
- EDGE-01 Dos primeras lecturas simultáneas siembran un solo almacén.
- EDGE-02 Nombre/abreviatura duplicados → 400 por campo.
- EDGE-03 Producto con unidad ya inactiva se edita sin tocar la unidad: válido.
- EDGE-04 Inventario deshabilitado: unidades/almacenes responden 403; escribir campos de inventario del producto → 400; desactivar stock sin historial → permitido.
- EDGE-05 `make-default` sobre almacén inactivo → 409.
- EDGE-06 PATCH sin tocar campos de inventario con producto con historial: válido.

## Authorization / permissions
Solo administrador de la empresa (`CompanyAdminPermission`); `required_modules=('inventory',)` en unidades y almacenes; productos siguen con `('catalog',)`.

## API contract
- API-01 `Product` agrega `tracks_stock: bool`, `base_unit_id: uuid|null`, `base_unit: {id,name,abbreviation}|null` (lectura); entrada opcional `tracks_stock`, `base_unit_id` (retrocompatible).
- API-02 `GET/POST /api/units/`, `GET/PATCH /api/units/<id>/`, `POST .../activate/`, `.../deactivate/`; filtros `active`, `search`; paginación como productos. Campos: id, name, abbreviation, allows_fractions, active, in_use.
- API-03 `GET/POST /api/warehouses/`, `GET/PATCH /api/warehouses/<id>/`, `POST .../activate/`, `.../deactivate/`, `.../make-default/`; filtros `active`, `search`. Campos: id, name, description, active, is_default.
- Errores: 400 por campo, 403 módulo/permiso, 404, 409 con `{detail, code}` (`stock_history_locked`, `unit_in_use`, `warehouse_has_stock`, `warehouse_pending_receipts`, `warehouse_is_default`, `warehouse_inactive`).

## UI behavior
- UI-01 Formulario de producto: sección «Inventario» (interruptor + selector) según DDR, solo con módulo habilitado.
- UI-02 Lista: columnas «Controla stock» y «Unidad base» condicionadas al módulo; detalle análogo.
- UI-03 `/inventory/configuration` con pestañas Almacenes y Unidades, listado + diálogo, filtro Activos por defecto.
- UI-04 Mensajes de bloqueo en `alert-warning`; unidad en uso con campos deshabilitados.
- UI-05 Submenú Inventario: Inicio, Almacenes y unidades, Ajustes.

## Non-functional requirements
Sin `float`; migraciones aditivas; textos en español; accesibilidad (labels, `role=tablist`).

## Out of scope
Movimientos, saldos, recepciones, ajustes, regularización, conversiones, costo/valor de inventario, integración con Ventas/Compras.

## Open questions
Ninguna bloqueante.

# Test Specification

## Unit tests
Dominio: `Product` (INV-01), `UnitOfMeasure`, `Warehouse` (INV-03..07).
## Integration tests
API productos (AC-01..06), unidades (AC-07), almacenes (AC-08, 09), aislamiento entre empresas (INV-09), gate de módulo (EDGE-04), siembra concurrente (EDGE-01), migración de productos existentes (AC-02), puerto `stock_history` con proveedor doble que devuelve True (AC-03), `WarehouseActivity` doble (AC-09), `test_boundaries` con `inventory: set()`.
Frontend (Karma): formulario, lista, detalle de producto; componente de configuración, servicios.
## E2E
**NO** — sin flujo crítico de punta a punta; sin nuevas dependencias.
## Regression tests
Suites de catálogo y ventas existentes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-04 | test_api catálogo + spec de formulario |
| AC-02 | test de migración |
| AC-03 | test_api con proveedor doble de historial |
| AC-05 | specs de lista/detalle/formulario con módulo on/off |
| AC-06 | test: producto sin stock se crea y se lee sin unidad; suite de Ventas |
| AC-07 | tests de dominio y API de unidades + spec de configuración |
| AC-08 | tests de API de almacenes (siembra, predeterminado, aislamiento) |
| AC-09 | test de API con doble de `WarehouseActivity` y caso del predeterminado |

# Implementation Plan

## Architecture considerations
Ver ADR: unidades en `catalog`, almacenes en `inventory`, puerto `shared/stock_history.py`.

## Proposed solution
Dominio puro por entidad, casos de uso con repositorios por `company_id`, vistas finas con `required_modules`, frontend en `features/inventory` y ampliación de `features/products`.

## Files/components affected
- Backend: `catalog/domain` (product, unit), `application`, `infrastructure/django` (models, mappers, repositories), `api` (serializers, views, urls), migración `catalog/0003`; nuevo `modules/inventory/` (domain, application, infrastructure, api, migration `0001`); `shared/stock_history.py`; `config/settings/base.py`, `config/urls.py`; `sales/tests/test_boundaries.py`; `docs/architecture/ddd.md`.
- Frontend: `features/products` (modelo, servicio, form, lista, detalle), `features/inventory` (páginas, servicios, modelos), `app.routes.ts`, `routes.json`, i18n, `docs/design/design-system.md`.

## Implementation steps
1. `shared/stock_history.py` + tests (INV-02).
2. Catálogo: unidad (dominio, modelo, repo, casos de uso, API) + migración 0003 (INV-03..05, AC-07).
3. Producto: campos, reglas, API (INV-01, 02, 08; AC-01..06).
4. Módulo `inventory`: almacén, siembra, predeterminado, puerto de actividad, API, registro en settings/urls, test de fronteras (INV-06, 07, 09; AC-08, 09).
5. Frontend productos (UI-01, 02).
6. Frontend configuración de inventario, rutas y menú (UI-03..05).
7. Documentación (`ddd.md`, `design-system.md`) y verificación.

## Database / migrations
`catalog/0003`: `CreateModel UnitOfMeasure` (unique ci por empresa) + `AddField tracks_stock` (default False) + `AddField base_unit` FK `PROTECT` nullable. `inventory/0001`: `Warehouse` con índice único parcial del predeterminado y único ci por empresa. No se edita ninguna migración existente.

## Risks
Proveedor real de historial sin enchufar hasta la historia de movimientos; siembra concurrente (bloqueo + restricción); línea base de specs rotos del frontend.

## New dependencies
Ninguna.
