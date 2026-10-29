# PLAN-2026-10-28-ajustar-existencias-con-motivo (v1)

**Task:** TASK-ajustar-existencias-con-motivo · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-ajustar-existencias-con-motivo-pantallas-ajustes-existencias · ADR: ninguno nuevo (se aplican los de PB-INV-003/004)

## Objective
Permitir a la persona administradora registrar un conteo (producto, almacén, cantidad contada, motivo), calcular la diferencia contra el saldo del libro y, al confirmar, generar la entrada o salida de ajuste en el libro, guardando el ajuste como documento trazable; exigir reconfirmar si el saldo cambió.

## Context
Ver TASK. Supuestos (no bloqueantes, revisables): diferencia cero no crea ajuste ni movimiento; estado «revertido» derivado del movimiento; «Revertir» llega con PB-INV-008; se permite ajustar productos sin movimientos previos; referencia generada por el servidor; cantidad contada con hasta 3 decimales (igual que la apertura).

# Specification

## Domain context
`inventory` (propietario del ajuste y del libro); `catalog` por el puerto `ProductDirectory` existente; `modularity` (`required_modules`).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Ajuste | Documento que corrige el saldo de un producto en un almacén tras un conteo | PB-INV-006 |
| Saldo del sistema | Σ entradas − Σ salidas del libro al momento de confirmar | PB-INV-004 |
| Cantidad contada | Existencia física informada, ≥ 0 | PB-INV-006 |
| Diferencia | contada − saldo del sistema; > 0 entrada, < 0 salida | PB-INV-006 |
| Movimiento de ajuste | Entrada/salida del libro con origen `inventory_adjustment` y el id del ajuste | PB-INV-004 |
| Saldo esperado | Saldo que la persona vio al contar; se compara al confirmar | PB-INV-006 |

Inconsistencia declarada: «Ajustes» ya nombra la configuración del módulo en el menú; la entrada nueva se llama «Ajustes de existencias».

## Current behavior
El libro y la apertura existen (`services.py:39-75`, `stock_use_cases.py:46-95`); el origen `inventory_adjustment` existe sin productor (`movement.py:33-36`); no hay ajustes ni pantalla.

## Expected behavior
Existe el ajuste confirmado (inmutable) ligado a su movimiento; la API lo crea, lista y detalla; la UI ofrece lista, «Nuevo ajuste» con revisión y detalle de solo lectura.

## Domain rules / invariants
- INV-01 Un ajuste guarda empresa, producto, almacén, saldo del sistema, cantidad contada, diferencia (con signo, ≠ 0), motivo, usuario y movimiento generado.
- INV-02 Inmutable: sin edición ni borrado; su estado se deriva del movimiento (confirmed/reversed).
- INV-03 Diferencia = contada − saldo del sistema, calculada por el dominio con `Decimal`; el cliente no la envía.
- INV-04 Diferencia 0 ⇒ no se crea ajuste ni movimiento (409 `no_difference`).
- INV-05 Motivo obligatorio (1-200 caracteres tras recortar); cantidad contada ≥ 0, ≤ 3 decimales, sin fracciones si la unidad no las admite; producto con `tracks_stock`; almacén activo y de la empresa.
- INV-06 Bajo el bloqueo del almacén, si el saldo actual ≠ saldo esperado ⇒ 409 `balance_changed` con el saldo vigente y no se registra nada.
- INV-07 Confirmar crea el ajuste y exactamente un movimiento (`kind` por el signo, cantidad = |diferencia|, origen `(inventory_adjustment, adjustment_id)`) en una sola transacción; el historial previo no se modifica. El ajuste puede dejar el saldo en la cantidad contada aunque quede por encima o por debajo (la salida no usa `allow_negative`: como contada ≥ 0, nunca deja saldo negativo).
- INV-08 Idempotencia por `adjustment_id` (clave del cliente): reintento con los mismos datos ⇒ el ajuste existente (200); con otros datos ⇒ 409 `adjustment_id_reused`. La réplica se evalúa antes que INV-06.
- INV-09 Todo con `company_id`; ids ajenos ⇒ 404 (existente para movimientos, nuevo para ajustes).

## Acceptance criteria
- AC-01 Producto, almacén, cantidad contada y motivo son obligatorios; el sistema calcula y devuelve la diferencia y el sentido (INV-03, INV-05).
- AC-02 Confirmar genera el movimiento de entrada o salida de ajuste y no modifica movimientos previos; el saldo pasa a ser la cantidad contada (INV-07).
- AC-03 Si el saldo cambió entre el conteo y la confirmación, la confirmación se rechaza con el saldo nuevo y la UI exige revisar y reconfirmar (INV-06).
- AC-04 Diferencia cero: la UI informa «Sin diferencia», no deja confirmar y la API no crea nada (INV-04).
- AC-05 Lista: referencia, fecha, producto, almacén, saldo del sistema, contada, diferencia, usuario y estado; filtros por fecha, producto y almacén.
- AC-06 Detalle de solo lectura con los datos de INV-01, el estado y el enlace al movimiento; sin editar ni eliminar; sin «Revertir» hasta PB-INV-008.
- AC-07 Reintentar la misma confirmación (doble clic, red) no duplica el ajuste ni el movimiento (INV-08).

## Edge cases / Error cases
- EDGE-01 Dos confirmaciones simultáneas del mismo almacén: serializadas por el bloqueo; la segunda ve el saldo nuevo ⇒ `balance_changed` o réplica.
- EDGE-02 Cantidad negativa, no numérica, `float`, con más de 3 decimales, fraccionaria en unidad entera, motivo vacío o de solo espacios ⇒ 400 por campo.
- EDGE-03 Producto sin `tracks_stock`, inexistente, almacén inactivo/ajeno ⇒ 400/404 (los mismos que el libro).
- EDGE-04 Saldo del sistema negativo (ventas con `allow_negative`): la diferencia es contada − saldo (entrada); válido.
- EDGE-05 Filtros inválidos (fecha, UUID, rango invertido) ⇒ 400 por parámetro.

## Authorization / permissions
Administrador de la empresa (`CompanyAdminPermission`); `required_modules = ('inventory',)`; la empresa sale del usuario.

## API contract
- API-01 `POST /api/stock-adjustments/` body `{adjustment_id, product_id, warehouse_id, counted_quantity, expected_system_quantity, reason}` → 201 (creado) / 200 (réplica) con el ítem de API-03 más `movement{id}`. Errores: 400 por campo; 404 almacén; 409 `balance_changed` (`{detail, code, current_balance}`), `no_difference`, `adjustment_id_reused`.
- API-02 `GET /api/stock-adjustments/balance/?product_id=&warehouse_id=` → `{system_quantity, unit{abbreviation, allows_fractions}}` (saldo vigente para el formulario; 0 si no hay movimientos).
- API-03 `GET /api/stock-adjustments/` (paginada de 25; filtros `date_from`, `date_to`, `product_id`, `warehouse_id`; orden por fecha desc). Ítem: `id`, `reference`, `created_at`, `product{id,name}`, `warehouse{id,name}`, `system_quantity`, `counted_quantity`, `difference` (string decimal con signo), `kind` (`in|out`), `unit{abbreviation}`, `user{id,name}`, `status` (`confirmed|reversed`).
- API-04 `GET /api/stock-adjustments/<uuid>/`: lo anterior más `reason` y `movement{id}`.
- Otros métodos ⇒ 405. Sin compatibilidad que romper (endpoints nuevos).
- Fachada Python (para PB-INV-008 y otros): `inventory.services.adjust_stock(company_id, *, adjustment_id, product_id, warehouse_id, counted_quantity, expected_system_quantity, reason, user_id, user_name)` solo si hace falta fuera del módulo; no es obligatoria en esta historia.

## UI behavior
- UI-01 Lista según DDR (filtros, columnas, badge de estado, vacío/cargando/error, paginación de servidor, «Nuevo ajuste»).
- UI-02 Formulario de dos pasos según DDR (saldo de solo lectura, diferencia en vivo, «Sin diferencia», clave de idempotencia, `unsavedChangesGuard`).
- UI-03 Reconfirmación tras 409 `balance_changed` (saldo nuevo visible, confirmación explícita).
- UI-04 Detalle de solo lectura; enlace al movimiento; sin «Revertir».
- UI-05 Submenú «Ajustes de existencias», rutas `inventory/adjustments`, `/new`, `/:id` con `moduleGuard`; botón «Ajustar» en Existencias; i18n es/en/de del menú; actualizar `routes.json` y `design-system.md`.

## Non-functional requirements
`Decimal` siempre (nunca `float`); índices por `(company_id, created_at)` y `(company_id, product_id, warehouse)`; textos en español; sin dependencias nuevas.

## Out of scope
Revertir (PB-INV-008), ajuste de varios productos, adjuntos, costos/valorización, pantalla de conteo físico por lotes, cambio del nombre del menú de configuración.

## Open questions
Si el ajuste debe poder ocurrir sobre un producto sin historial (hoy permitido) — revisable.

# Test Specification

## Unit tests
Dominio `StockAdjustment.create`: diferencia y sentido (INV-03), cero (INV-04), validaciones de motivo/cantidad/unidad (INV-05, EDGE-02).

## Integration tests
Caso de uso con BD: confirmar entrada y salida y comprobar saldo y movimiento (AC-02, INV-07), saldo cambiado (AC-03, INV-06), diferencia cero (AC-04), idempotencia secuencial y concurrente con `TransactionTestCase` (AC-07, INV-08, EDGE-01), saldo negativo (EDGE-04). API: crear/lista/detalle/balance, filtros, 400/403/404/405/409, aislamiento por empresa (INV-09), módulo deshabilitado. Frontend (Karma): servicio, lista, formulario (diferencia, «Sin diferencia», reconfirmación, doble envío), detalle, ruta/menú.

## E2E
**NO** — el flujo cruza un solo módulo y se cubre con pruebas de API y specs de componente; no se instala Playwright.

## Regression tests
Suites de inventario (almacenes, movimientos, existencias), catálogo y fronteras (`test_boundaries`); sidebar.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | tests de dominio + API (400 por campo) + spec del formulario |
| AC-02 | test de caso de uso/API: movimiento y saldo |
| AC-03 | test de API 409 + spec de reconfirmación |
| AC-04 | test de dominio/API + spec del formulario |
| AC-05, AC-06 | tests de API (filtros, detalle, 405) + specs de lista y detalle |
| AC-07 | test de idempotencia secuencial y concurrente |

# Implementation Plan

## Architecture considerations
Mismo patrón que la apertura: dominio puro, caso de uso que toma `repository.locked(warehouse_id)`, compara el saldo y registra el movimiento con `RecordMovement` (anidado en la misma transacción), repositorio Django con `company_id`, vistas finas. Sin fronteras nuevas.

## Proposed solution
Entidad `StockAdjustment` (dominio) con `create(...)` que calcula la diferencia; puerto `StockAdjustmentRepository`; casos de uso `ConfirmAdjustment`, `GetAdjustmentBalance`, `ListAdjustments`, `GetAdjustment`; modelo `StockAdjustmentModel` con `OneToOne` al movimiento (`PROTECT`); estado derivado del movimiento al leer. Frontend: modelos, servicio, `adjustment-list`, `adjustment-form`, `adjustment-detail`.

## Files/components affected
- Backend: `inventory/domain/adjustment.py`, `exceptions.py`, `repositories.py`; `application/adjustment_use_cases.py`; `infrastructure/django/models.py`, `adjustment_repository.py`, migración `0003`; `api/adjustment_views.py`, `adjustment_serializers.py`, `adjustment_urls.py`, `config/urls.py`; `tests/test_adjustments.py`; `docs/architecture/ddd.md`.
- Frontend: `features/inventory` (modelo, servicio, 3 páginas, `inventory.routes.ts` o rutas en `app.routes.ts`), `stock-list` (botón «Ajustar»), `routes.json`, menú lateral + i18n es/en/de, specs, `docs/design/design-system.md`.

## Implementation steps
1. Dominio `StockAdjustment` y excepciones (INV-01..05; AC-01, AC-04).
2. Modelo + migración `0003` (restricciones, índices).
3. Repositorio y caso de uso `ConfirmAdjustment` con bloqueo, comparación de saldo, réplica y movimiento (INV-06..08; AC-02, AC-03, AC-07).
4. API: balance, crear, lista con filtros, detalle (AC-05, AC-06; API-01..04) y registro en `config/urls.py`.
5. Pruebas backend (unitarias, integración, concurrencia, API, aislamiento).
6. Frontend: modelos y servicio; lista y detalle (UI-01, UI-04).
7. Frontend: formulario con revisión, «Sin diferencia» y reconfirmación (UI-02, UI-03).
8. Rutas, menú, botón «Ajustar», i18n, `routes.json` (UI-05).
9. Docs (`ddd.md`, `design-system.md`) y verificación completa (`manage.py test`, `npm test`, `npm run lint`, `npm run build`).

## Database / migrations
`inventory/0003`: `CreateModel StockAdjustment` (`inventory_stock_adjustment`): `id` (uuid = clave del cliente), `company_id`, `reference` (único por empresa), `product_id`, `warehouse` (FK PROTECT), `system_quantity`, `counted_quantity`, `difference` (decimales 16,4), `reason` (200), `user_id`, `user_name`, `movement` (OneToOne a `StockMovementModel`, PROTECT), `created_at`; `CheckConstraint difference <> 0`; índices indicados. No toca migraciones existentes.

## Risks
Colisión de nombre en el menú; concurrencia (requiere BD real); retrocompatibilidad del mensaje 409 de la apertura (sigue válido); nuevo contrato 409 `balance_changed` que PB-INV-008 no reutiliza.

## New dependencies
Ninguna.
