# PLAN-2026-10-30-integracion-recepciones-entradas-inventario (v1)

**Task:** TASK-integracion-recepciones-entradas-inventario · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno (sin patrón visual nuevo ni decisión arquitectónica nueva)

> COMPLETO por dos ejes: comportamiento de dominio afectado (el modo con que se confirmó es un dato del documento) y contrato/datos con costo de reversa (campo nuevo en el API y migración).

## Objective
Cerrar PB-INT-001 sobre la integración Compras→Inventario ya existente (PB-COM-004): que la recepción **conserve el modo con que se confirmó** (con Inventario o documental) y que el resumen y el detalle muestren los textos, la identificación de ítems sin stock y las referencias de movimiento pedidos.

## Context
Ver `docs/tasks/TASK-integracion-recepciones-entradas-inventario.md`. Los AC de generación, atomicidad e idempotencia de la tarjeta ya se cumplen con PB-COM-004 y solo se verifican con regresiones.

# Specification

## Domain context
**Bounded Context:** Purchases. Inventory solo por `inventory.services` (sin cambios en Inventory).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Modo de inventario de la recepción (`inventory_mode`) | `inventory` = Inventario habilitado al confirmar; `documental` = deshabilitado al confirmar | PB-INT-001 |
| Ítem sin stock | Línea de producto sin control de stock; no genera entrada | PB-INT-001 |
| Recepción documental | Recepción sin movimiento de inventario | PB-INT-001 |

## Current behavior
Ver TASK (`receipt_queries.py:101-110`): el detalle usa el estado actual del módulo; no hay modo guardado.

## Expected behavior
Al confirmar se guarda el modo. El detalle se rige por el modo guardado, no por la configuración actual. El resumen del formulario y el detalle usan los textos de UI-01…UI-04.

## Domain rules / invariants
Existentes: INV-08…INV-10 de PB-COM-004 (entradas, atomicidad, idempotencia) no cambian.
Nuevas:
- INV-01: toda recepción nueva guarda `inventory_mode` = `inventory` si Inventario está habilitado al registrarla (aunque ninguna línea sea controlada), si no `documental`; el valor es inmutable.
- INV-02: el detalle nunca recalcula el modo desde la configuración actual; solo desde el valor guardado.
- INV-03: una recepción `documental` nunca expone movimientos, aunque Inventario se habilite después; una `inventory` expone los movimientos de su origen aunque Inventario se deshabilite después.
- INV-04: recepciones anteriores a esta task: `inventory` si tienen almacén; sin almacén → modo `null` y el detalle usa el comportamiento previo.
- INV-05: un reintento con el mismo `receipt_id` devuelve la recepción existente con su modo original, aunque la configuración haya cambiado (sin entradas nuevas).

## Acceptance criteria
Backend:
- AC-01: con Compras e Inventario activos, una recepción con N líneas controladas genera N entradas `in` en el almacén elegido, con origen `purchase_receipt`, y `inventory_mode = 'inventory'` (regresión de AC-08 de PB-COM-004).
- AC-02: líneas sin control de stock no generan movimientos; con Inventario deshabilitado la recepción se registra con `inventory_mode = 'documental'`, `warehouse` nulo y sin movimientos.
- AC-03: confirmar con Inventario habilitado y **sin** líneas controladas guarda `inventory_mode = 'inventory'` y `movements = []`.
- AC-04: el detalle de una recepción `inventory` conserva `movements` (con `reference`, cantidad, producto, almacén, unidad) y `warehouse` aunque Inventario se deshabilite después; `inventory_available` (estado actual) es `false`.
- AC-05: el detalle de una recepción `documental` devuelve `movements: null` y `warehouse: null` aunque Inventario se habilite después.
- AC-06: cada línea del detalle indica `stock_entry` (`true` si tiene movimiento en el libro, `false` si no) solo con modo `inventory`; con modo `documental` o `null` es `null`.
- AC-07: recepciones previas: la migración asigna `inventory` a las que tienen almacén y deja `null` en el resto; `null` conserva el comportamiento anterior (estado actual del módulo).
- AC-08: error de Inventario (almacén inactivo, producto inválido) → nada se guarda (ni recepción, ni modo, ni acumulado, ni movimientos); reintentar con el mismo `receipt_id` tras corregir no duplica (regresión de AC-10/11).
- AC-09: reintento con el mismo `receipt_id` después de apagar Inventario devuelve 200 con la recepción original y su modo, sin movimientos nuevos (INV-05).
- AC-10: confirmaciones concurrentes de la misma compra no duplican entradas ni superan lo comprado (regresión de AC-17 de PB-COM-004, PostgreSQL en publish).
- AC-11: `GET …/reception-form/` y las reglas de validación no cambian de forma; el contrato de creación no cambia (aditivo).
Interfaz:
- AC-12: en el resumen, con Inventario habilitado, se muestra «Esta recepción generará entradas de inventario» con almacén destino, y cada línea indica producto controlado (con cantidad y unidad) o «Sin control de stock · sin entrada»; con Inventario deshabilitado, «Recepción documental, sin movimiento de inventario».
- AC-13: el detalle de una recepción `inventory` lista los movimientos con referencia y cantidad y un enlace por movimiento/«Ver movimientos» hacia Inventario → Movimientos (solo si Inventario está habilitado ahora; si no, los movimientos se ven sin enlace y con una nota); las líneas sin entrada se rotulan «Sin control de stock · sin entrada».
- AC-14: el detalle de una `documental` muestra «Recepción documental, sin movimiento de inventario»; el de una `inventory` sin líneas controladas muestra «Esta recepción no generó entradas de inventario».
- AC-15: ante error en la confirmación no hay mensaje de éxito, los datos escritos se conservan y se reintenta con el mismo `receipt_id` (comportamiento existente, con prueba).
- AC-16: la lista de Movimientos conserva «Entrada por compra» y filtra por recepción (regresión de AC-25 de PB-COM-004).

## Edge cases / Error cases
- EDGE-01: Inventario deshabilitado después de confirmar → INV-03/AC-04.
- EDGE-02: Inventario habilitado después de una recepción documental → AC-05; no se generan entradas retroactivas.
- EDGE-03: recepción con modo `null` (histórica sin almacén) → comportamiento previo, sin afirmar un modo.
- EDGE-04: producto con `tracks_stock` cambiado después → `stock_entry` se calcula desde el libro (movimiento existente), no desde el catálogo actual.

## Authorization / permissions
Sin cambios: usuario autenticado con empresa y módulo `purchases` habilitado; los datos de movimientos vienen del libro de la empresa. El frontend no es la barrera.

## API contract
- API-01 `GET /api/purchases/{id}/receipts/{rid}/`: campos **aditivos** `inventory_mode` (`'inventory' | 'documental' | null`), `inventory_available` (bool, estado actual), `lines[].stock_entry` (`bool | null`) y `movements[].reference`; la semántica de `movements` y `warehouse` pasa a depender del modo guardado (INV-03). Compatible hacia atrás para clientes que ignoran campos nuevos.
- API-02 `POST …/receipts/`: respuesta con los mismos campos aditivos; request sin cambios.

## UI behavior
- UI-01 Resumen (`reception-form`, paso 2), con Inventario habilitado y alguna línea controlada: alerta `alert-info` «Esta recepción generará entradas de inventario» + almacén destino + conteo; por línea, badge «Entrada de stock» o texto atenuado «Sin control de stock · sin entrada».
- UI-02 Resumen, con Inventario deshabilitado: alerta informativa «Recepción documental, sin movimiento de inventario».
- UI-03 Detalle (`reception-detail`), modo `inventory`: tarjeta «Movimientos de inventario» con referencia, producto, almacén, cantidad y unidad (patrón `stock-output-card`); enlace «Ver movimientos» solo si `inventory_available`; si no está disponible, nota «Inventario está deshabilitado; los movimientos se muestran sin enlace». Líneas con `stock_entry = false` rotuladas «Sin control de stock · sin entrada».
- UI-04 Detalle, modo `documental`: nota «Recepción documental, sin movimiento de inventario» en lugar de la tarjeta; modo `inventory` sin movimientos: «Esta recepción no generó entradas de inventario»; modo `null`: comportamiento previo.
Plantillas de `design-system.md`: «Detalle con pestañas…», «Formulario con líneas y paso de resumen» y `alert` de Bootstrap; sin componentes compartidos nuevos.

## Non-functional requirements
Sin N+1 (los movimientos se leen una vez por recepción); cantidades `Decimal` como texto; migración aditiva sin bloqueo prolongado (columna con valor por defecto y `RunPython` acotado por empresa/almacén).

## Out of scope
Revertir recepciones (H-03 de PB-COM-004); numeración de recepciones; almacén por línea; entradas retroactivas al habilitar Inventario; cambios en Inventario; E2E.

## Open questions
Ninguna bloquea. Supuestos H-01…H-05 del TASK, reversibles con aprobación.

# Test Specification

## Unit tests
- `purchases/tests/test_receipt_application.py` (falsos): `RegisterReception` guarda `inventory_mode` según el puerto (`inventory` con módulo habilitado, aun sin líneas controladas; `documental` sin él); reintento tras cambiar disponibilidad (INV-05); `GetReceipt` usa el modo guardado y devuelve movimientos/`stock_entry`/`inventory_available` según INV-03, INV-04, EDGE-04.
- `purchases/tests/test_receipt_domain.py`: `Receipt` conserva `inventory_mode` y no lo cambia.
- Frontend (Karma): `reception-form.component.spec.ts` (UI-01, UI-02: textos, rótulo por línea, sin éxito parcial ante error con `receipt_id` reutilizado), `reception-detail.component.spec.ts` (UI-03, UI-04: modos `inventory`, `documental`, `null`, enlace según `inventory_available`), `receipts-api.service.spec.ts` (mapeo de campos nuevos).

## Integration tests
- `purchases/tests/test_receipt_api.py` (BD): AC-01…AC-06, AC-08, AC-09 con Inventario real (habilitar, deshabilitar y volver a habilitar el módulo con `module_gate`), conteo de `StockMovement`.
- `purchases/tests/test_receipt_repository.py`: ida y vuelta de `inventory_mode`; prueba de la migración de datos (con almacén → `inventory`, sin él → nulo).
- `makemigrations --check` (migración `0005`).
- Concurrencia (`test_receipt_concurrency.py`, PostgreSQL en publish): AC-10 se re-ejecuta tal cual.

## E2E
**NO.** Sin flujo nuevo de punta a punta; API real con Inventario y componentes cubren los AC. Revisión visual manual en `delivery-publish`.

## Regression tests
Suite completa de backend; `ng lint`, `ng build`, Karma de `features/purchases` y `features/inventory`; `test_boundaries`/`test_guards`/`test_enforcement`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02, AC-03 | `test_receipt_application`, `test_receipt_api` |
| AC-04, AC-05, AC-06 | `test_receipt_application`, `test_receipt_api` (módulo apagado/encendido) |
| AC-07 | `test_receipt_repository` (migración de datos) |
| AC-08, AC-09 | `test_receipt_application`, `test_receipt_api` |
| AC-10 | `test_receipt_concurrency` (PostgreSQL) |
| AC-11 | `test_receipt_api` (contrato de creación y formulario sin cambios) |
| AC-12 | `reception-form.component.spec.ts` |
| AC-13, AC-14 | `reception-detail.component.spec.ts` |
| AC-15 | `reception-form.component.spec.ts` |
| AC-16 | spec existente de `movement-list` (regresión) |

# Implementation Plan

## Architecture considerations
`docs/architecture/ddd.md`: el modo es un dato del agregado `Receipt` (dominio sin Django); la decisión de si Inventario estaba habilitado se toma en `application` (`RegisterReception`) con el puerto `StockEntry`; el detalle lee el modo guardado. Sin importaciones nuevas entre módulos.

## Proposed solution
Agregar `InventoryMode` (enum) y `Receipt.inventory_mode`; persistir en `ReceiptModel.inventory_mode` (nullable); `RegisterReception` lo fija al registrar; `GetReceipt.detail` deja de consultar `is_available()` para decidir y usa el modo (más `inventory_available` informativo); `StockEntryMovement` gana `reference`; el serializer expone los campos aditivos; Angular ajusta modelos, resumen y detalle.

## Files/components affected
- **Backend** (`backend/modules/purchases/`): `domain/{enums,receipt}.py`; `application/{ports,receipt_commands,receipt_queries}.py`; `infrastructure/{adapters.py,django/{models,mappers,receipt_repository}.py}`; `migrations/0005_receipt_inventory_mode.py` (por `makemigrations` + `RunPython` de backfill); `api/receipt_serializers.py`; pruebas listadas.
- **Frontend** (`frontend/panel_admin/src/app/features/purchases/`): `models/receipt.ts`, `services/receipts-api.service.ts`, `pages/{reception-form,reception-detail}/*`, `testing/receipt-fixtures.ts`.
- **Docs**: `docs/producto/modulos-implementados.md` y nota en `docs/architecture/ddd.md` si corresponde.

## Implementation steps
1. **Dominio**: `InventoryMode` y campo en `Receipt` + prueba (INV-01).
2. **Persistencia**: campo en el modelo, `makemigrations`, backfill (con almacén → `inventory`), mappers y repositorio + prueba (AC-07).
3. **Aplicación**: `RegisterReception` fija el modo; `StockEntryMovement.reference`; `GetReceipt` por modo guardado, `stock_entry` por línea y `inventory_available` + pruebas (INV-01…05, AC-01…09).
4. **API**: serializer aditivo y pruebas de API con Inventario real (AC-01…AC-11).
5. **Frontend**: modelos/servicio/fixtures; resumen UI-01/02; detalle UI-03/04 + specs (AC-12…AC-16).
6. **Documentación** y verificación local: `manage.py test`, `makemigrations --check`, `ng lint`, `ng build`, Karma de `features/purchases` e `inventory`.

## Database / migrations
`0005_receipt_inventory_mode`: columna `inventory_mode` `CharField(max_length=20, null=True, blank=True)` en `purchases_receipt` + `RunPython` que asigna `inventory` a las filas con `warehouse_id`. No se edita ninguna migración aplicada. Rollback: la columna es nullable y el código previo la ignora; `migrate purchases 0004` la elimina sin pérdida de datos de negocio.

## Risks
- Backfill parcial (recepciones sin almacén quedan en `null`): documentado, comportamiento previo conservado.
- Cambio de semántica de `movements`/`warehouse` en el detalle: compatible porque el frontend único se actualiza en el mismo PR; revisar que no haya otro consumidor.
- `inventory_available` dependiente del módulo: el enlace «Ver movimientos» no debe aparecer si la ruta respondería 403.

## New dependencies
Ninguna.

## Changelog
_v1 inicial._
