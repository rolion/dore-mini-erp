# PLAN-2026-10-30-compras-recepciones-parciales-completas (v1)

**Task:** TASK-compras-recepciones-parciales-completas · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR formulario-y-detalle-recepcion](../design/DDR-compras-recepciones-parciales-completas-formulario-y-detalle-recepcion.md) · [ADR modelo-y-persistencia](../adr/ADR-compras-recepciones-parciales-completas-modelo-y-persistencia.md) · [ADR integracion-inventario-y-contrato](../adr/ADR-compras-recepciones-parciales-completas-integracion-inventario-y-contrato.md)

> COMPLETO por los tres ejes: reglas e invariantes de dominio nuevas (acumulado, estado de recepción), frontera cruzada Compras→Inventario y contrato API/migración/ADR/DDR.

## Objective
Permitir que un administrador registre una o varias recepciones, parciales o completas, de una compra confirmada, con fecha y cantidades por línea sin exceder lo comprado, calculando el estado de recepción; con Inventario activo, dar entrada en un almacén a los productos controlados en la misma operación.

## Context
Ver `docs/tasks/TASK-compras-recepciones-parciales-completas.md` (supuestos H-01…H-10). Parte de `main` en `81c0093` con PB-COM-003 integrado.

# Specification

## Domain context
**Bounded Context:** Purchases (propietario). **Inventory** como integración opcional, solo por su fachada `inventory.services`. Sin cambios en Catalog, Expenses ni pagos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Recepción (`Receipt`) | Documento que registra las cantidades recibidas de una compra en una fecha | PB-COM-004 |
| Estado de la recepción | `confirmed` («Confirmada») o `reverted` («Revertida», sin acción en esta task) | PB-COM-004 (H-03) |
| Estado de recepción de la compra | `not_received` («Sin recibir»), `partial` («Recibida parcialmente»), `received` («Recibida») | PB-COM-003 |
| Comprada / Recibida / Pendiente | Cantidad de la línea / suma de recepciones confirmadas / comprada − recibida | PB-COM-004 |
| Producto controlado | Producto con control de stock (`tracks_stock`) | Inventario |
| Inventario activo | Módulo `inventory` habilitado para la empresa | Modularity |
| Referencia de recepción | `REC-` + 8 primeros hex mayúsculos del id | H-01 |
| `receive` | Acción permitida (`allowed_actions`) para registrar una recepción | ADR |

## Current behavior
No hay recepciones. `reception_status` siempre es `not_received` y la acción deshabilitada en el detalle (`purchase-detail.component.html:114-116`). La cancelación de una confirmada siempre es posible (`purchase.py:259-263`). Inventario ya soporta entradas con origen `purchase_receipt` (`inventory/domain/movement.py:37`).

## Expected behavior
Desde el detalle de una compra confirmada con pendiente, «Registrar recepción» abre un formulario con las líneas y sus pendientes; la persona indica cantidades a recibir (puede omitir líneas), elige fecha y, si aplica, almacén, revisa y confirma. La recepción queda registrada, el acumulado y el estado de recepción de la compra se actualizan (parcial o completa) con independencia del pago, y con Inventario activo se crean las entradas de stock de los productos controlados en la misma operación. La compra deja de poder cancelarse. Se pueden listar y consultar las recepciones (con sus movimientos).

## Domain rules / invariants
Existentes: INV-05 de PB-COM-003 (no cancelar con actividad; ahora alcanzable); estados solo por métodos del agregado; `company_id` en toda consulta.
Nuevas:
- INV-01: solo una compra `confirmed` admite recepciones (si no, 409).
- INV-02: por línea, Σ cantidades de recepciones `confirmed` ≤ cantidad comprada.
- INV-03: cada línea de recepción refiere una línea existente de la compra, sin repetirse; cantidad > 0, 3 decimales como máximo, entera si la unidad no admite fracciones.
- INV-04: una recepción tiene ≥ 1 línea (las de cantidad cero se omiten en la interfaz; el API rechaza el cero).
- INV-05: fecha obligatoria, válida y no futura.
- INV-06: `reception_status` = `received` si todas las líneas están completas; `partial` si alguna tiene acumulado > 0; si no, `not_received`. No depende de `payment_status`.
- INV-07: la recepción confirmada es inmutable; `reverted` no lo produce ninguna acción de esta task.
- INV-08: con Inventario activo y ≥ 1 línea controlada, `warehouse_id` es obligatorio, de la empresa y activo; se crea una entrada por línea controlada con origen `(purchase_receipt, receipt.id, product_id)`; recepción, compra y entradas se confirman todas o ninguna.
- INV-09: sin Inventario activo (o sin líneas controladas) no se crean movimientos y `warehouse_id` se ignora y no se guarda.
- INV-10: repetir `POST` con el mismo `receipt_id` (misma compra) devuelve la recepción existente sin otro efecto.
- INV-11: dos recepciones simultáneas de la misma compra no superan lo comprado (bloqueo de la compra).
- INV-12: recibir no modifica precios, cantidades compradas, total, pagos ni gastos; `purchases` solo toca Inventario por su fachada.

## Acceptance criteria
Backend:
- AC-01: `POST /api/purchases/{id}/receipts/` sobre una compra confirmada con líneas válidas → 201 con la recepción (referencia `REC-…`, fecha, estado `confirmed`, usuario, líneas) y el detalle de la compra muestra `received_quantity`/`pending_quantity` actualizados.
- AC-02: varias recepciones acumulan; la compra pasa a `partial` mientras quede pendiente y a `received` cuando todas las líneas se completan; `payment_status` no cambia.
- AC-03: cantidad ausente, no numérica, negativa o cero → 400 `lines[i].quantity`; con más de 3 decimales o fracción en unidad entera → 400; acumulado > comprado → 400 en esa línea indicando el pendiente; no se guarda nada.
- AC-04: sin líneas → 400 `lines`; línea repetida o `item_id` ajeno a la compra → 400 en esa posición; todos los errores de líneas se devuelven juntos.
- AC-05: fecha ausente, inválida o futura → 400 `receipt_date`.
- AC-06: compra en borrador o cancelada → 409 «Solo una compra confirmada admite recepciones.» sin cambios.
- AC-07: Inventario deshabilitado → recepción documental: 201, sin movimientos, `warehouse` nulo, `movements: null` en el detalle; `warehouse_id` enviado se ignora.
- AC-08: Inventario habilitado con líneas controladas: sin `warehouse_id` → 400 `warehouse_id`; almacén inexistente, de otra empresa o inactivo → 400 `warehouse_id`; con almacén activo → una entrada `in` por línea controlada (cantidad, almacén, referencia `REC-…`, usuario, origen `purchase_receipt`) y el saldo aumenta lo recibido.
- AC-09: líneas no controladas (o recepción sin ninguna controlada) no generan entradas ni exigen almacén.
- AC-10: atomicidad: si Inventario rechaza (p. ej. almacén desactivado) no queda recepción, ni acumulado, ni `reception_status` cambiado, ni movimientos.
- AC-11: idempotencia: repetir el mismo `receipt_id` → 200 con la misma recepción, un solo conjunto de movimientos y el mismo acumulado; ese id en otra compra → 409 `receipt_conflict`.
- AC-12: tras la primera recepción la compra no puede cancelarse (409 con el mensaje existente) y `allowed_actions` no incluye `cancel`; incluye `receive` para `confirmed` con pendiente y no para `received`, `draft` ni `cancelled`.
- AC-13: `GET …/receipts/` lista paginada de la compra (fecha desc); `GET …/receipts/{rid}/` devuelve líneas, almacén y movimientos (`null` con Inventario apagado, `[]` si no hubo entradas); recepción de otra compra o de otra empresa → 404.
- AC-14: `GET …/reception-form/` devuelve por línea `ordered/received/pending/tracks_stock/allows_fractions`, `inventory_enabled`, `warehouses` y `warehouse_id` sugerido (solo si aplica); 409 si la compra no está confirmada.
- AC-15: aislamiento y acceso: otra empresa → 404; sin token → 401; módulo `purchases` deshabilitado → 403 `module_disabled`; métodos no soportados → 405.
- AC-16: recibir no crea ni modifica gastos ni pagos; `ConfirmPurchase`/`CancelPurchase` y el PATCH siguen con su comportamiento.
- AC-17: dos recepciones simultáneas que juntas exceden lo comprado → una se registra y la otra falla con 400 (bloqueo verificado en PostgreSQL real en publish).
Interfaz:
- AC-18: el detalle de la compra tiene pestañas «Resumen» y «Recepciones»; la segunda muestra el avance por producto y la tabla de recepciones (referencia, fecha, estado, usuario) con vacío explicado; la tabla de productos del Resumen de una confirmada muestra Recibida y Pendiente.
- AC-19: «Registrar recepción» sale solo con `receive` en `allowed_actions`; con la compra completa se explica «Compra recibida por completo»; no hay entrada nueva en el menú lateral.
- AC-20: formulario: fecha (hoy por defecto, no futura); líneas con producto de solo lectura, comprada, recibida, pendiente y «A recibir»; no permite exceder el pendiente ni valores inválidos; exige ≥ 1 cantidad positiva; omite las líneas en cero al enviar; «Recibir todo lo pendiente».
- AC-21: el almacén aparece y es obligatorio solo con Inventario activo y productos controlados con pendiente; sin ellos no se muestra ni se exige; sin almacenes activos se explica y se bloquea el avance si hay líneas controladas con cantidad.
- AC-22: paso de resumen con los datos a confirmar y aviso de entradas de stock cuando aplica; «Confirmar recepción» se deshabilita mientras envía y reutiliza `receipt_id` en reintentos; errores del servidor se muestran por línea/campo sin borrar lo escrito.
- AC-23: tras confirmar: toast, vuelta al detalle de la compra en la pestaña «Recepciones» con pendientes y estado actualizados.
- AC-24: detalle de recepción: referencia, compra, fecha, estado, usuario, almacén cuando aplica, productos y cantidades recibidas, movimientos vinculados (con enlace a Movimientos) solo con Inventario habilitado.
- AC-25: la lista de Movimientos etiqueta «Entrada por compra» las entradas con origen `purchase_receipt`.

## Edge cases / Error cases
- EDGE-01: recepción total en una sola operación → `received`; última recepción parcial restante → `received`.
- EDGE-02: producto desactivado o no comprable después de confirmar → se puede recibir (H-06).
- EDGE-03: recepción solo de productos no controlados con Inventario activo → sin almacén ni movimientos.
- EDGE-04: almacén desactivado entre abrir el formulario y confirmar → 400 `warehouse_id`, nada se guarda.
- EDGE-05: compra cancelada mientras se llenaba el formulario → 409 al confirmar.
- EDGE-06: cantidades con decimales en unidades enteras → 400 por línea.
- EDGE-07: `receipt_id` o `item_id` que no son UUID → 400; id de compra/recepción no UUID en la URL → 404.
- EDGE-08: Inventario deshabilitado luego de haber recibido → el detalle no muestra movimientos; las recepciones persisten.
- EDGE-09: compras confirmadas antes de esta task → `reception_status = not_received`, sin recepciones, pendiente = comprada.

## Authorization / permissions
Igual que PB-COM-002/003: usuario autenticado con empresa y módulo `purchases` habilitado (`required_modules = ('purchases',)`); solo existe el rol administrador. Los datos de almacén/movimientos solo se devuelven con Inventario habilitado. La empresa sale del usuario autenticado.

## API contract
API-01 `GET …/reception-form/`; API-02 `POST …/receipts/`; API-03 `GET …/receipts/`; API-04 `GET …/receipts/{rid}/`; API-05 campos nuevos del detalle de compra (`received_quantity`, `pending_quantity` por línea; `receive` en `allowed_actions`). Aditivo y compatible hacia atrás (detalle en el ADR de integración).

## UI behavior
UI-01 detalle de compra con pestañas Resumen/Recepciones; UI-02 columnas Recibida/Pendiente y acción «Registrar recepción»; UI-03 formulario de recepción en dos pasos (plantilla «Formulario con líneas y paso de resumen»); UI-04 detalle de recepción (plantilla Detalle + `stock-output-card`); UI-05 etiqueta «Entrada por compra» en Movimientos. Detalle en el DDR.

## Non-functional requirements
Operación atómica con bloqueo de fila (compra → almacén); sin N+1 en listas y detalle (agregaciones por compra); sin dependencias nuevas; migración aditiva; cantidades `Decimal` serializadas como texto.

## Out of scope
Revertir recepciones y sus contramovimientos (H-03); pagos; numeración correlativa; notas en la recepción; recepción por almacén y línea; recepciones de compras no confirmadas; edición o eliminación de recepciones; recepción sobre lo no comprado; costeo/actualización de precios; adjuntos; notificaciones; E2E.

## Open questions
Ninguna bloquea. Supuestos H-01…H-10 del TASK, reversibles con aprobación.

# Test Specification

## Unit tests
- `purchases/tests/test_receipt_domain.py` (sin BD): `Purchase.receive` — INV-01…06, errores juntos por posición, cálculo de `reception_status` (`partial`/`received`), no futura, fracciones, `allowed_actions`, inmutabilidad de la compra.
- `purchases/tests/test_receipt_application.py` (repositorios y puerto de stock falsos): `RegisterReception` — con y sin Inventario, almacén requerido/inválido, solo no controlados, atomicidad (falla del stock → nada guardado), idempotencia por `receipt_id`, concurrencia lógica (acumulado leído tras el bloqueo), consultas (`GetReceptionForm`, lista y detalle).
- Frontend (Karma): `purchases-api.service.spec.ts` (mapeo y errores de los cuatro endpoints), `reception-math`/utilidades de cantidades si se extraen, `purchase-detail.component.spec.ts` (pestañas, Recibida/Pendiente, botón por `receive`), `reception-tab`/lista, `reception-form.component.spec.ts` (validaciones por línea, ≥ 1 positiva, omisión de ceros, almacén condicionado, resumen, envío con `receipt_id`, errores), `reception-detail.component.spec.ts`, rutas, y la etiqueta en `movement-list`.

## Integration tests
- `purchases/tests/test_receipt_api.py` (BD): AC-01…AC-16 con y sin Inventario habilitado (módulo + productos controlados + almacenes reales), conteo de `StockMovement`/`Expense`, saldo, 401/403/404/405, aislamiento entre empresas.
- `purchases/tests/test_receipt_repository.py` (BD): ida y vuelta, acumulado por línea (solo `confirmed`), aislamiento, conservación del `purchase_item_id` tras `PurchaseRepository.save`.
- `makemigrations --check` (migración `0004`).
- `purchases/tests/test_receipt_concurrency.py` (BD, PostgreSQL real en publish; `skipUnless` como la de compras): AC-17.
- Guardas: `test_boundaries` (`purchases → inventory`), `accounts/test_guards` y `modularity/tests/test_enforcement` (rutas nuevas con `required_modules`).

## E2E
**NO.** El flujo se cubre con API (incluida la integración real con Inventario) y componentes; no hay Playwright ni dependencia que lo justifique. Revisión visual manual en `delivery-publish`.

## Regression tests
Suite completa de backend; `ng lint`, `ng build`, Karma de `features/purchases`, `features/inventory` (lista de movimientos) y rutas/menú. Las pruebas de PB-COM-001/002/003 (incluida la cancelación) deben seguir verdes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | `test_receipt_domain`, `test_receipt_application`, `test_receipt_api` |
| AC-03, AC-04, AC-05 | `test_receipt_domain`, `test_receipt_api` |
| AC-06 | `test_receipt_domain`, `test_receipt_api` |
| AC-07, AC-09 | `test_receipt_application`, `test_receipt_api` |
| AC-08 | `test_receipt_application`, `test_receipt_api` (con Inventario real y saldo) |
| AC-10 | `test_receipt_application`, `test_receipt_api` (almacén inactivo) |
| AC-11 | `test_receipt_application`, `test_receipt_api` |
| AC-12 | `test_receipt_domain`, `test_receipt_api` |
| AC-13, AC-14 | `test_receipt_api`, `test_receipt_repository`, `purchases-api.service.spec.ts` |
| AC-15 | `test_receipt_api`, `test_enforcement`, `test_guards` |
| AC-16 | `test_receipt_api` (conteos), `test_boundaries` |
| AC-17 | `test_receipt_concurrency` (PostgreSQL) y revisión del `select_for_update` |
| AC-18, AC-19 | `purchase-detail.component.spec.ts`, componente de la pestaña |
| AC-20, AC-21, AC-22, AC-23 | `reception-form.component.spec.ts`, `purchases-api.service.spec.ts` |
| AC-24 | `reception-detail.component.spec.ts` |
| AC-25 | spec de `movement-list` |

# Implementation Plan

## Architecture considerations
`docs/architecture/ddd.md` y los ADR. Estado y reglas en el agregado; reglas entre módulos (Inventario habilitado, producto controlado, almacén) y la idempotencia en `application`; mapeo de errores en la vista (`_run`). La única importación nueva entre módulos es `purchases/infrastructure/adapters.py → modules.inventory.services`.

## Proposed solution
`ReceiptStatus`, `Receipt`/`ReceiptLine`, `Purchase.receive` y `PurchaseNotReceivable` en el dominio; `ReceiptRepository`; casos de uso `RegisterReception`, `GetReceptionForm`, `ListReceipts`, `GetReceipt`; puerto `StockEntry` + `StockEntryAdapter`; vistas, serializers y rutas bajo `purchases/`. En Angular: modelos y servicio ampliados, pestañas en el detalle, `ReceptionFormComponent` y `ReceptionDetailComponent`, etiqueta en Movimientos.

## Files/components affected
- **Backend** (`backend/modules/purchases/`): `domain/{enums,exceptions,purchase,receipt,repositories}.py`; `application/{ports,purchase_queries,receipt_commands,receipt_queries}.py`; `infrastructure/{adapters.py,django/{models,mappers,receipt_repository}.py}`; `migrations/0004_receipts.py` (por `makemigrations`); `api/{receipt_views,receipt_serializers,purchase_serializers,purchase_urls}.py`; pruebas listadas; `sales/tests/test_boundaries.py` (dependencia permitida).
- **Frontend** (`frontend/panel_admin/src/app/features/purchases/`): `models/{purchase,receipt}.ts`, `services/{purchases-api.service,reception-quantities}.ts`, `pages/{purchase-detail,reception-form,reception-detail}/*`, `purchases.routes.ts`, `testing/*`; y en `features/inventory/` la etiqueta del origen en la lista/detalle de movimientos.
- **Docs**: `docs/design/design-system.md` (notas en «Detalle con pestañas…» y «Formulario con líneas…»), `docs/producto/modulos-implementados.md`, `docs/architecture/ddd.md` (recepciones y dependencia `purchases → inventory`).

## Implementation steps
1. **Dominio**: enums, `Receipt`, `Purchase.receive`/`allowed_actions`/`pending`, excepción y cálculo de estado + pruebas (INV-01…07, AC-01…06, AC-12).
2. **Infraestructura**: modelos, migración `0004`, mappers, `DjangoReceiptRepository` (`received_totals`, `list_for_purchase`) + prueba (INV-02, conservación del `purchase_item_id`).
3. **Aplicación**: puerto `StockEntry`, `RegisterReception` (bloqueo, acumulado, entradas, idempotencia), `GetReceptionForm`, consultas + pruebas con falsos (INV-08…11, AC-07…11, AC-14).
4. **Adaptador de Inventario** (`StockEntryAdapter`) y actualización de `test_boundaries` (AC-16).
5. **API**: serializers, vistas, rutas, campos del detalle de compra y guardas (AC-01…AC-16) con pruebas de API reales, incluidas con Inventario.
6. **Frontend base**: modelos, servicio, utilidades de cantidades, fixtures y pruebas (AC-13, 14).
7. **Detalle de compra**: pestañas, Recibida/Pendiente, acción (AC-18, 19).
8. **Formulario de recepción** en dos pasos (AC-20…23) y **detalle de recepción** (AC-24); rutas.
9. **Etiqueta de Movimientos** (AC-25).
10. **Documentación** y verificación local: `manage.py test`, `makemigrations --check`, `ng lint`, `ng build`, Karma de los features tocados.

## Database / migrations
`purchases/migrations/0004_receipts.py` por `makemigrations`: crea `purchases_receipt` y `purchases_receipt_item`. No se editan `0001`…`0003`. Rollback: ver ADR de modelo (`migrate purchases 0003`, tras devolver `reception_status` a `not_received` en entornos con datos).

## Risks
- Atomicidad cruzada y bloqueos: orden fijo compra → almacén; probada con falla de Inventario y con PostgreSQL real en publish.
- Reglas de `Purchase.receive` con tres decimales vs. cuatro de Inventario: la cantidad de la recepción cabe en el libro (≤ 4 decimales).
- Formulario con muchas líneas (hasta 200): tabla simple, sin virtualización; aceptable en el MVP.
- Estado «Revertida» sin acción: la UI lo soporta; documentado (H-03).
- `purchase_item_id` por UUID: depende de que las líneas confirmadas no se editen (hoy así).

## New dependencies
Ninguna.
