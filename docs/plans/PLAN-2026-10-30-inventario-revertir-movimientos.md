# PLAN-2026-10-30-inventario-revertir-movimientos (v2)

**Task:** TASK-inventario-revertir-movimientos · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR-inventario-revertir-movimientos-dialogo-reversion](../design/DDR-inventario-revertir-movimientos-dialogo-reversion.md) · [ADR-inventario-revertir-movimientos-contramovimientos](../adr/ADR-inventario-revertir-movimientos-contramovimientos.md)

## Objective
Permitir a un administrador corregir un movimiento de inventario confirmado con un contramovimiento vinculado y con motivo (movimientos/ajustes manuales desde Inventario; recepciones de compra desde Compras), conservando el historial y sin reversión doble.

## Context
Resumen en `docs/tasks/TASK-inventario-revertir-movimientos.md`. El dominio ya sabe revertir un movimiento, pero no hay API, UI ni reversión de recepciones.

# Specification

## Domain context
Bounded Context principal: **Inventario** (libro de movimientos, ajustes). Relacionado: **Compras** (recepciones; integra con Inventario solo por `inventory/services.py`). **Ventas** solo como origen rechazado.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Movimiento | Entrada/salida inmutable del libro; solo cambia `confirmed → reversed` | `inventory/domain/movement.py:81` |
| Contramovimiento | Movimiento opuesto creado por una reversión, vinculado por `reverses_id` | `movement.py:114` |
| Origen manual | Movimiento sin origen, `inventory_adjustment` o `inventory_opening` | decisión ADR |
| Recepción revertida | `Receipt.status = reverted`; sus cantidades dejan de contar como recibidas | `purchases/domain/enums.py:29` |
| Reversión | Acción con motivo que genera el contramovimiento (o los de una recepción) | tarjeta |

Inconsistencia declarada: el estado de la recepción se llama `reverted` y el del movimiento `reversed`; se conservan ambos nombres (ya existen en modelos/UI) y la UI muestra «Revertida»/«Revertido».

## Current behavior
`StockMovement.reverse` / `ReverseMovement` / `inventory/services.py:71 reverse_movement` existen sin consumidores (solo `inventory/tests/test_movements.py:173-192`). `API movimientos` es solo lectura (`movement_views.py:96`). Ninguna transición lleva una recepción a `reverted`.

## Expected behavior
- Inventario permite revertir un movimiento manual con motivo; el original queda `reversed`, se crea un contramovimiento opuesto vinculado y el saldo vuelve.
- Compras permite revertir una recepción completa: se revierten todas sus entradas de stock (si las hubo), la recepción queda `reverted`, la compra recalcula lo recibido/pendiente y su estado de recepción, y los pagos no cambian.
- Ninguna reversión puede ejecutarse dos veces; ninguna deja efectos parciales.

## Domain rules / invariants
- **INV-01** (existente, INV-07 de la task de movimientos) Un movimiento se revierte una sola vez; un contramovimiento no se revierte.
- **INV-02** (nueva) El motivo de una reversión es obligatorio (no vacío tras recortar, ≤200 caracteres).
- **INV-03** (nueva) Un movimiento con origen `sales_order` o `purchase_receipt` no se revierte por la API de movimientos; se corrige desde su documento (ventas: devolución fuera de alcance).
- **INV-04** (existente) Un contramovimiento de salida respeta la política de stock negativo de la empresa, revalidada bajo el bloqueo del almacén.
- **INV-05** (nueva) La reversión de una recepción es **todo-o-nada**: la política de stock se evalúa sobre el conjunto de contramovimientos (sumados por producto y almacén) y, si alguno falla, no se revierte ninguna línea ni cambia la recepción.
- **INV-06** (nueva) Revertir una recepción solo la pasa `confirmed → reverted` por `Receipt.revert`; recalcula `reception_status` con las recepciones `confirmed` restantes y **no toca pagos**.
- **INV-07** (nueva) Revertir una recepción documental no genera movimientos; una de modo `inventory` exige Inventario habilitado.

## Acceptance criteria
- **AC-01** `POST /api/stock-movements/<id>/reverse/` sin motivo, en blanco o de más de 200 caracteres → 400 con error en `reason`; no cambia nada.
- **AC-02** Con motivo válido sobre un movimiento manual confirmado → 200; el original queda `reversed`; existe un contramovimiento de tipo opuesto, misma cantidad/producto/almacén, `reverses_id` al original, motivo, usuario y fecha; el saldo se restituye; el original sigue consultable.
- **AC-03** Una segunda reversión del mismo movimiento → 409 `already_reversed`; revertir un contramovimiento → 409 `cannot_reverse_reversal`; dos reversiones simultáneas producen exactamente un contramovimiento.
- **AC-04** Un movimiento de origen `sales_order` → 409 `requires_return`; de origen `purchase_receipt` → 409 `reverse_from_origin`; no cambia nada.
- **AC-05** Revertir una entrada cuyo contramovimiento (salida) dejaría stock negativo con la política en «bloquear» → 409 `insufficient_stock` con producto, almacén y saldo; no cambia nada. Con la política en «permitir», procede.
- **AC-06** `POST /api/purchases/<pid>/receipts/<rid>/revert/` con motivo sobre una recepción confirmada con entradas de stock → 200; se crean contramovimientos para todas sus entradas, los originales quedan `reversed`, la recepción pasa a `reverted` con fecha, usuario y motivo; la compra recalcula `reception_status` y vuelve a admitir recepción por lo pendiente.
- **AC-07** Si cualquier línea de la recepción no puede revertirse por stock (política bloqueante) → 409 `insufficient_stock` con **todas** las líneas faltantes (producto, solicitado, saldo); ninguna línea se revierte y la recepción sigue `confirmed`.
- **AC-08** Revertir una recepción no modifica pagos, `payment_status` ni saldo de la compra.
- **AC-09** Revertir una recepción ya revertida → 409 `already_reverted`; motivo ausente/inválido → 400 `reason`.
- **AC-10** Una recepción documental se revierte sin movimientos de inventario; una recepción en modo `inventory` con Inventario deshabilitado → 409 `inventory_unavailable`.
- **AC-11** El detalle del movimiento original devuelve estado `reversed`, `reversed_by` con id, referencia, fecha, usuario y motivo del contramovimiento; el contramovimiento devuelve `reverses`. El detalle de recepción devuelve `reversal` (fecha, usuario, motivo), `can_revert` y, por movimiento, estado y vínculo al contramovimiento.
- **AC-12** El detalle de movimiento expone `reversal` `{allowed, code, message}` coherente con AC-02..04 (`allowed=false` con mensaje en venta, compra, ya revertido y contramovimiento).
- **AC-13** Ids de otra empresa (movimiento, compra, recepción) → 404; sin rol admin o sin el módulo requerido → 403 (comportamiento por defecto).
- **AC-14** Con Inventario o Compras (según el endpoint) deshabilitados, el endpoint respeta el bloqueo de módulo ya existente.
- **AC-15** UI de movimiento y ajuste: «Revertir» aparece solo si `reversal.allowed`; el diálogo muestra referencia/tipo, producto, almacén, cantidad, efecto inverso y exige motivo; en venta/compra se explica la restricción; no se ofrece una segunda reversión; tras revertir se ven estado «Revertido», contramovimiento enlazado, usuario, fecha y motivo.
- **AC-16** UI de recepción: «Revertir recepción» aparece solo si `can_revert`; el diálogo lista todas las líneas, el impacto y avisa que no devuelve pagos; el 409 de stock muestra productos y saldos sin revertir nada; tras revertir se recarga mostrando la reversión y el estado «Revertida».

## Edge cases / Error cases
- **EDGE-01** Recepción con líneas sin control de stock: solo se revierten las entradas existentes; las demás líneas igual dejan de contar como recibidas.
- **EDGE-02** Recepción con modo desconocido (anterior al modo guardado): se trata como `inventory` si tiene `warehouse_id`; si no, como documental.
- **EDGE-03** El almacén de la recepción fue desactivado: la reversión procede (corrige el libro; no es una operación comercial nueva).
- **EDGE-04** Reversión de un ajuste: su estado pasa a `reversed` sin cambios de esquema (el estado sale del movimiento).
- **EDGE-05** Reversión de una apertura de existencias: permitida (decisión ADR); el producto conserva el historial.
- **EDGE-06** Compra con recepciones parciales: revertir una no afecta a las otras; el estado pasa de `received` a `partial` o `not_received` según corresponda.

## Authorization / permissions
Sin permisos nuevos: usuario admin de empresa activa (permiso por defecto). `company_id` del usuario autenticado en repositorios y fachadas; módulos requeridos `inventory` (movimientos) y `purchases` (recepciones).

## API contract
- **API-01** `POST /api/stock-movements/<id>/reverse/` `{reason}` → 200 detalle del contramovimiento; 400/404/409 (códigos en AC).
- **API-02** `GET /api/stock-movements/<id>/` amplía el detalle: `reversal` y `reversed_by` expandido (retrocompatible: conserva `id`).
- **API-03** `POST /api/purchases/<pid>/receipts/<rid>/revert/` `{reason}` → 200 detalle de recepción; 400/404/409.
- **API-04** `GET .../receipts/<rid>/` amplía: `reversal`, `can_revert`, por movimiento `status` y `reversed_by`.
- 409 `insufficient_stock` usa el contrato existente (`product`, `warehouse`, `requested`, `available`, `lines`).
- Compatibilidad: solo se añaden campos y endpoints.

## UI behavior
- **UI-01** Detalle de movimiento: botón «Revertir» (`btn-warning`), mensaje de restricción (`small.text-muted`), bloque «Reversión» tras revertir (plantilla Detalle, DDR).
- **UI-02** Detalle de ajuste: «Revertir» abre el mismo diálogo con `movement.id`.
- **UI-03** `MovementReverseDialogComponent` (patrón diálogo con motivo de `purchase-cancel-dialog`).
- **UI-04** Detalle de recepción: «Revertir recepción» y `ReceiptRevertDialogComponent` con tabla de líneas, aviso de pagos y 409 de stock.
- **UI-05** Estados cargando/error/éxito en los diálogos (sección 4 del sistema de diseño); el frontend solo oculta botones.

## Non-functional requirements
Cantidades en `Decimal` (4 decimales en el libro). Operación atómica por petición. Consultas acotadas por `company_id`; sin N+1 en el detalle de recepción con movimientos.

## Out of scope
Devoluciones de clientes y reversión de salidas de venta; devolución de pagos; reversión parcial de recepciones; revertir pagos de compras; enlace desde un movimiento de compra a su recepción; permisos por usuario; reversión masiva.

## Open questions
Ninguna que bloquee. Decisiones tomadas y registradas en el ADR: apertura revertible, recepción documental revertible, `inventory_unavailable` cuando Inventario está deshabilitado.

# Test Specification

## Unit tests
- Dominio Inventario: `reverse` exige motivo (INV-02), mantiene INV-01; `ReverseSourceMovements` (todo-o-nada, suma por producto, idempotente sin pendientes).
- Dominio Compras: `Receipt.revert` (transición, doble reversión, datos de reversión); `Purchase.recompute_reception` (received→partial→not_received, restitución de pendiente); no cambia `payment_status`.

## Integration tests
- Aplicación Inventario: `ReverseMovement` con orígenes permitidos/rechazados y política de stock; `ReverseSourceMovements` contra repositorio real.
- Aplicación Compras: `RevertReception` con fakes de puertos (inventory, documental, módulo deshabilitado, faltante de stock, doble reversión).
- API Inventario y Compras con PostgreSQL de tests: AC-01..AC-14, `404` entre empresas, 403 sin rol, módulo deshabilitado.
- Persistencia: migración `purchases/0007` (campos nuevos, filas existentes intactas) y `test_migrations` si aplica.
- Concurrencia: dos reversiones simultáneas del mismo movimiento y de la misma recepción (un ganador, un 409), como `test_receipt_concurrency.py`.
- Frontend (Karma): servicios API (`movements-api`, `receipts-api`) con mapeo snake→camel de `reversal`/`reversed_by`; diálogos (motivo obligatorio, cierre con motivo recortado, errores 400/409); páginas de detalle (botón según `reversal.allowed`/`can_revert`, mensajes de restricción, bloque «Reversión», recarga tras éxito).

## E2E
**NO** — los flujos están cubiertos por pruebas de API con base real y de componentes; no es un flujo crítico de punta a punta que justifique instalar Playwright. La verificación visual la hace `delivery-publish`.

## Regression tests
Actualizar `inventory/tests/test_movements.py` (motivo obligatorio), `test_adjustments.py`/`test_stock_query.py` si usan `reverse_movement` sin motivo; suites de recepciones (`purchases/tests/test_receipt_*`) para confirmar que `received_totals` y `can_receive` siguen igual; `purchases/tests/test_payment_*` sin cambios.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API test inventario (400 reason) + unit dominio |
| AC-02 | API test + application test (`ReverseMovement`) |
| AC-03 | API test (409×2) + test de concurrencia |
| AC-04 | API test (venta, compra) |
| AC-05 | API test con política «bloquear» y «permitir» |
| AC-06 | Application test `RevertReception` + API test de recepción (estado de la compra) |
| AC-07 | Application + API test (409 con varias líneas, nada revertido) + test del caso de uso Inventario |
| AC-08 | API test: pagos y `payment_status` idénticos antes/después |
| AC-09 | API test (409 `already_reverted`, 400 reason) + unit dominio |
| AC-10 | Application test (documental / módulo deshabilitado) |
| AC-11 | API test de ambos detalles + spec de servicios frontend |
| AC-12 | API test de `reversal` por cada origen/estado |
| AC-13 | API test multiempresa y sin rol/módulo |
| AC-14 | API test con módulo deshabilitado |
| AC-15 | Specs Karma de movimiento, ajuste y `MovementReverseDialog` |
| AC-16 | Specs Karma de recepción y `ReceiptRevertDialog` |

# Implementation Plan

## Architecture considerations
Ver ADR. Inventario: la política de orígenes es del caso de uso, el agregado queda genérico. Compras: `RevertReception` espeja `RegisterReception` (compra bloqueada → almacén bloqueado). Sin imports de infraestructura entre módulos: Compras llama solo a `inventory/services.py` desde `StockEntryAdapter`.

## Proposed solution
1. Inventario: motivo obligatorio en `reverse`; `ReverseMovement` con orígenes permitidos; `ReverseSourceMovements`; endpoint y presentador; fachada.
2. Compras: migración 0007, `Receipt.revert`, `Purchase.recompute_reception`, puerto/adaptador `reverse_entries`, `RevertReception`, endpoint y serializadores.
3. Frontend: modelos, servicios, dos diálogos, cambios en tres detalles.
4. Docs: sección 5 del sistema de diseño (diálogo de acción irreversible con motivo) y documentación de API si existe.

## Files/components affected
- **Backend Inventario:** `domain/movement.py`, `domain/exceptions.py` (códigos), `application/movement_use_cases.py`, `services.py`, `infrastructure/django/movement_repository.py` (movimientos pendientes de un origen, contrapartidas), `api/movement_views.py`, `api/movement_urls.py`; tests en `inventory/tests/`.
- **Backend Compras:** `domain/receipt.py`, `domain/purchase.py`, `domain/exceptions.py`, `application/ports.py`, `application/receipt_commands.py`, `application/receipt_queries.py`, `infrastructure/adapters.py`, `infrastructure/django/{models,mappers,receipt_repository}.py`, migración `0007_receipt_reversal.py`, `api/receipt_views.py`, `api/receipt_serializers.py`, `api/purchase_urls.py`; tests en `purchases/tests/`.
- **Frontend:** `inventory/models/movement.ts`, `inventory/services/movements-api.service.ts`, `inventory/components/movement-reverse-dialog/`, páginas `movement-detail` y `adjustment-detail`, `purchases/models/receipt.ts`, `purchases/services/receipts-api.service.ts`, `purchases/components/receipt-revert-dialog/`, `pages/reception-detail`, fixtures de pruebas.
- **Docs:** `docs/design/design-system.md`, esta task.

## Implementation steps
1. (INV-02) `StockMovement.reverse` exige motivo; actualizar tests existentes. Añadir códigos `requires_return`, `reverse_from_origin`.
2. (AC-02..05, INV-03) `ReverseMovement` con `allowed_sources`; endpoint `reverse/` con serializer de motivo; presentador con `reversal` y `reversed_by` expandido (AC-11, AC-12); tests de API y concurrencia.
3. (INV-05, AC-07) Repositorio: movimientos confirmados de un origen; `ReverseSourceMovements`; `reverse_source_movements` y `SourceMovement.status/reversed_by_id` en la fachada.
4. (INV-06, AC-06, AC-08) Migración 0007 + modelo/mapper; `Receipt.revert`, `Purchase.recompute_reception`; tests de dominio.
5. (AC-06, AC-07, AC-09, AC-10, INV-07) Puerto `StockEntry.reverse_entries`, adaptador (traducción de `InsufficientStock`/conflictos), `RevertReception`; tests de aplicación.
6. (AC-06..AC-14) Endpoint `revert/`, serializadores de detalle con `reversal`/`can_revert`/estado de movimientos; tests de API.
7. (AC-15, UI-01..03) Modelos/servicio, `MovementReverseDialogComponent`, páginas de movimiento y ajuste; specs.
8. (AC-16, UI-04..05) Modelos/servicio, `ReceiptRevertDialogComponent`, página de recepción; specs.
9. Actualizar `docs/design/design-system.md` y la Implementación del TASK. Ejecutar `python manage.py test`, `npm test`, `npm run lint`, `npm run build`.

## Database / migrations
Nueva `purchases/0007_receipt_reversal` (aditiva, nullable/blank; no edita migraciones aplicadas). Inventario no cambia el esquema (el estado del ajuste y la unicidad de reversión ya existen). Verificación posterior: todo movimiento `purchase_receipt` `reversed` tiene su recepción `reverted` y viceversa.

## Risks
- Orden de bloqueos (compra → almacén) para evitar interbloqueos con una recepción simultánea; cubierto por test de concurrencia.
- Cambiar el motivo a obligatorio rompe llamadas existentes de `reverse_movement` (solo tests).
- Recepciones antiguas sin modo: EDGE-02 acota el comportamiento.
- Si el mapa `Receipt` ↔ movimientos usa `source_line=product_id`, dos líneas de la misma compra con el mismo producto colisionan al recibir (limitación preexistente); no se corrige aquí.

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-10-30): [Implementation Plan] Corrige las rutas citadas a `/api/stock-movements/...` (las reales del proyecto; sin cambio de comportamiento ni de AC) y registra que el enlace del bloque «Reversión» se rotula «Contramovimiento · <referencia>». Solicitado por delivery-publish, REV-01 y REV-03.
