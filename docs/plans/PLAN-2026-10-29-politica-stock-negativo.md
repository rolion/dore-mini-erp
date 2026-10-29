# PLAN-2026-10-29-politica-stock-negativo (v1)

**Task:** TASK-politica-stock-negativo · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-politica-stock-negativo-campo-y-mensaje-saldo-insuficiente · ADR-politica-stock-negativo-lectura-y-aplicacion-de-la-politica

## Objective
Que cada empresa decida si Inventario permite salidas que dejen saldo negativo (bloqueado por defecto), aplicando la decisión de forma atómica en toda salida del libro y mostrando producto, almacén, cantidad solicitada y existencia actual cuando se rechaza.

## Context
Ver TASK. Alcance acordado con el usuario: política + Inventario; Ventas no se conecta (la entrega con descuento de stock y la reversión de recepciones llegan en sus propias historias y consumirán esta política).

# Specification

## Domain context
Bounded context `inventory` (aplica) y `modularity` (configuración por empresa). Sin cambios en `sales`, `catalog` ni `accounts`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Política de stock negativo | Ajuste de la empresa que permite o bloquea salidas que dejan el saldo bajo cero | PB-INV-007 |
| Permitir stock negativo | Ajuste `inventory.allow_negative_stock`; defecto desactivado | PB-INV-007 |
| Saldo insuficiente | Salida (o contramovimiento de salida) mayor que el saldo del producto en el almacén | `movement_use_cases.py:61-65` |
| Existencia actual | Saldo vigente del producto en el almacén al rechazar | PB-INV-007 |

## Current behavior
`RecordMovement`/`ReverseMovement` bloquean salidas sin saldo salvo que el llamante pase `allow_negative=True` (`movement_use_cases.py:58-65,81-84`); el 409 es genérico; no hay ajuste por empresa (`modularity/domain/settings.py:39-54`).

## Expected behavior
La empresa ve en Inventario → Configuración → General el interruptor «Permitir stock negativo» (desactivado). Con el bloqueo activo, una salida insuficiente se rechaza sin crear movimiento ni cambiar saldos y el error explica producto, almacén, solicitado y existente. Con la política permitida, la salida se registra y el saldo puede quedar negativo. Salidas simultáneas nunca consumen las mismas unidades.

## Domain rules / invariants
- **INV-01** (nueva) Toda empresa sin valor guardado rige `false` (bloqueado). Permitirlo exige guardar explícitamente `true`.
- **INV-02** (existente, ampliada) Con política bloqueada, una salida/contramovimiento de salida con `cantidad > saldo` no crea movimiento, ni marca revertido, ni toca nada.
- **INV-03** (existente) La lectura de la política, la comparación del saldo y la inserción ocurren dentro de `locked(warehouse_id)` (una sola transacción).
- **INV-04** (nueva) Las entradas nunca se bloquean por la política; deshabilitarla no corrige saldos negativos existentes.
- **INV-05** (nueva) La política no es decisión del llamante: no existe parámetro `allow_negative` en casos de uso ni fachada.

## Acceptance criteria
- **AC-01** Sin valor guardado, `get_inventory_settings` devuelve `allow_negative_stock=False`; la API de ajustes de `inventory` lista el campo `boolean` con defecto `false`; guardar `true` es una acción explícita y queda en el historial (valor anterior «Bloqueado», nuevo «Permitido», con usuario y fecha).
- **AC-02** Con bloqueo activo, una salida insuficiente (movimiento directo, reversión de una entrada, apertura/ajuste) lanza `insufficient_stock`, no inserta movimiento y no marca el original como revertido; el 409 incluye producto, almacén, `requested` y `available`.
- **AC-03** Con la política permitida la misma salida se registra y el saldo queda negativo; las entradas siguen registrándose en ambos modos.
- **AC-04** Dos salidas simultáneas cuya suma excede el saldo: solo una se confirma, la otra recibe `insufficient_stock` y el saldo final no es negativo (prueba de concurrencia sobre PostgreSQL).
- **AC-05** La UI: el campo muestra etiqueta, descripción del efecto en entregas, ajustes y reversión de recepciones, y valor predeterminado; al activar y guardar se pide confirmar la explicación de saldos negativos; cancelar no guarda; desactivar guarda sin diálogo; los errores conservan los datos del formulario.
- **AC-06** El formulario de ajuste (y futuras pantallas) muestra el aviso «No hay existencia suficiente» con producto, almacén, cantidad solicitada y existencia actual cuando recibe `insufficient_stock`, sin perder los datos.

## Edge cases / Error cases
- **EDGE-01** Cantidad solicitada = saldo exacto: se permite (el saldo queda en 0).
- **EDGE-02** Reintento idempotente de una operación de origen ya registrada devuelve el movimiento existente sin reevaluar la política (se mantiene).
- **EDGE-03** Módulo Inventario deshabilitado: no se puede guardar el ajuste (409 existente de PB-CFG-001); el valor guardado se conserva y rige al reactivar.
- **EDGE-04** Valor no booleano enviado a la API (`"si"`, `1`, `null`): 400 por clave, no se guarda nada.
- **EDGE-05** Se cambia la política mientras hay una salida en curso: gana el valor leído dentro del bloqueo de esa salida (consistente, sin estado intermedio).
- **EDGE-06** Política permitida y luego bloqueada con saldos negativos existentes: las nuevas salidas se rechazan; las entradas se aceptan.

## Authorization / permissions
Solo el administrador de la empresa cambia el ajuste (permiso por defecto de PB-CFG-001, `CompanyAdminPermission`). La política se aplica en el backend, nunca depende de la UI. Aislamiento por `company_id` en configuración y libro.

## API contract
- **API-01** `GET/PATCH /api/settings/inventory/` (ruta vigente de PB-CFG-001): se añade el ajuste `{key: 'inventory.allow_negative_stock', kind: 'boolean', value: 'false'|'true', default: 'false', label, description}`. Compatible hacia atrás (clave nueva; los clientes ignoran lo desconocido; el frontend se actualiza en este PR).
- **API-02** Error de saldo insuficiente en endpoints de inventario: `409 {detail, code: 'insufficient_stock', product: {id, name}, warehouse: {id, name}, requested: '5.000', available: '2.000'}` (decimales en texto). Reemplaza el 409 genérico (mismo `code`).
- **API-03** Fachada Python: `modularity.services.get_inventory_settings(company_id) -> InventorySettings`; `inventory.services.record_movement/reverse_movement` pierden el parámetro `allow_negative`.

## UI behavior
- **UI-01** Plantilla Formulario (`design-system.md` §5) en `module-settings`: interruptor «Permitir stock negativo» con descripción y «Valor predeterminado: Bloqueado» + «Restablecer».
- **UI-02** Confirmación al activar: `ModuleConfirmDialogComponent` con el texto del DDR; «Permitir» guarda, «Cancelar» no guarda.
- **UI-03** Componente `insufficient-stock-alert` (`alert-danger`, `role="alert"`) con Producto, Almacén, Solicitada, Existencia actual (unidad); no limpia el formulario; se oculta al reintentar.
- **UI-04** Estados de la pantalla: cargando, error de carga con reintento, guardando, error por campo, éxito, aviso de salida con cambios sin guardar (ya existentes).

## Non-functional requirements
Una lectura de configuración por salida, dentro del bloqueo; sin migraciones; textos en español; decimales como texto con tres decimales.

## Out of scope
Conectar Ventas a Inventario (descuento de stock al entregar, almacén en el pedido); endpoint y pantalla de reversión (PB-INV-008); recepciones de compra; corrección automática de saldos negativos; permisos distintos al administrador.

## Open questions
Ninguna bloqueante.

# Test Specification

## Unit tests
- Dominio de ajustes (`modularity`): `boolean` acepta `'true'/'false'` y rechaza otros valores; defecto `false`; `display` → «Permitido»/«Bloqueado» (AC-01, EDGE-04).
- `RecordMovement`/`ReverseMovement` con puerto de política falso: bloqueado + insuficiente → `MovementConflict` con detalle y sin `insert`; permitido → registra y saldo negativo; saldo exacto OK; entrada siempre OK (AC-02, AC-03, EDGE-01, INV-04).
- Frontend: `module-settings` pinta el interruptor, abre el diálogo al activar, no guarda al cancelar, guarda al desactivar sin diálogo; `insufficient-stock-alert` muestra los cuatro datos (AC-05, AC-06).

## Integration tests
- API de ajustes de `inventory`: GET con defecto, PATCH `true`, historial con valores anterior/nuevo, 400 con valor inválido, 403/aislamiento por empresa (AC-01, EDGE-03, EDGE-04).
- Casos con BD real: salida insuficiente por apertura/ajuste devuelve 409 con el cuerpo de API-02 y no crea movimiento (AC-02); con política permitida deja saldo negativo (AC-03).
- Fachada: `reverse_movement` de una entrada con saldo consumido → conflicto y original sigue sin revertir (AC-02); `test_boundaries` incluye `inventory → modularity`.

## Concurrency tests
`TransactionTestCase` en PostgreSQL con dos hilos registrando salidas que suman más que el saldo: una se confirma, la otra falla con `insufficient_stock`, saldo final ≥ 0 y un solo movimiento nuevo (AC-04, EDGE-05). Si el entorno de tests no es PostgreSQL, se declara la limitación en la prueba (como en `modularity/tests/test_concurrency.py`).

## E2E
NO — no hay flujo de entrega o reversión de punta a punta en la UI; la cobertura es unitaria + integración + componentes.

## Regression tests
Se mantienen verdes `inventory/tests/test_movements.py` (adaptado a la política en lugar de `allow_negative`), `test_adjustments.py`, `test_stock_query.py` (usa `allow_negative=True` para crear saldos negativos: se migra a guardar la política permitida) y la suite `modularity`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Unit dominio `modularity`; integración API de ajustes + historial |
| AC-02 | Unit `RecordMovement`/`ReverseMovement`; integración 409 con cuerpo API-02; fachada de reversión |
| AC-03 | Unit casos de uso; integración con política permitida |
| AC-04 | Prueba de concurrencia en PostgreSQL |
| AC-05 | Specs de `module-settings` (interruptor, diálogo, cancelar, guardar) |
| AC-06 | Spec de `insufficient-stock-alert` y de `adjustment-form` (409 conserva el formulario) |

# Implementation Plan

## Architecture considerations
Seguir el ADR: ajuste en el catálogo de `modularity`, fachada de lectura, puerto + adaptador en `inventory`, política consultada dentro de `locked()`, 409 estructurado. Dominio sin Django.

## Proposed solution
1. `modularity/domain/settings.py`: constante `BOOLEAN`, validación `'true'/'false'` (y `bool` JSON → texto normalizado; cualquier otro valor error «Elija una opción válida»), `display` → Permitido/Bloqueado, y `SettingDefinition('inventory.allow_negative_stock', 'inventory', 'Permitir stock negativo', <descripción>, BOOLEAN, 'false')`.
2. `modularity/services.py`: `InventorySettings` + `get_inventory_settings`.
3. `inventory`: puerto `InventoryPolicy` (`application/ports.py`), adaptador `ModularityInventoryPolicy` (`infrastructure/adapters.py`); `RecordMovement`/`ReverseMovement` lo reciben, quitan `allow_negative` y consultan la política dentro de `locked()`; `MovementConflict` lleva el detalle del saldo insuficiente.
4. Cableado en fachada (`services.py`), `ConfirmAdjustment` y las vistas/casos que construyen `RecordMovement` (apertura de existencias).
5. API: serializador 409 `insufficient_stock` (API-02) en `api/views.py` (`Conflict` ampliada) usado por apertura y ajustes.
6. Frontend `settings`: `SettingKind` + `boolean`, interruptor y diálogo en `module-settings`; `inventory`: `insufficient-stock-alert` y uso en `adjustment-form` y en el error de apertura, con `InventoryApiError` ampliado.
7. Docs: `docs/producto/modulos-implementados.md`, nota en `docs/architecture/ddd.md` (dependencia `inventory → modularity`).

## Files/components affected
- Backend: `modularity/domain/settings.py`, `modularity/services.py`, `modularity/api/serializers.py` (serialización del tipo si hace falta), `inventory/application/{ports,movement_use_cases,adjustment_use_cases}.py`, `inventory/domain/exceptions.py`, `inventory/infrastructure/adapters.py`, `inventory/services.py`, `inventory/api/{views,stock_views,adjustment_views}.py`.
- Frontend: `features/settings/{models/setting.ts, services/settings-api.service.ts, pages/module-settings/*}`, `features/inventory/{models/api-error.ts, components/insufficient-stock-alert/*, pages/adjustment-form/*, pages/stock-opening/*}`.
- Tests: `modularity/tests/*`, `inventory/tests/*`, `sales/tests/test_boundaries.py`, specs de frontend.
- Migraciones: ninguna.

## Implementation steps
1. Dominio de `modularity` + fachada + tests (INV-01, AC-01, EDGE-04).
2. Puerto/adaptador de política y refactor de `RecordMovement`/`ReverseMovement`/fachada; adaptar tests existentes que usaban `allow_negative` (INV-02..05, AC-02, AC-03).
3. Detalle del conflicto y 409 estructurado en API (API-02, AC-02).
4. Prueba de concurrencia en PostgreSQL (AC-04).
5. Frontend de configuración: interruptor + diálogo + specs (UI-01, UI-02, AC-05).
6. Componente de saldo insuficiente + integración en ajuste y apertura + specs (UI-03, AC-06).
7. Documentación (`modulos-implementados.md`, `ddd.md`) y verificación completa (backend `manage.py test`, frontend `npm test` contra la línea base, `npm run lint`).

## Database / migrations
Sin migraciones: el valor se guarda en la tabla genérica de ajustes por empresa y el historial en la tabla de cambios existentes.

## Risks
- Quitar `allow_negative` rompe tests que lo usaban para fabricar saldos negativos (`test_stock_query.py`, `test_movements.py`): migrarlos a guardar la política permitida.
- Dependencia nueva `inventory → modularity`: cubierta por el test de frontera.
- Prueba de concurrencia requiere PostgreSQL real; si el entorno no la corre, queda documentado.
- Valores `true` ya guardados con clave desconocida si se revierte el PR: inertes.

## New dependencies
Ninguna.
