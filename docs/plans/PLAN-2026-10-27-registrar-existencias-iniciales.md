# PLAN-2026-10-27-registrar-existencias-iniciales (v2)

**Task:** TASK-registrar-existencias-iniciales · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-registrar-existencias-iniciales-pantallas-existencias-apertura.md`, `docs/adr/ADR-registrar-existencias-iniciales-apertura-sobre-libro-de-movimientos.md` (reemplaza al ADR v1 `...-movimientos-saldos-idempotencia`)

## Objective
Permitir que el administrador cargue el stock inicial de productos que controlan stock en un almacén activo, creando movimientos de apertura y saldos de forma idempotente, con una pantalla de Existencias y movimientos como destino.

## Context
PB-INV-001/002 (PR #20) dejaron productos con `tracks_stock`/unidad base, almacenes y dos puertos sin datos. Ver TASK.

# Specification

## Domain context
Bounded context `inventory` (movimientos, saldos, aperturas). Relacionado: `catalog` (producto/unidad, solo vía `catalog.services`), `modularity` (gate del módulo).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Apertura | Carga única de stock inicial de uno o más productos en un almacén | PB-INV-003 |
| Movimiento | Registro inmutable de un cambio de existencia (aquí tipo `opening`) | PB-INV-003 |
| Saldo | Existencia actual de un producto en un almacén | PB-INV-003 |
| Clave de apertura (`opening_id`) | UUID generado por el formulario para que reintentos no dupliquen | ADR |
| Ajuste | Corrección posterior (otra historia) | PB-INV-003 |

## Current behavior
(v2) `main` ya trae el libro de movimientos de PB-INV-004: `inventory/infrastructure/django/models.py` (`StockMovementModel`), `inventory/services.py` (`record_movement`, `get_balance`, `has_history`), `application/movement_use_cases.py` (`RecordMovement`), `movement_repository.py` (saldo agregado, `locked`), `apps.py` (registra `stock_history`), `LedgerWarehouseActivity`, `/api/stock-movements/` y su pantalla. No existe una operación de apertura ni una pantalla de Existencias.

## Expected behavior
El administrador elige almacén activo, fecha, referencia y líneas (producto que controla stock + cantidad ≥ 0), revisa el resumen y confirma. Se crean, en una transacción, una entrada del libro (origen `inventory_opening`) por línea con cantidad > 0; el saldo es el del libro. Reintentar con la misma clave devuelve el resultado original sin crear nada. Después, Existencias muestra los saldos y cada uno abre sus movimientos.

## Domain rules / invariants
- **INV-01** Una apertura tiene ≥ 1 línea, sin producto repetido, referencia obligatoria (≤ 100), fecha no futura. (nueva)
- **INV-02** Cantidad ≥ 0, ≤ 3 decimales, máx. 11 enteros; entera si la unidad base no admite fracciones. (nueva)
- **INV-03** El almacén es de la empresa y está activo; cada producto es de la empresa y controla stock. (nueva)
- **INV-04** Solo se abre un par producto+almacén sin movimientos previos (de cualquier tipo). (nueva)
- **INV-05** (v2) Los movimientos son inmutables (invariante de PB-INV-004) y el saldo se calcula del libro; la apertura solo agrega entradas. (existente)
- **INV-06** Todo o nada: una línea inválida impide crear cualquier movimiento. (nueva)
- **INV-07** Misma clave + mismo contenido = réplica sin efectos; misma clave + distinto contenido = conflicto. (nueva)
- Existente: aislamiento por `company_id`; empresa del usuario autenticado.

## Acceptance criteria
- **AC-01** Se registra producto, almacén, cantidad ≥ 0, fecha y referencia de apertura (INV-01..03).
- **AC-02** Confirmar crea el movimiento de apertura y el saldo; repetir la confirmación (mismo `opening_id`) no duplica y devuelve el resultado original (INV-05, INV-07).
- **AC-03** Si el producto+almacén ya tiene movimientos se rechaza (409) y la UI señala la línea; las correcciones son ajustes (INV-04, INV-06).
- **AC-04** El formulario no permite productos duplicados, muestra unidad base de solo lectura, resumen previo (almacén, productos, cantidades) y cancelar no crea nada.
- **AC-05** Confirmar con éxito lleva a Existencias, que lista el saldo y permite abrir los movimientos; doble clic no envía dos veces.
- **AC-06** (v2: ya lo aporta PB-INV-004; se verifica con aperturas reales) Tras una apertura, Catálogo bloquea cambiar unidad base o control de stock del producto; un almacén con saldo ≠ 0 no se puede desactivar.

## Edge cases / Error cases
- **EDGE-01** (v2) Cantidad 0: se acepta en la apertura pero **no genera movimiento** (el libro exige cantidad > 0); el producto queda sin historial y puede abrirse después. Una apertura con todas las líneas en 0 no registra nada.
- **EDGE-02** Fracción en unidad que no la admite, más de 3 decimales, negativa, no numérica → 400 por línea.
- **EDGE-03** Dos confirmaciones simultáneas (misma clave) → una crea, la otra recibe la réplica; con claves distintas para el mismo par, la segunda recibe 409.
- **EDGE-04** Almacén inactivo/ajeno/inexistente, producto ajeno o sin control de stock → 400/404 sin efectos.
- **EDGE-05** Fecha futura → 400. Cuerpo sin líneas → 400.
- **EDGE-06** Módulo `inventory` deshabilitado → 403; usuario no administrador → 403.
- **EDGE-07** Clave ya usada con contenido distinto → 409 `opening_id_reused`.

## Authorization / permissions
Solo administrador de la empresa (`CompanyAdminPermission`) y módulo `inventory` habilitado (`required_modules = ('inventory',)`).

## API contract
- **API-01** `POST /api/stock/openings/` body `{opening_id, warehouse_id, movement_date, reference, lines:[{product_id, quantity}]}` → 201 `{opening_id, warehouse_id, movement_date, reference, lines:[{product_id, quantity, movement_id|null}]}` (`movement_id` nulo en líneas con cantidad 0); réplica → 200 con el mismo cuerpo. Errores: 400 (`lines[i].campo`), 404 almacén, 409 `stock_history_exists` (con `lines:[{index, product_id}]`) / `opening_id_reused`.
- **API-02** `GET /api/stock/?warehouse_id=` (paginado, orden por producto) → `{product_id, product_name, warehouse_id, warehouse_name, quantity, unit:{abbreviation, allows_fractions}}` (v2: sin `unit.name`; el saldo sale del libro).
- **API-03** (v2: eliminado) Los movimientos se leen con `GET /api/stock-movements/?product_id=&warehouse_id=` de PB-INV-004.
- **API-04** `GET /api/stock/opening-check/?warehouse_id=&product_id=…` (parámetro repetible) → `{products_with_history: [uuid]}`.
- **API-05** (Catálogo, aditivo) `GET /api/products/?tracks_stock=true|false` y `base_unit.allows_fractions` en la respuesta. Compatible hacia atrás.

## UI behavior
Derivado del DDR y de `design-system.md`:
- **UI-01** Existencias: plantilla Lista con filtro de almacén, botón «Registrar apertura», enlace «Movimientos»; vacío con mensaje guía.
- **UI-02** Apertura: plantilla Formulario con líneas; selector sin duplicados, unidad de solo lectura, validación de cantidad según fracciones; línea con historial en `table-warning` + alerta y «Revisar resumen» bloqueado.
- **UI-03** Resumen: `dl` + tabla; «Confirmar apertura» se deshabilita mientras envía; clave generada al abrir y reutilizada.
- **UI-04** Éxito → Existencias del almacén + toast; errores de servidor visibles sin perder el borrador.
- **UI-05** (v2) «Movimientos» de cada fila abre la lista de PB-INV-004 (`/pocketbiz/inventory/movements`) filtrada por producto y almacén; no hay pantalla de movimientos propia.
- **UI-06** Submenú «Existencias» (es/en/de), rutas con `moduleGuard`; `unsavedChangesGuard` en la apertura.

## Non-functional requirements
`Decimal` en backend, texto decimal en JSON; consultas de catálogo por lote (sin N+1); migración aditiva.

## Out of scope
Ajustes, transferencias, compras/ventas que mueven stock, búsqueda por nombre en Existencias, kardex avanzado, importación CSV, costos/valorización, recepciones pendientes reales, pantalla de regularización.

## Open questions (no bloquean)
Supuestos de TASK (cero admitido, fecha no futura, referencia obligatoria, producto inactivo): confirmables en la revisión del PR; cambiarlos es un ajuste local.

# Test Specification

## Unit tests
Dominio `StockOpening` (INV-01, 02); validación de cantidades.

## Integration tests
API con base de datos: apertura feliz con varias líneas (AC-01, 02), réplica (AC-02, EDGE-07), concurrencia con dos hilos (EDGE-03), historial previo (AC-03), validaciones (EDGE-01, 02, 04, 05), permisos y módulo (EDGE-06), aislamiento entre empresas, lecturas API-02..04, filtro y campo de Catálogo (API-05), puertos conectados: bloqueo de unidad en Catálogo y de desactivar almacén con saldo (AC-06), `test_boundaries` con `inventory → catalog`. Frontend (Karma): servicio, formulario (duplicados, unidad, fracciones, línea con historial, resumen, envío único, clave estable), lista de existencias, movimientos.

## E2E
**NO** — sin Playwright en el proyecto y la cobertura de API + componentes cubre el flujo; no se instala nada.

## Regression tests
Suites de `catalog`, `inventory`, `modularity` y la suite Karma contra la línea base (71 specs demo rotos).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Unit dominio + integración API-01 |
| AC-02 | Integración (réplica, concurrencia, restricciones únicas) |
| AC-03 | Integración 409 + spec del formulario (línea marcada) |
| AC-04 | Spec del formulario/resumen (duplicados, unidad, cancelar sin llamadas) |
| AC-05 | Spec de navegación tras éxito y botón deshabilitado en vuelo; integración API-02/03 |
| AC-06 | Integración Catálogo/almacén con datos reales |

# Implementation Plan

## Architecture considerations
Según ADR: movimientos y saldos en `inventory`, puerto `StockProductCatalog` sobre `catalog.services`, bloqueo por fila del almacén, restricciones de base como defensa final, puertos conectados en `ready()`.

## Proposed solution
Agregado `StockOpening` + caso de uso `RegisterOpening` (transaccional), repositorio Django con `select_for_update`, vistas finas bajo `api/stock/`, y feature Angular `inventory` ampliada.

## Files/components affected
- **Backend (v2):** `inventory/domain/{stock.py (StockOpening),movement.py (SOURCE_TYPES + inventory_opening),exceptions.py,repositories.py}`, `application/stock_use_cases.py` (`RegisterOpening`, `CheckOpeningHistory`, `ListStock`), `infrastructure/django/movement_repository.py` (`products_with_history`, `find_by_source_id`, `list_balances`), `api/{stock_views,stock_serializers,stock_urls}.py`; `catalog/api/{serializers.py,views.py}` y repositorio (filtro `tracks_stock` y `allows_fractions`); `config/urls.py`; tests. **Sin migraciones** (reutiliza `inventory/0002` de PB-INV-004).
- **Frontend:** `features/inventory/{models,services,pages/stock-list,pages/stock-opening,pages/stock-movements}`, rutas en `app.routes.ts`, `assets/data/routes.json`, i18n es/en/de, `features/products` (`allowsFractions` en `BaseUnit`, filtro).
- **Docs:** `design-system.md` (patrón nuevo), `architecture/ddd.md`, `producto/modulos-implementados.md`.

## Implementation steps
1. Catálogo: `allows_fractions` en `base_unit`, filtro `tracks_stock`, `get_stock_products` (API-05).
2. Dominio `StockOpening` y reglas puras (INV-01, 02).
3. Modelos y migración `0002` (restricciones únicas y check) (INV-04, 05).
4. `RegisterOpening` con puerto, transacción, bloqueo, réplica y mapeo de integridad (AC-01..03, INV-03..07, EDGE-*).
5. API-01..04 + permisos; registrar rutas; actualizar `test_boundaries`.
6. Conectar puertos: `ready()` registra `stock_history`; adaptador real de actividad de almacén (AC-06).
7. Tests backend (unit, integración, concurrencia).
8. Frontend: modelos, servicio, Existencias, Movimientos, Apertura con resumen e idempotencia (UI-01..06), rutas, menú e i18n; specs.
9. Docs de diseño/arquitectura/producto; verificación (`manage.py test`, `makemigrations --check`, lint, build, Karma vs. línea base).

## Database / migrations
(v2) Ninguna: el libro y sus restricciones son los de `inventory/0002_stock_movements` (PB-INV-004).

## Risks
Carrera entre claves distintas (mitigada con bloqueo + restricción); olvido de registrar el proveedor (prueba de contrato en AC-06); Windows/reloj en tests intermitentes preexistentes (REV-03 anterior).

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-10-28): [Implementation Plan] Rebase sobre el libro de movimientos de PB-INV-004 (PR #21, ya en `main`): se eliminan las tablas, la migración y el modelo propios; la apertura usa `RecordMovement` con origen `inventory_opening`; se descarta `/api/stock/movements/` y la pantalla de movimientos propia. Solicitado por el usuario tras detectar el conflicto REV-07. [Specification] EDGE-01 (cantidad 0, que era un supuesto no bloqueante del plan) pasa de «crea movimiento y saldo 0» a «no genera movimiento»; AC-01..06 sin cambios. Se informa al usuario en el chat para que lo vete.
