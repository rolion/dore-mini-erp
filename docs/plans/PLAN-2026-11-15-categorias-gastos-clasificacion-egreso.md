# PLAN-2026-11-15-categorias-gastos-clasificacion-egreso (v1)

**Task:** TASK-categorias-gastos-clasificacion-egreso · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-categorias-gastos-clasificacion-egreso-pestana-egresos · ADR-categorias-gastos-clasificacion-egreso-propiedad-y-snapshot

## Objective
Asociar cada categoría de Gastos y los pagos a proveedores con una clasificación de egreso de Contabilidad, aplicarla (como instantánea) a los gastos y pagos nuevos, y exigir la configuración antes de confirmar cuando Contabilidad cubre la operación.

## Context
Base `origin/accounting` (CONT-01 y CONT-06). Detalle en el TASK. Los movimientos de egreso llegan con CONT-02/GAS-01/COM-01, que consumirán la instantánea.

# Specification

## Domain context
Contexto propietario: Contabilidad (clasificaciones, cobertura). Relacionados: Gastos (categorías, gastos) y Compras (pagos), ambos por `accounting.services`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Clasificación de egreso | `Classification` con `direction = EXPENSE`: por qué sale el dinero | `accounting/domain/classification.py` |
| Asociación | Vínculo categoría de Gastos → clasificación (o ajuste de pagos a proveedores) | esta tarea |
| Instantánea | `classification_id` guardado en el gasto/pago al crearlo | ADR |
| Cobertura | `coverage_status(...).covered` | ADR CONT-06 |

## Current behavior
Ver TASK («Hechos encontrados»): ni gastos ni pagos de compra guardan clasificación; no hay asociación.

## Expected behavior
- La persona admin asocia una clasificación de egreso activa de su empresa a cada categoría y a «Pagos a proveedores»; puede quitarla.
- Registrar un gasto guarda la clasificación de su categoría; registrar un pago de compra guarda la de proveedores. Cambiar la asociación no altera lo ya registrado.
- Con cobertura y sin asociación válida, el registro se rechaza con un mensaje que indica dónde corregirlo. Sin cobertura se guarda sin error.
- El detalle del gasto y del pago muestran la clasificación aplicada.

## Domain rules / invariants
- **INV-01 (nueva):** una asociación apunta a una clasificación `EXPENSE`, activa y de la misma empresa al momento de asociar.
- **INV-02 (nueva):** la instantánea de un gasto/pago no cambia aunque cambie la asociación, la clasificación se renombre o se desactive.
- **INV-03 (existente):** categorías inactivas no se ofrecen en gastos nuevos; los gastos históricos las conservan (`commands.py:12-21`).
- **INV-04 (nueva):** un pago de compra no crea gasto ni convierte «Pagos a proveedores» en categoría de Gastos.
- **INV-05 (existente):** acceso por empresa del usuario autenticado; solo admin.

## Acceptance criteria
- **AC-01** (tarjeta 1): asociar «Alquiler» a una clasificación de egreso; un gasto nuevo en «Alquiler» queda con esa clasificación.
- **AC-02** (tarjeta 2): rechazar (400 `classification_id`) clasificación de ingreso, inactiva, inexistente o de otra empresa, tanto para categorías como para pagos a proveedores.
- **AC-03** (tarjeta 3): cambiar o quitar la asociación no modifica `classification_id` de gastos ni pagos ya registrados.
- **AC-04** (tarjeta 4): registrar el pago de una compra guarda la clasificación configurada para proveedores y no crea ningún gasto.
- **AC-05** (tarjeta 5): un usuario no admin (o sin empresa) recibe 403 al modificar o leer asociaciones.
- **AC-06:** con cobertura y categoría sin asociación (o clasificación asociada inactiva), crear/editar a esa categoría un gasto responde 400 con `classification_not_configured`/`classification_invalid` y no persiste; sin cobertura (Contabilidad deshabilitada, antes del corte) se guarda y la instantánea queda vacía si no hay asociación válida.
- **AC-07:** con cobertura y sin clasificación de proveedores válida, registrar un pago de compra responde 400 con el mismo código y no persiste; sin cobertura se guarda.
- **AC-08:** la pestaña «Egresos» lista las categorías activas con su estado (Configurada/Pendiente/Inactiva) y la fila de pagos a proveedores, guarda por fila y muestra errores de la API.
- **AC-09:** cambios de otros flujos sin regresión (gastos y compras existentes, cobros de ventas/servicios, libro de entradas, reportes de gastos).

## Edge cases / Error cases
- Reintento idempotente de un pago existente (`payment_id` repetido): devuelve el existente sin recalcular clasificación.
- Categoría inactiva con asociación: se conserva; no aparece en la pestaña ni en el selector de gastos.
- Clasificación desactivada tras asociarla: la pestaña la marca «Inactiva»; con cobertura el registro se rechaza (`classification_invalid`); sin cobertura se guarda sin instantánea.
- Editar un gasto: si cambia de categoría se recalcula la instantánea con las reglas de creación; si no cambia, se conserva (aunque la asociación haya cambiado).
- Gasto anulado: conserva su instantánea.

## Authorization / permissions
`CompanyAdminPermission` por defecto; `required_modules = ('expenses',)` para categorías y `('purchases',)` para el ajuste de proveedores (la configuración de Contabilidad sigue sin exigir el módulo). El aislamiento sale de `company_id_from(request)`.

## API contract
- **API-01:** `GET /api/expense-categories/` y `…/<id>/` añaden `classification: {id, name, active} | null`.
- **API-02:** `PUT /api/expense-categories/<id>/classification/` body `{classification_id: uuid|null}` → categoría actualizada; 400 `{classification_id: [...]}`, 404 categoría ajena.
- **API-03:** `GET`/`PUT /api/purchases/payment-classification/` → `{classification: {id, name, active} | null}`; mismas validaciones.
- **API-04:** gasto (`/api/expenses/…`) y pago de compra añaden `classification: {id, name} | null` (instantánea).
- **API-05:** errores de registro con cobertura: 400 con `code` `classification_not_configured|classification_invalid` y `detail` accionable (en `category_id` para gastos, `non_field_errors` para pagos).
- Compatibilidad: solo campos añadidos; los clientes actuales no se rompen.

## UI behavior
- **UI-01:** pestaña «Egresos» en `accounting-settings` (plantilla de configuración con listados en pestañas, DDR): tabla de categorías + fila «Pagos a proveedores», guardar por fila, estados cargando/vacío/error/éxito.
- **UI-02:** detalle del gasto muestra «Clasificación».
- **UI-03:** formularios de gasto y pago de compra muestran el enlace «Configurar en Contabilidad → Egresos» ante los códigos de API-05.

## Non-functional requirements
Sin consultas N+1 en listas (nombres de clasificación en una consulta por lote). Todos los textos con claves es/en/pt.

## Out of scope
Cuenta de salida, movimientos y reversión (CONT-02, GAS-01/02, COM-01); saldos y reportes (CONT-04/05); unificar catálogos; backfill de gastos/pagos anteriores; configurar desde el diálogo de categoría.

## Open questions
Ninguna que bloquee. (Riesgo aceptado: empresas con Contabilidad habilitada deberán configurar antes de registrar con cobertura.)

# Test Specification

## Unit tests
- Dominio de Gastos: resolver instantánea (con/sin asociación, cambio de categoría).
- Casos de uso con fakes: `SetCategoryClassification`, `CreateExpense`/`UpdateExpense` con puerto `ClassificationGateway`, `RegisterPayment`.
## Integration tests
- API: asociación (AC-01, AC-02 por tipo de clasificación y empresa, AC-05), instantánea y no reclasificación (AC-03), pago de compra (AC-04, AC-07), cobertura vs. sin cobertura (AC-06, AC-07), migraciones aditivas, aislamiento por empresa.
- `accounting.services.describe_classifications` (empresa ajena no aparece).
- Fronteras: `test_boundaries` con nuevas dependencias; `accounting` ↛ `expenses/purchases` sigue verde.
- Frontend (Karma): servicio de API, pestaña «Egresos» (estados y guardado por fila), detalle del gasto, `i18n:check`.
## E2E
**NO** — no es un flujo crítico de punta a punta; la integración de API y las pruebas de componentes cubren el comportamiento.
## Regression tests
Suites `accounting`, `receivables`, `sales`, `expenses`, `purchases`, `reporting` y `test_boundaries`; `npm test` de la parte tocada.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API de expenses (asociar + crear gasto) |
| AC-02 | API de expenses y purchases (ingreso/inactiva/ajena/inexistente) + `validate_classification` |
| AC-03 | API (cambiar asociación y comprobar gasto/pago previos) |
| AC-04 | API de purchases (pago guarda clasificación; sin gasto creado) |
| AC-05 | API (usuario no admin → 403) |
| AC-06 | API de expenses con `coverage_status` real (habilitado/deshabilitado/antes del corte) |
| AC-07 | API de purchases con cobertura real |
| AC-08 | Karma: pestaña «Egresos» |
| AC-09 | Suites de regresión listadas |

# Implementation Plan

## Architecture considerations
Ver ADR: asociación en el módulo dueño, instantánea en el registro, validación vía `accounting.services`; imports solo en `infrastructure/adapters.py` con puerto en `application/ports.py`.

## Proposed solution
1. Contabilidad expone `describe_classifications`.
2. Expenses: `ClassificationGateway` + adaptador; `ExpenseCategory.classification_id`; casos de uso `SetCategoryClassification`; `CreateExpense/UpdateExpense` resuelven la instantánea con la regla de cobertura.
3. Purchases: ajuste `PurchaseSettings`, casos de uso de ajuste, `RegisterPayment` resuelve la instantánea.
4. Frontend: pestaña «Egresos», detalle de gasto, enlace en errores.

## Files/components affected
- **Backend:** `accounting/services.py`; `expenses/{domain,application,infrastructure,api}`, `expenses/services.py` (sin cambios de contrato); `purchases/{domain,application,infrastructure,api}`; `config/urls.py`; `sales/tests/test_boundaries.py`.
- **Migraciones:** `expenses/0003_classification.py`, `purchases/0008_payment_classification.py`.
- **Frontend:** `features/accounting/{components/expense-config-tab,services,models,pages/accounting-settings}`, `features/expenses/{models,services,pages/expense-detail,pages/expense-form}`, `features/purchases` (pago), `assets/i18n/{es,en,pt}.json`.
- **Docs:** `docs/design/design-system.md` solo si la pestaña añade un patrón nuevo (no se espera).

## Implementation steps
1. Fachada de Contabilidad `describe_classifications` + pruebas (AC-02).
2. Fronteras: `ALLOWED_DEPENDENCIES`/`CONSUMERS` + puerto/adaptador de Expenses.
3. Migración y modelo de Expenses; dominio/aplicación (`SetCategoryClassification`, instantánea y regla de cobertura); API y serializers (INV-01..03, AC-01..03, AC-05, AC-06).
4. Migración y modelo de Purchases (`PurchaseSettings`, `PaymentModel.classification_id`); aplicación y API (AC-02, AC-04, AC-07, INV-04).
5. Frontend: servicios y modelos; pestaña «Egresos»; detalle del gasto; enlaces de error; i18n es/en/pt (AC-08, UI-01..03).
6. Regresiones y `i18n:check`, `npm run lint`, build (AC-09).

## Database / migrations
Aditivas y anulables: `expenses_category.classification_id`, `expenses_expense.classification_id`, tabla `purchases_settings`, `purchases_payment.classification_id`. Rollback: migrar hacia atrás; sin datos destructivos.

## Risks
Empresas con Contabilidad habilitada sin asociaciones no podrán registrar con cobertura hasta configurar (mensaje accionable; pestaña «Pendiente»). Contrato de la instantánea compartido con CONT-02/GAS-01/COM-01.

## New dependencies
Ninguna (`pip`/`npm`).
