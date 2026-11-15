# TASK-cuentas-dinero-clasificaciones: Cuentas de dinero y clasificaciones de ingresos/egresos (CONT-01)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-cuentas-dinero-clasificaciones
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/74
**Fuente:** https://trello.com/c/ZmEEzqym/1-cont-01-definir-y-adaptar-cuentas-de-dinero-y-clasificaciones-de-ingresos-egresos

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-15 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello; `main` al día (3c81fee) | delivery-start |
| 2026-11-15 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (modelo nuevo + migración sobre `accounting_account`, contrato API, fachada entre módulos) | delivery-start |
| 2026-11-15 | PLANNING → ENGINEERING | Specification READY: las decisiones abiertas se resolvieron con criterio propio y quedan en el plan | delivery-start |
| 2026-11-15 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |

## Investigación

### Requerimiento
Insumo de la tarjeta CONT-01 (lista «Por hacer — orden de implementación», tablero «PocketBiz — Contabilidad: egresos, gastos y compras»; **no es una Specification aprobada**; sin checklists ni comentarios). Objetivo: separar *dónde* se mueve el dinero (cuenta de dinero) de *por qué* se mueve (clasificación), reutilizando Contabilidad. Esperado: revisar el modelo actual y documentar su equivalencia; cuentas (Caja, Banco, Billetera) que admiten ingresos y egresos sin restricción de dirección; clasificaciones que identifican ingreso o egreso (ventas, servicios, alquiler, publicidad, pago a proveedores); método de pago, cuenta y clasificación son conceptos distintos; ambas pertenecen a una empresa y se desactivan sin alterar históricos; no cambiar significado ni saldos de ingresos existentes; sin partida doble ni valoración de inventario. Pruebas de aceptación de la tarjeta: (1) una misma cuenta Banco se selecciona para un cobro y un pago; (2) cuenta/clasificación de otra empresa se rechaza por API; (3) desactivar impide usos nuevos y conserva historial; (4) cobros existentes de ventas y servicios conservan referencias y montos. Dependencias: ninguna.

### Hechos encontrados
- `backend/modules/accounting/infrastructure/django/models.py:8-23` — `AccountModel` (`accounting_account`): `company_id` UUID sin FK, `name` ≤80 (único por empresa sin distinguir mayúsculas), `currency`, `is_active`. **No tiene tipo** (Caja/Banco/Billetera) ni restricción de dirección: ya sirve para ingresos y egresos.
- `models.py:26-40` — `MethodMappingModel`: método de pago → cuenta, una fila por `(company_id, method)`. El método ya es un concepto aparte de la cuenta.
- `models.py:43-76` — `EntryModel`: entrada de libro inmutable (solo inserta), con `account` FK `PROTECT`, `payment_method`, `origin_kind` (`PRODUCT`/`SERVICE`), `origin_id`. **No hay clasificación**; el «por qué» hoy solo se infiere de `origin_kind`.
- `backend/modules/accounting/domain/account.py:50-78` — agregado `Account` (`create`, `rename`, `change_currency`, `activate`, `deactivate`, `can_receive`); `domain/catalog.py:6-18` — métodos, `FLOW_CURRENCY='BOB'`, `ORIGIN_KINDS`.
- `backend/modules/accounting/application/use_cases.py:90-105` — `DeactivateAccount` bloquea (409 `account_in_use`) si métodos activos la usan; el historial se conserva porque las cuentas no se borran (`PROTECT`).
- `backend/modules/accounting/services.py:34-45,88-113` — fachada: `resolve_account(company_id, method)` y `record_entry` (rechaza cuenta inexistente en la empresa, `services.py:103-105`; moneda distinta). No hay fachada para validar una cuenta o clasificación elegida por otro módulo.
- `backend/modules/accounting/api/urls.py:16-27` y `api/views.py:100-130` — API `/api/accounting/accounts|payment-methods|entries|regularization`; vistas de configuración con `required_modules = ()` y empresa de `company_id_from(request)`.
- `backend/modules/expenses/domain/category.py:14-33` y `expenses/infrastructure/django/models.py:8-31` — `ExpenseCategory` (`expenses_category`, por empresa, activo/inactivo, FK `PROTECT` desde `ExpenseModel`): es el equivalente actual de una **clasificación de egreso**, pero vive en otro módulo y no existe su par de ingresos.
- `backend/modules/accounting/migrations/0001..0003` — historial de migraciones aplicado (no se edita).
- Frontend: `features/accounting/models/accounting.ts:8-25` (`Account` sin tipo), `components/accounts-tab/accounts-tab.component.ts:17-130` (lista, filtro activo/inactivo, diálogo, bloqueo 409), `components/account-dialog`, `pages/accounting-settings` (pestañas Cuentas y Métodos), ruta `accounting/settings` sin `moduleGuard` (`app.routes.ts:105`).
- Plantilla de pantalla: «Configuración con listados en pestañas y diálogo» (`docs/design/design-system.md:141`).
- Antecedentes: `docs/tasks/TASK-crear-cuentas-mapear-metodos-pago.md`, `TASK-pagos-ventas-libro-entradas.md`, `TASK-pagos-servicios-libro-entradas.md`, `TASK-validar-cobros-unificados-accounting.md`.

### Hipótesis / supuestos no confirmados (resueltos en el plan)
- «Cuenta de dinero» = `Account` existente; se le añade un **tipo** (Caja/Banco/Billetera) y se mantiene sin restricción de dirección.
- Las cuentas ya existentes quedan **sin tipo** (no se infiere); el tipo es obligatorio solo al crear y editable después.
- La clasificación es un concepto nuevo de Contabilidad (`INCOME`/`EXPENSE`); `ExpenseCategory` **no se migra** en esta tarea (equivalencia documentada en el ADR).
- No se enlazan entradas ni gastos a clasificaciones todavía (eso corresponde a las tarjetas siguientes); aquí solo se define el catálogo y la fachada de validación.
- El «pago» de la prueba 1 aún no existe en Contabilidad: se verifica con la fachada de validación de cuenta, válida para ambas direcciones.
- No se siembran clasificaciones por defecto (los ejemplos de la tarjeta son ilustrativos).

### Módulos y dependencias relacionadas
`accounting` (dominio, aplicación, API, migración, fachada); consumidores futuros `expenses`/`purchases` vía `accounting.services`; frontend `features/accounting`. Sin cambios en `sales`/`receivables`.

### Implementaciones similares existentes
Cuentas: `Account` y su CRUD con activar/desactivar. Clasificaciones: `ExpenseCategory` y su repositorio por empresa.

### Comportamiento actual
Las cuentas reciben cobros según el mapeo método → cuenta; las entradas guardan cuenta, método y origen. No hay tipo de cuenta ni clasificación.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, `Decimal`, no editar migraciones aplicadas, i18n es/en/pt, DDD pragmático, módulos solo por `services.py`.

### Riesgos identificados
- Migración sobre una tabla con datos (columna nueva anulable: sin reescritura de filas ni cambio de saldos).
- Confundir clasificación con `ExpenseCategory` (dos catálogos coexistiendo hasta una tarea posterior).
- Cambios de contrato API de cuentas: el campo nuevo debe ser opcional en lectura para clientes actuales.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — modelo y migración nuevos sobre datos existentes, contrato API ampliado y fachada nueva consumible por otros módulos.

### Diseño requerido
**SI** — pestaña nueva de clasificaciones, selector de tipo en el diálogo de cuentas.

## Diseño
`docs/design/DDR-cuentas-dinero-clasificaciones-pestanas-cuentas-clasificaciones.md`

## Arquitectura
`docs/adr/ADR-cuentas-dinero-clasificaciones-modelo-y-contrato.md`

## Plan
`docs/plans/PLAN-2026-11-15-cuentas-dinero-clasificaciones.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
**Backend** (`backend/modules/accounting/`): `Account.kind` (`CASH/BANK/WALLET`, nulo en legadas; INV-02) y agregado `Classification` (`domain/classification.py`; INV-03, INV-04, `ensure_usable` INV-05); `ClassificationModel` + migración `0004_account_kind_classification` (solo `AddField` anulable y `CreateModel`); `DjangoClassificationRepository` por empresa; casos de uso de clasificaciones; API `/api/accounting/classifications/` (list/create, detalle GET/PATCH solo nombre, activate/deactivate) y `kind` en cuentas (alta obligatoria en el serializer, PATCH opcional) (API-01..05); fachada `validate_money_account` y `validate_classification` en `services.py` (AC-01..03). `EntryModel` y `record_entry` sin cambios (AC-04).
**Frontend** (`features/accounting/`): `kind` en modelos y servicio, columna «Tipo» y selector obligatorio en el diálogo de cuenta, pestaña `ClassificationsTabComponent` y `ClassificationDialogComponent`, tercera pestaña en `AccountingSettingsComponent`, claves i18n es/en/pt (UI-01..03). Referencia: plantilla «listados en pestañas y diálogo» (`inventory-configuration`), reutilizando estilos de `AccountsTabComponent`; sin componentes compartidos nuevos.
**Cobertura:** AC-01..03, 05..07 → `accounting/tests/test_classifications.py` (dominio, API con dos empresas, fachada); AC-04 → `test_unified_journey`, `test_entries_api` y pagos de Ventas/Cobros dentro de la suite completa; UI → specs de `classifications-tab`, `classification-dialog`, `account-dialog`, `accounting-settings`.
**Desviaciones respecto al plan:** (1) `Account.create` mantiene `kind` opcional en el dominio (muchos tests y fixtures crean cuentas sin tipo); la obligatoriedad al crear se aplica en el serializer de la API, único punto de alta real. (2) No hubo test de migración de datos dedicado: la migración es aditiva y la regresión de entradas lo cubre.
**Ejecución propia (no es el Quality Gate):** `manage.py test` completo 1663 OK; `ng test` 1419/1420 (falla `screens-i18n.spec.ts` «Entregue/Entregado», que también falla en `main` limpio); `npm run lint` e `i18n:check` OK.
**Deuda técnica:** coexistencia de `ExpenseCategory` y clasificaciones EXPENSE; cuentas legadas «Sin tipo» hasta editarlas.

## Review
_Pendiente_

## Publicación
_Pendiente_
