# TASK-numeracion-correlativa-compras: Numeración correlativa de compras por período fiscal

**Etapa actual:** REVIEW
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
| 2026-11-26 | ENGINEERING → REVIEW | Implementación y pruebas escritas; suite backend (2492) y Karma (644 de los módulos tocados) en verde por verificación propia | delivery-build |

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

**Resumen.** La compra recibe `(período fiscal, número)` al confirmarse (`draft → confirmed`), dentro de la transacción de la confirmación. `reference` pasa a `NC-000001`; borradores y heredadas sin número conservan la etiqueta provisional `COM-XXXXXXXX`. El API añade `number` y `fiscal_period {id, name}`.

**Backend (qué cubre cada parte)**
- Dominio `purchases/domain/purchase.py`: `PurchaseNumber`, `Purchase.number`, `ensure_confirmable()`, `confirm(now, number, ...)`, `provisional_reference()` (INV-01..06, AC-03). `PurchaseSummary` lleva `number`.
- Puerto `PurchaseNumbering` (`application/ports.py`) usado por `ConfirmPurchase`; `ensure_confirmable()` corre antes de numerar (AC-02) y la confirmación repetida sigue idempotente sin numerar (EDGE-01). `PurchaseNumberingRejected` (subclase de `PostingRejected`) para `fiscal_period_missing`/`fiscal_period_closed`: la API (409 `{code, detail, period?}`) y la importación (`ImportRejected(code)`) ya la traducen sin cambios (AC-05, AC-06, AC-10).
- Adaptador `PurchaseNumberingAdapter` (`infrastructure/adapters.py`): `accounting.services.lock_open_period` + contador con `select_for_update` (AC-01, AC-04, AC-07..AC-09). Descripciones de asientos de recepción, pago/anticipo y reversión con el período (AC-11).
- Modelos y migraciones: `0010` (columnas nulas, `PurchaseNumberCounterModel` con `company_id` indexado, restricción única parcial y dos CHECK) y `0011` (numera las compras con `confirmed_at`, incluidas las canceladas que se confirmaron, en orden `confirmed_at, created_at, id`; repetible; AC-12).
- Repositorio: `reference`/`number` en el resumen y búsqueda por `NC-000012`, por número y por prefijo de id (`com-…`) (AC-11). API: `reference`, `number`, `fiscal_period` en lista y detalle (API-01..03). `import_received_purchase` numera con el mismo adaptador (AC-10).

**Frontend.** `fiscalPeriod` en modelos y mapeo; lista (tabla y tarjetas) y detalle (fila «Período fiscal») muestran el período solo con número (UI-01, UI-02); `PurchaseApiError` con `code` y `periodName`; el detalle muestra `app-fiscal-period-alert` en lugar del toast para los dos códigos (UI-03). **`app-fiscal-period-alert` se movió de `features/sales/components` a `shared/components`** (segundo módulo que lo usa) y sus claves pasaron de `SALES.FISCAL_PERIOD.*` a `COMMON.FISCAL_PERIOD.*` (es/en/pt); cambian solo imports en ventas. Claves nuevas `PURCHASES.PURCHASE_DETAIL.PERIODO_FISCAL` y `PURCHASES.PURCHASE_LIST.PERIODO`. Pantallas de referencia: Lista con seguimiento de estados (`purchase-list`) y Detalle con acciones de ciclo de vida (`purchase-detail`); sin patrones nuevos.

**Pruebas añadidas.** `test_purchase_number_domain` (dominio y casos de uso con fakes), `test_purchase_numbering` (serie por período/empresa e independiente de ventas, `purchase_date`, borradores, canceladas, snapshot, bloqueos, rollback, restricciones de BD, API y búsqueda, compra inferida de la importación), `test_purchase_numbering_concurrency` (8 confirmaciones simultáneas → `{1..8}`; dos períodos y dos empresas; la misma compra dos veces; confirmar vs. cerrar con sincronización determinista; confirmar tras cierre firme), `test_purchase_number_migration` (0011 e idempotencia). Karma: componente movido, detalle, lista y servicio. **Mutación comprobada:** sustituyendo `lock_open_period` por `period_for` y quitando `select_for_update`, 5 de 6 pruebas de carrera fallan; con ellos pasan.

**Pruebas heredadas ajustadas.** `numbering_support.py` (`fake_number`, `FakeNumbering`); `PurchaseApiTestCase` crea un período abierto amplio (`open_test_period`, reutilizado de `sales/tests/periods.py`); `PaymentBooks` y `PurchasePostingBase` reemplazan ese período por el suyo; claves nuevas en los conjuntos de campos del API; las aserciones de la referencia de una compra confirmada pasan de `COM-…` a `NC-…`.

**Desviaciones respecto al plan.**
- `PurchaseNumberingRejected` hereda de `PostingRejected` (detalle de implementación): evita tocar el traductor 409 de las vistas y el de la importación, que ya cubren `PostingRejected`.
- Las claves del componente compartido se movieron a `COMMON.FISCAL_PERIOD.*` (el plan solo anticipaba mover el componente).
- Para ejecutar las pruebas se usa el `backend/.env` copiado en el worktree (con autorización previa del usuario) y el `node_modules` enlazado; ambos están en `.gitignore`.

**Deuda técnica / notas.** Contador no extraído a `shared/` (ADR decisión 8): quedan dos implementaciones con la misma forma. Compras heredadas con fecha fuera de todo período siguen con la etiqueta provisional. Sin período/Contabilidad no se puede confirmar (misma decisión que ventas). Avisos de lint previos sin tocar; cero avisos nuevos en líneas cambiadas (`flake8`; `ruff` solo avisa líneas previas).

**Verificación propia (no es el Quality Gate).** `ng lint` y `i18n:check` sin hallazgos; `ng build` compila; Karma de `purchases`, `sales`, `shared` y `core/i18n`: 644 pruebas OK; backend: suite completa (`python manage.py test`, PostgreSQL) 2492 pruebas OK, y `modules.purchases` repetido tras el último ajuste de formato de líneas: OK.

## Review
_Pendiente_

## Publicación
_Pendiente_
