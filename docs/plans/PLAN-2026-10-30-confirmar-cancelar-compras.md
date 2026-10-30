# PLAN-2026-10-30-confirmar-cancelar-compras (v1)

**Task:** TASK-confirmar-cancelar-compras · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR detalle-y-dialogos](../design/DDR-confirmar-cancelar-compras-detalle-y-dialogos.md) · [ADR ciclo-de-vida-y-contrato](../adr/ADR-confirmar-cancelar-compras-ciclo-de-vida-y-contrato.md)

> COMPLETO por el eje 1 (transiciones de estado y reglas de dominio nuevas) y el eje 3 (contrato API, migración, ADR/DDR).

## Objective
Permitir que un administrador confirme un borrador (bloqueándolo) o cancele una compra (con motivo, solo sin recepciones ni pagos) desde el detalle, con las reglas aplicadas por el backend, sin mover existencias y de forma idempotente.

## Context
Ver `docs/tasks/TASK-confirmar-cancelar-compras.md` (supuestos H-01…H-07). Parte de `main` en `5be4232` con PB-COM-002 integrado.

# Specification

## Domain context
**Bounded Context:** Purchases. Sin cambios en Inventory, Expenses ni Catalog.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Borrador / Confirmada / Cancelada | Estados documentales `draft`, `confirmed`, `cancelled` | PB-COM-003 |
| Confirmar | Cerrar el borrador: queda de solo lectura; no mueve stock | PB-COM-003 |
| Cancelar | Anular la compra con motivo; terminal | PB-COM-003 |
| Estado de recepción | `not_received` («Sin recibir»), `partial`, `received` | PB-COM-003 (H-02) |
| Estado de pago | `unpaid` («Sin pagar»), `partial`, `paid` | PB-COM-003 (H-02) |
| Referencia interna | `COM-` + 8 primeros hex mayúsculos del id | H-01 |
| Acciones permitidas (`allowed_actions`) | Lista que el servidor calcula para los botones | ADR |

## Current behavior
Solo existe `draft`; `PATCH` ya responde 409 si no es borrador (`domain/purchase.py:210-216`, `api/purchase_views.py:20-27`). No hay confirmar/cancelar ni motivo/fecha de cancelación. Detalle sin acciones de ciclo de vida (`purchase-detail.component.html`).

## Expected behavior
Desde el detalle de un borrador se puede Confirmar (diálogo con resumen y aviso) o Cancelar (diálogo con motivo). Una confirmada es de solo lectura, ofrece Cancelar solo mientras no haya recepciones ni pagos, y muestra recepción «Sin recibir» y pago «Sin pagar» sin ningún dato de existencias. Una cancelada muestra motivo y fecha y es de solo lectura. Repetir confirmar o cancelar devuelve el mismo estado sin duplicar nada.

## Domain rules / invariants
- INV-01: `confirm` solo desde `draft`; exige ≥ 1 línea (`items`: «La compra necesita al menos un producto.»).
- INV-02: al confirmar el proveedor debe existir en la empresa y estar activo (`supplier_id`: «Selecciona un proveedor activo.»); errores de INV-01/02 se devuelven juntos.
- INV-03: confirmada ⇒ no editable (cabecera, notas, líneas); `editable` = es borrador.
- INV-04: `cancel` desde `draft` o `confirmed`; exige `reason` no vacío, recortado, ≤ 500.
- INV-05: `cancel` se rechaza si `reception_status != not_received` o `payment_status != unpaid`.
- INV-06: `cancelled` es terminal: no se confirma, edita ni vuelve a cancelar con otro motivo.
- INV-07: `confirm` sobre confirmada y `cancel` sobre cancelada son idempotentes: sin cambios (ni fechas ni motivo), sin guardar.
- INV-08: `confirmed_at` y `cancelled_at` se fijan una sola vez al transitar; `cancellation_reason` solo existe si cancelada.
- INV-09: confirmar o cancelar no crea ni modifica `StockMovement` ni `Expense`; `purchases` sigue sin importar `inventory`/`expenses`.
- INV-10: `reception_status`/`payment_status` valen `not_received`/`unpaid` y ninguna acción de esta task los cambia.
- INV-11: toda consulta filtra por `company_id`; el estado cambia solo por métodos del agregado; dominio sin Django; dinero en `Decimal`.

## Acceptance criteria
- AC-01: `POST /api/purchases/{id}/confirm/` sobre un borrador con proveedor activo y ≥ 1 línea → 200, `status="confirmed"`, `confirmed_at` informado, `editable=false`, `allowed_actions=["cancel"]`, `reception_status="not_received"`, `payment_status="unpaid"`.
- AC-02: confirmar un borrador sin líneas → 400 `items`; con proveedor inactivo/inexistente → 400 `supplier_id`; ambos juntos si ocurren a la vez; el borrador queda como estaba.
- AC-03: `PATCH` de una confirmada (cabecera, notas o `items`) → 409 y nada cambia; precios y cantidades se conservan.
- AC-04: confirmar no crea `StockMovement` ni `Expense` ni cambia saldos; repetir `confirm` → 200 con la misma `confirmed_at`, sin otro cambio.
- AC-05: `POST /api/purchases/{id}/cancel/` con `reason` sobre un borrador → 200, `status="cancelled"`, `cancelled_at`, `cancellation_reason` (recortado), `allowed_actions=[]`, `editable=false`.
- AC-06: cancelar una confirmada sin recepciones ni pagos → 200 como AC-05.
- AC-07: `reason` ausente, vacío, solo espacios o > 500 → 400 `reason` y no se cancela.
- AC-08: si `reception_status` o `payment_status` indican actividad → cancelar responde 409 con el mensaje del ADR y no cambia nada (verificado a nivel de dominio/aplicación y API manipulando el estado en la prueba).
- AC-09: repetir `cancel` sobre una cancelada → 200 y conserva el motivo y la fecha originales; confirmar una cancelada → 409; `PATCH` de una cancelada → 409.
- AC-10: el detalle (`GET`) y las respuestas de acción incluyen `reference`, `reception_status`, `payment_status`, `confirmed_at`, `cancelled_at`, `cancellation_reason` y `allowed_actions`: borrador → `["edit","confirm","cancel"]`; confirmada → `["cancel"]` (o `[]` con actividad); cancelada → `[]`. La lista refleja el `status`.
- AC-11: compra inexistente o de otra empresa → 404 «Compra no encontrada.» en ambas acciones; sin token → 401; módulo deshabilitado → 403 `module_disabled`; `GET`/`PUT`/`DELETE` sobre las acciones → 405.
- AC-12: dos confirmaciones o cancelaciones simultáneas dan un solo cambio (bloqueo de fila + idempotencia).
- AC-13 (UI, detalle): pestaña «Resumen» con los datos de DDR (referencia interna, proveedor, fecha, referencia externa, estado documental, de recepción y de pago, ítems, total, notas; motivo y fecha solo si cancelada); badge de estado por color.
- AC-14 (UI, acciones): los botones salen de `allowed_actions`/`status`: borrador → Editar, Confirmar, Cancelar compra; confirmada → «Registrar recepción» y «Registrar pago» deshabilitados («Disponible próximamente»), Cancelar solo si el servidor lo permite, sin Editar; cancelada → solo Volver.
- AC-15 (UI, confirmar): el diálogo muestra proveedor, fecha, n.º de productos y total, y el aviso de que precios y cantidades quedarán bloqueados; «Volver» no cambia nada; al confirmar, toast, detalle actualizado y botones acordes.
- AC-16 (UI, cancelar): el diálogo exige motivo: «Cancelar compra» deshabilitado con motivo vacío/espacios, máximo 500; «Volver» no cambia nada; errores del servidor visibles; al cancelar, toast y detalle de solo lectura con motivo y fecha.
- AC-17 (UI, sin stock): ninguna pantalla de una compra confirmada muestra aumento de existencias; se aclara que confirmar no modifica el stock.
- AC-18 (UI, lista): el badge de estado y la acción «editar» de la lista respetan `confirmed`/`cancelled` (editar solo en borrador).

## Edge cases / Error cases
- EDGE-01: proveedor desactivado después del borrador → confirmar falla con `supplier_id`; cancelar sigue permitido.
- EDGE-02: producto de una línea desactivado o no comprable después → confirmar sigue permitido (H-04).
- EDGE-03: total 0.00 con líneas de precio 0 → confirmar permitido.
- EDGE-04: motivo con espacios laterales → se guarda recortado; con 500 caracteres exactos → válido.
- EDGE-05: `id` no UUID en la URL → 404 (la ruta exige `uuid`).
- EDGE-06: error de red o 409 durante la acción → toast, botones se rehabilitan y se vuelve a leer la compra.
- EDGE-07: compras creadas antes de la migración → `draft` con valores iniciales.

## Authorization / permissions
Igual que PB-COM-002: usuario autenticado con empresa y módulo `purchases` habilitado (`required_modules = ('purchases',)`); solo existe el rol administrador. La empresa sale del usuario.

## API contract
API-01 `POST /api/purchases/{id}/confirm/`; API-02 `POST /api/purchases/{id}/cancel/` `{reason}`; API-03 campos nuevos del detalle y `allowed_actions`. Aditivo y compatible hacia atrás (ver ADR).

## UI behavior
UI-01 detalle con `ngbNav` y pestaña «Resumen»; UI-02 barra de acciones por estado; UI-03 diálogo Confirmar; UI-04 diálogo Cancelar; UI-05 badges de estado en lista y detalle. Detalle en el DDR; plantilla Detalle del sistema de diseño.

## Non-functional requirements
Operaciones atómicas con bloqueo de fila; sin N+1; sin dependencias nuevas; migración aditiva.

## Out of scope
Registrar recepciones y pagos (y los movimientos de inventario/gastos que generen); numeración correlativa; reabrir, revertir o eliminar compras; edición parcial de confirmadas; auditoría de usuarios que confirman/cancelan; notificaciones; filtro por estado en la lista; E2E.

## Open questions
Ninguna bloquea. Supuestos H-01…H-07 del TASK, reversibles con aprobación: referencia interna derivada, estados de recepción/pago preparatorios, cancelar desde borrador y confirmada, no revalidar productos al confirmar, confirmada totalmente de solo lectura, idempotencia con 200, motivo ≤ 500.

# Test Specification

## Unit tests
- `purchases/tests/test_purchase_domain.py` (sin BD): INV-01, 03–08, 10; `allowed_actions` por estado; reloj inyectado; recorte y límite del motivo (EDGE-04).
- `purchases/tests/test_purchase_application.py` (repositorios falsos): `ConfirmPurchase` (proveedor inactivo, sin líneas, ambos juntos, EDGE-01/02/03, idempotencia sin guardar), `CancelPurchase` (borrador, confirmada, con actividad, idempotente).
- Frontend (Karma): `purchases-api.service.spec.ts` (confirm/cancel, mapeo de campos nuevos y errores), `purchase-detail.component.spec.ts` (botones por estado, datos de cancelada, sin edición en confirmada), `purchase-confirm-dialog` y `purchase-cancel-dialog` specs (resumen, aviso, botón deshabilitado sin motivo, límite), `purchase-list.component.spec.ts` (badges y editar solo en borrador).

## Integration tests
- `purchases/tests/test_purchase_api.py` (BD): AC-01…AC-12, incluidos aislamiento entre empresas, módulo deshabilitado, 405, conteo de `StockMovement`/`Expense` (AC-04) y `PATCH` bloqueado.
- `purchases/tests/test_purchase_repository.py` (BD): ida y vuelta de los campos nuevos y valores por defecto.
- `purchases/tests/test_migrations` o comprobación `makemigrations --check`.
- Guardas existentes: `test_boundaries`, `accounts/test_guards` (rutas con `required_modules`), `modularity/tests/test_enforcement` (rutas nuevas bloqueadas sin el módulo).

## E2E
**NO.** Se cubre con API y componentes; no hay Playwright ni flujo crítico que lo justifique. Revisión visual manual en `delivery-publish`.

## Regression tests
Suite completa de backend, `ng lint`, `ng build`, Karma de `features/purchases` y de rutas/menú; las pruebas de PB-COM-002 (crear/editar borrador) deben seguir verdes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | `test_purchase_domain`, `test_purchase_application`, `test_purchase_api` |
| AC-03 | `test_purchase_api` (PATCH 409), `test_purchase_domain` |
| AC-04 | `test_purchase_api` (conteos, repetición), `test_boundaries` |
| AC-05, AC-06, AC-07 | `test_purchase_domain`, `test_purchase_application`, `test_purchase_api` |
| AC-08 | `test_purchase_domain`, `test_purchase_application`, `test_purchase_api` (estado manipulado) |
| AC-09 | `test_purchase_application`, `test_purchase_api` |
| AC-10 | `test_purchase_api`, `test_purchase_repository`, `purchases-api.service.spec.ts` |
| AC-11 | `test_purchase_api`, `test_enforcement`, `test_guards` |
| AC-12 | `test_purchase_application` (idempotencia tras bloqueo); `select_for_update` verificado por revisión (PostgreSQL real en publish) |
| AC-13, AC-14 | `purchase-detail.component.spec.ts` |
| AC-15 | `purchase-confirm-dialog` spec y `purchase-detail.component.spec.ts` |
| AC-16 | `purchase-cancel-dialog` spec y `purchase-detail.component.spec.ts` |
| AC-17 | `purchase-detail.component.spec.ts` (sin texto de aumento de stock) |
| AC-18 | `purchase-list.component.spec.ts` |

# Implementation Plan

## Architecture considerations
Seguir `docs/architecture/ddd.md` y el ADR. Transiciones en el agregado; reglas entre agregados (proveedor activo) y la idempotencia, en la capa de aplicación; mapeo de errores en la vista (`_run`). Sin imports nuevos entre módulos.

## Proposed solution
`PurchaseStatus` crece; `Purchase` suma `confirmed_at`, `cancelled_at`, `cancellation_reason`, `reception_status`, `payment_status`, `confirm()`, `cancel()`, `has_activity`, `allowed_actions`, `reference`. Casos de uso `ConfirmPurchase` y `CancelPurchase`; vistas `PurchaseConfirmView`/`PurchaseCancelView`; serializer del detalle ampliado. En Angular, modelos y servicio ampliados, dos diálogos `NgbModal` y el detalle con pestañas y acciones.

## Files/components affected
- **Backend** (`backend/modules/purchases/`): `domain/{enums,exceptions,purchase}.py`; `application/purchase_commands.py` (+ `ConfirmPurchase`, `CancelPurchase`); `infrastructure/django/{models,mappers}.py`; `migrations/0003_purchase_lifecycle.py` (por `makemigrations`); `api/{purchase_views,purchase_serializers,purchase_urls}.py`; pruebas listadas.
- **Backend sin cambios de contrato**: `services.py`; `config/urls.py` (ya monta `api/purchases/`).
- **Frontend** (`features/purchases/`): `models/purchase.ts` (estados, campos, `allowedActions`), `services/purchases-api.service.ts` (+ `confirm`, `cancel`, mapeo), `components/purchase-confirm-dialog/*`, `components/purchase-cancel-dialog/*`, `pages/purchase-detail/*`, `pages/purchase-list/*`, `testing/purchase-fixtures.ts` y specs.
- **Docs**: `docs/design/design-system.md` (nota en «Detalle»), `docs/producto/modulos-implementados.md`, `docs/architecture/ddd.md` (ciclo de vida de Compras).

## Implementation steps
1. **Dominio**: estados, excepciones (`PurchaseInvalidTransition`, `PurchaseCancellationBlocked`), `confirm`, `cancel`, `allowed_actions`, `reference`, estados preparatorios + pruebas (INV-01, 03–08, 10).
2. **Infraestructura**: campos del modelo, `makemigrations` → `0003`, mapper de ida y vuelta + prueba de repositorio (INV-08, EDGE-07).
3. **Aplicación**: `ConfirmPurchase`/`CancelPurchase` (bloqueo, errores juntos, idempotencia) + pruebas (AC-01, 02, 04–09, 12).
4. **API**: serializers (campos nuevos, `reason`), vistas, URLs (AC-01…AC-11) y actualizar guardas.
5. **Frontend base**: modelos, servicio, fixtures y pruebas (AC-10).
6. **Diálogos** de confirmar y cancelar con pruebas (AC-15, AC-16).
7. **Detalle** con pestañas y acciones, y ajustes de la lista (AC-13, 14, 17, 18).
8. **Documentación** y verificación local: `manage.py test`, `makemigrations --check`, `ng lint`, `ng build`, Karma del feature.

## Database / migrations
`purchases/migrations/0003_purchase_lifecycle.py` generada con `makemigrations`: cinco columnas aditivas con valores por defecto/nulos. No se edita `0001`/`0002`. Rollback: `migrate purchases 0002`.

## Risks
- Estados de recepción/pago preparatorios (H-02): las tasks futuras deben respetarlos; mitigado por el ADR y la regla de cancelación ya probada.
- Referencia interna derivada (H-01) no es correlativa.
- Concurrencia: cubierta por `select_for_update` e idempotencia; se valida con PostgreSQL real en publish.
- Badges y acciones que asuman un solo estado en la lista (AC-18).

## New dependencies
Ninguna.
