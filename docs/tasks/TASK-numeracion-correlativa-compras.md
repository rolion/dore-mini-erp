# TASK-numeracion-correlativa-compras: Numeración correlativa de compras por período fiscal

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-numeracion-correlativa-compras
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/125

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → DESIGN | NEEDS_ARCHITECTURE, diseño requerido | delivery-start |
| 2026-11-26 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-11-26 | ARCHITECTURE → PLANNING | ADR escrito | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | PLAN v1 READY | delivery-start |

## Investigación

### Requerimiento
Gemela de la numeración de ventas ya mergeada (TASK-numeracion-correlativa-pedidos-venta, PR #124): las compras solo tienen UUID y una etiqueta provisional `COM-XXXXXXXX`. Se pide una serie correlativa **separada** `NC-000001`, con las **mismas reglas** que el usuario ya decidió para ventas:

- Se asigna al **confirmar** (`draft → confirmed`); las compras canceladas que llegaron a confirmarse conservan su número; nunca se reutiliza.
- Reinicio por **período fiscal** de contabilidad (rango de fechas), según `purchase_date`. Primera confirmada del período = 000001.
- Sin período fiscal para la fecha, o período **cerrado**: bloquear la confirmación (409 `fiscal_period_missing` / `fiscal_period_closed`), también en cualquier otro camino que confirme compras.
- El número se repite entre períodos: la UI muestra el período junto al código.
- UUID sigue siendo la clave primaria. Inventario y Contabilidad siguen mostrando UUIDs en «Origen»/documento de origen (decisión del usuario, fuera de alcance).
- **Obligatorio:** pruebas de carrera sobre PostgreSQL (con comprobación por mutación).
- Migración de datos para compras existentes: como `PurchaseModel` tiene `confirmed_at`, una compra cancelada que llegó a confirmarse conserva número; se numera por empresa y período en orden `confirmed_at, created_at`; los borradores, las canceladas sin confirmar y las de fecha fuera de período quedan sin número; repetible.
- Reemplazar `COM-XXXXXXXX` en backend y frontend (lista, detalle, diálogos, i18n es/en/pt) y revisar los textos contables.
- Decidir (técnicamente, con justificación en el ADR) si extraer ya un contador compartido.

### Hechos encontrados
- `backend/modules/purchases/domain/purchase.py:325-327` — `Purchase.reference` devuelve `COM-` + 8 hex del id; docstring: «la numeración correlativa es otra task». `purchase.py:361-373` — `confirm(now, supplier_active)`: `draft → confirmed`, exige proveedor activo y ≥1 ítem, fija `confirmed_at`. `purchase.py:494-497` — `update` exige `ensure_editable` (solo borrador), así que `purchase_date` no cambia tras confirmar.
- `backend/modules/purchases/infrastructure/django/models.py:25-52` — `PurchaseModel`: `confirmed_at`, `cancelled_at`, `status` (draft/confirmed/cancelled); sin campo de número. `cancel` no limpia `confirmed_at` (`purchase.py:375-388`), por lo que se puede saber si una cancelada se confirmó antes.
- `backend/modules/purchases/application/purchase_commands.py:121-135` — `ConfirmPurchase`: carga con bloqueo (`_load_locked`), **idempotente** sobre una compra ya confirmada (devuelve sin cambios) y llama a `purchase.confirm`.
- Caminos que confirman: la API (`api/purchase_views.py:201`) y la importación de ventas (`purchases/services.py:82,110` — `import_received_purchase`, que crea, confirma y recibe la «compra inferida»).
- Referencia derivada del id en tres sitios del backend: `domain/purchase.py:327`, `infrastructure/django/purchase_repository.py:44` (resumen de lista) y `purchase_repository.py:128-136` (la búsqueda de la lista acepta `com-` + prefijo hex del id). El API la devuelve como `reference` (`api/purchase_serializers.py:68,104`).
- Descripciones de asientos con la referencia: `infrastructure/adapters.py:177` (reconocimiento en la recepción), `:191` (pago/anticipo) y `:226` (recepción revertida).
- Errores del API: `api/purchase_views.py:110-138` traduce excepciones de dominio; 409 por `Conflict`; `PostingRejected` ya lleva `{code, detail, **extra}` (`:116-117`).
- Frontend: `features/purchases` muestra `reference` en lista (`purchase-list.component.html:138-141,205`), detalle (`purchase-detail.component.html:20,65`), recepción (`reception-detail.component.html:45`, `reception-form.component.html:13,34,152`) y modelos (`models/purchase.ts:85,111`); errores 409 de acciones se muestran como toast con el `detail` (`purchases-api.service.ts:165-172`, `purchase-detail.component.ts:105-133`). Fixtures con `COM-1A2B3C4D` (`testing/purchase-fixtures.ts:28,55`).
- Patrón ya implementado en ventas (mergeado): `OrderNumber` (dominio), puerto `OrderNumbering` (`sales/application/ports.py`), `OrderNumberingAdapter` (`sales/infrastructure/adapters.py`: `accounting.services.lock_open_period` + `OrderNumberCounterModel.select_for_update`), migraciones `sales/0006..0008`, `app-fiscal-period-alert` (`features/sales/components/fiscal-period-alert`), fixture `sales/tests/periods.py::open_test_period` y pruebas de carrera `sales/tests/test_order_numbering_concurrency.py`.
- Último migration de purchases: `0009_payment_advances.py`. Último de accounting con períodos: `0009_fiscal_period`.
- Pruebas que confirman compras sin período: `purchases/tests/*` (≥20 archivos que usan confirm), más pruebas de otros módulos que importan o confirman compras.

### Hipótesis / supuestos no confirmados
- Que la «compra inferida» de la importación de ventas comparte fecha con la venta, así que falla por período junto con la venta (a verificar al implementar).
- Que ninguna otra pantalla fuera de `features/purchases` muestre la referencia provisional de compras.

### Módulos y dependencias relacionadas
`purchases` (dominio, aplicación, infraestructura, API, migraciones, tests), `accounting` (solo su fachada pública), `data_import` (llama a `import_received_purchase`), frontend `features/purchases` y `shared/components`.

### Implementaciones similares existentes
Numeración de ventas (arriba) y los contadores por empresa de `quotations`/`receivables`.

### Comportamiento actual
Confirmar no consulta Contabilidad ni exige período; toda compra se muestra como `COM-XXXXXXXX`.

### Restricciones
Dominio sin Django; sin importar infraestructura de otros módulos (solo `modules.accounting.services`); no editar migraciones aplicadas; aislamiento por `company_id`; i18n es/en/pt; PostgreSQL; sin dependencias nuevas.

### Riesgos identificados
- Bloquear confirmaciones sin período afecta a empresas sin Contabilidad/sin períodos y a importaciones con fechas fuera de período (misma decisión que ventas).
- Mover `app-fiscal-period-alert` a `shared/` toca archivos de ventas ya mergeadas (imports y specs).
- Muchas pruebas heredadas de compras confirman sin período.
- La búsqueda de la lista por prefijo de id debe seguir funcionando para borradores y heredados sin número.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — migración de datos sobre compras existentes, nueva dependencia de `purchases` con la fachada de `accounting`, concurrencia y cambio de contrato API.

### Diseño requerido
**SI** — cambia la identificación visible de las compras en lista, detalle y recepciones, y aparece un estado de bloqueo nuevo al confirmar.

## Diseño
Ver `docs/design/DDR-numeracion-correlativa-compras-codigo-y-bloqueo.md`.

## Arquitectura
Ver `docs/adr/ADR-numeracion-correlativa-compras-contador-por-periodo.md`.

## Plan
`docs/plans/PLAN-2026-11-26-numeracion-correlativa-compras.md` (v1, COMPLETO, Specification READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
