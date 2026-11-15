# TASK-categorias-gastos-clasificacion-egreso: Clasificación de egreso por categoría de Gastos y para pagos a proveedores (CONT-03)

**Etapa actual:** ENGINEERING (implementación escrita; pruebas de backend con BD pendientes de ejecutar)
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-categorias-gastos-clasificacion-egreso (base: `origin/accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/76
**Fuente:** https://trello.com/c/x0qPnHlK/4-cont-03-configurar-clasificaci%C3%B3n-de-categor%C3%ADas-de-gastos-y-pagos-a-proveedores

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-15 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-03 | delivery-start |
| 2026-11-15 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Veredicto NEEDS_ARCHITECTURE, diseño SI | delivery-start |
| 2026-11-15 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR | delivery-start |

## Investigación

### Requerimiento
Tarjeta CONT-03 (insumo, no Specification aprobada). Objetivo: evitar que la persona clasifique dos veces una operación y mantener una configuración consistente. Pide: (1) asociar cada categoría de Gastos con una clasificación de egreso activa de la misma empresa; (2) usar esa asociación al registrar un gasto (categoría y cuenta de salida son pasos distintos); (3) configurar una clasificación de egreso para pagos de Compras («Pago a proveedores»), sin convertirla en gasto operativo; (4) exponer configuración y validaciones en API y frontend con permisos equivalentes a la administración contable; (5) con Contabilidad habilitada y sin configuración, impedir confirmar y mostrar cómo corregirlo; (6) cambiar la asociación afecta solo operaciones nuevas; (7) las categorías inactivas se conservan en gastos históricos y no se ofrecen en registros nuevos.
Pruebas de aceptación de la tarjeta: 1) Alquiler → clasificación de egreso y se aplica al nuevo gasto; 2) rechazar clasificación de ingreso, inactiva o de otra empresa; 3) cambiar la asociación no modifica el movimiento anterior; 4) pagar una compra usa la clasificación de proveedores; 5) usuario sin permiso no modifica asociaciones. Dependencias: CONT-01 y CONT-06 (ambas en `origin/accounting`). Aclaración de la persona: usar la rama `accounting` como base.

### Hechos encontrados
- `backend/modules/accounting/services.py:79` — `validate_classification(company_id, id, direction)` ya valida existencia en la empresa, activa y dirección; es el contrato previsto para egresos (ADR CONT-01, decisión 4).
- `backend/modules/accounting/services.py:93-110` — `coverage_status(company_id, effective_date)` es la decisión única de cobertura: sin cobertura la operación se guarda sin movimiento y sin error; con cobertura exige configuración válida (ADR CONT-06, decisión 5).
- `backend/modules/accounting/infrastructure/lifecycle.py:12-21` — no existen aún movimientos de egreso (`open_count` = 0); los registra CONT-02.
- `backend/modules/expenses/infrastructure/django/models.py:7-48` — `ExpenseCategoryModel` y `ExpenseModel` no tienen clasificación; categoría y empresa por UUID.
- `backend/modules/expenses/application/commands.py:12-21,24-41` — `CreateExpense` valida categoría existente y activa; `UpdateExpense` solo exige categoría activa si cambia.
- `backend/modules/expenses/api/views.py:70-90` — `ExpenseListCreateView` crea con `CreateExpense`; permisos por defecto `CompanyAdminPermission` + `required_modules = ('expenses',)`.
- `backend/modules/purchases/application/payment_commands.py:23-37` — `RegisterPayment` registra el pago con la compra bloqueada; no toca Contabilidad ni clasificación.
- `backend/modules/purchases/infrastructure/django/models.py:114-131` — `PaymentModel` sin clasificación; Purchases no tiene tabla de ajustes de empresa.
- `backend/modules/sales/tests/test_boundaries.py:12-28,36` — `expenses: set()` y `purchases: {catalog, inventory}`; `CONSUMERS` solo permite imports entre módulos desde `infrastructure/adapters.py`.
- `docs/adr/ADR-modularidad-corte-historicos-contabilidad-ciclo-de-vida-y-corte.md` (decisión 7) — fija la dirección objetivo `expenses → accounting` y `purchases → accounting` por `services.py`, y la regla `accounting` ↛ `expenses`/`purchases` (probada en `backend/modules/accounting/tests/test_coverage.py:300-316`).
- `backend/config/permissions.py:20-39` — toda la API exige admin de empresa activa; no hay roles contables distintos: «permisos equivalentes» = `CompanyAdminPermission`.
- `frontend/panel_admin/src/app/features/accounting/pages/accounting-settings/accounting-settings.component.html:21-39` — página de configuración con pestañas (Cuentas, Métodos, Clasificaciones, Corte); ruta sin `moduleGuard` (`app.routes.ts:104-107`) para configurar antes de habilitar.
- `frontend/panel_admin/src/app/features/expenses/services/categories-api.service.ts:15-48` — servicio de categorías con `list/create/rename/activate/deactivate` bajo `/expense-categories/`.

### Hipótesis / supuestos no confirmados
- Como CONT-02 (registro de egresos) y GAS-01/COM-01 aún no existen, «el movimiento anterior» se materializa hoy como la **clasificación guardada en el propio gasto o pago al crearlo** (instantánea); CONT-02/GAS-01/COM-01 la consumirán para crear el movimiento. (Decisión de diseño, ver ADR.)
- El bloqueo «impedir confirmar» se aplica al **registrar el gasto y el pago de compra** cuando `coverage_status.covered` y falta o es inválida la configuración. Empresas con Contabilidad ya habilitada deberán configurar antes de registrar nuevos gastos/pagos (riesgo de despliegue, ver Riesgos).

### Módulos y dependencias relacionadas
`accounting` (validación y nombres de clasificaciones), `expenses` (asociación por categoría, instantánea en el gasto), `purchases` (ajuste de empresa y instantánea en el pago), `reporting` (lee Gastos; no cambia), frontend `features/accounting`, `features/expenses`.

### Implementaciones similares existentes
- Ajuste por empresa con puerto/ciclo de vida: `accounting_settings` y `accounting_method_mapping` (`accounting/infrastructure/django/models.py:28-60,83-95`).
- Adaptadores entre módulos: `purchases/infrastructure/adapters.py` (patrón puerto en `application/ports.py` + adaptador sobre `services.py`).
- Pestaña de configuración con listado y diálogo: `classifications-tab` (`docs/design/design-system.md`, sección 5).

### Comportamiento actual
Un gasto solo guarda categoría; un pago de compra no guarda clasificación; no hay vínculo categoría↔clasificación ni ajuste de proveedores. Contabilidad habilitada no condiciona hoy ni gastos ni pagos de compras.

### Restricciones
Fronteras de `test_boundaries.py` (dependencias declaradas, solo por `services.py`, consumidores solo desde `adapters.py`); dominio sin Django; `company_id` del usuario autenticado; no editar migraciones aplicadas; textos con `translate` en es/en/pt; dinero no interviene.

### Riesgos identificados
- **Despliegue:** empresas con Contabilidad habilitada y sin asociaciones quedarían sin poder registrar gastos/pagos hasta configurar; el mensaje de error indica dónde corregirlo y la pestaña muestra lo pendiente. Se avisa en el PR.
- Nuevas dependencias entre módulos (`expenses → accounting`, `purchases → accounting`): sin ciclo, ya previstas por el ADR de CONT-06.
- Solapamiento posterior con CONT-02/GAS-01/COM-01: el contrato (`classification_id` instantánea) debe mantenerse estable para ellas.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — introduce dos dependencias nuevas entre módulos de negocio, migraciones en `expenses` y `purchases` y un contrato API que Angular consumirá; define dónde vive la configuración y cómo se preserva el histórico.

### Diseño requerido
**SI** — hay una pestaña/flujo nuevo de configuración en Contabilidad y cambios visibles en el detalle del gasto y mensajes de error accionables.

## Diseño
Ver [DDR-categorias-gastos-clasificacion-egreso-pestana-egresos](../design/DDR-categorias-gastos-clasificacion-egreso-pestana-egresos.md).

## Arquitectura
Ver [ADR-categorias-gastos-clasificacion-egreso-propiedad-y-snapshot](../adr/ADR-categorias-gastos-clasificacion-egreso-propiedad-y-snapshot.md).

## Plan
[PLAN-2026-11-15-categorias-gastos-clasificacion-egreso](../plans/PLAN-2026-11-15-categorias-gastos-clasificacion-egreso.md) (v1, COMPLETO, Specification READY).

## Implementación
**Backend.** `accounting.services.describe_classifications` (AC-02, INV-01). `expenses`: `classification_id` en categoría y gasto (migración `0003`), puerto `ClassificationGateway` + adaptador `AccountingClassifications`, `SetCategoryClassification`, `resolve_classification` en `CreateExpense`/`UpdateExpense` (AC-01, AC-03, AC-06, INV-02/03), `PUT /api/expense-categories/<id>/classification/` y `classification` en categorías y gastos (API-01/02/04/05). `purchases`: tabla `purchases_settings` y `classification_id` en pagos (migración `0008`), `SetPaymentClassification`/`GetPaymentClassification`, `RegisterPayment` con instantánea y regla de cobertura, `GET/PUT /api/purchases/payment-classification/` (AC-02, AC-04, AC-07, INV-04, API-03). Fronteras: `ALLOWED_DEPENDENCIES`/`CONSUMERS` actualizados.
**Frontend.** Pestaña «Egresos» (`expense-config-tab`, plantilla de configuración con listados en pestañas; reutiliza `AccountingApiService.listClassifications`, badges y `form-select`), servicio `ExpenseConfigApiService`, línea «Clasificación» en el detalle del gasto, claves i18n es/en/pt `ACCOUNTING.EXPENSE_CONFIG` (AC-08, UI-01, UI-02).
**Pruebas.** Backend: `test_classification_application` (sin BD, pasan), `test_classification_api` (expenses) y `test_payment_classification_api` (purchases) escritas pero **no ejecutadas** (sin credenciales de PostgreSQL en este worktree); `test_boundaries` y las pruebas de dominio/aplicación de Gastos pasan. Frontend: 149 specs de `accounting` y `expenses` OK, `lint` e `i18n:check` OK.
**Desviaciones.** UI-03 (enlace «Configurar en Contabilidad → Egresos» en formularios de gasto/pago): el mensaje de la API ya indica la ruta en texto; el enlace queda como mejora. La API de errores de registro devuelve `code` junto a `category_id`/`non_field_errors`.
**Deuda técnica.** Ejecutar y ajustar las pruebas de API y las regresiones de backend (accounting, receivables, sales, expenses, purchases, reporting); `EXPENSE_KEYS`/`PAYMENT_FIELDS` ya incluyen `classification`.

## Review
_Pendiente_

## Publicación
_Pendiente_
