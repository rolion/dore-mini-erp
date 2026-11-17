# PLAN-2026-11-16-configurar-asientos-automaticos-modulo (v4)

**Task:** TASK-configurar-asientos-automaticos-modulo · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-configurar-asientos-automaticos-modulo-panel-cuentas-por-evento.md` · `docs/adr/ADR-configurar-asientos-automaticos-modulo-catalogo-modelo-y-fachada.md`

## Objective
Definir una configuración simple de cuentas por evento de negocio (catálogo fijo, sin constructor de reglas), con validación por rol, vista previa Debe/Haber y una fachada que los módulos usarán para verificar la configuración antes de confirmar y contabilizar con el motor CONT-02 sin duplicar ni omitir en silencio. La UI se monta en cada módulo (Ventas, Compras, Inventario, Gastos).

## Context
Base: rama `accounting` (PR #84 integrado, no está en `main`). Ningún módulo contabiliza por partida doble aún; VEN-01, COM-01/02, INV-01 y las tarjetas de gastos consumirán esta fachada. Ver TASK (hechos con `archivo:línea`) y ADR.

# Specification

## Domain context
Bounded context `accounting` (config + fachada). Módulos relacionados solo en frontend (`sales`, `purchases`, `inventory`, `expenses`); en backend se relacionan a futuro por `accounting.services`.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Evento | Hecho de negocio contabilizable; su código es el `origin_kind` del asiento | ADR §1 |
| Rol | Función de una cuenta en un evento (Ingresos por ventas, Cuentas por cobrar…) con clasificación obligatoria | ADR §1 |
| Mapeo | Cuenta elegida por la empresa para un rol, una categoría de gasto o un método de pago | ADR §2 |
| Cuenta de dinero | Cuenta de Activo (caja, banco…) a la que apunta un método de pago; no se exige tipo de cuenta; **no** es el método de pago | tarjeta, `domain/account.py` |
| Cobertura | Decisión de si una operación debe crear asiento (`coverage_status`) | `services.py:127` |
| Configuración faltante | Rol/método/categoría sin cuenta o con cuenta no utilizable | ADR §4 |

## Current behavior
Existe el motor y el mapeo método → cuenta sin validar clasificación (`api/views.py:353-360`, `domain/account.py:157-174`); no hay configuración por evento ni verificación previa; los módulos no contabilizan (TASK › Hechos).

## Expected behavior
- Por módulo se listan solo sus eventos con vista previa Debe/Haber y el estado de la configuración.
- La persona asigna cuentas por rol (y por categoría de gasto, y por método de pago a una cuenta de Activo); el servidor valida empresa, cuenta activa y clasificación.
- Con Contabilidad habilitada y cobertura, `check_posting_ready` informa lo que falta con mensaje accionable y `post_automatic_entry` lo exige (nunca omite); sin cobertura no se exige ni se crea nada.
- Cambiar la configuración no altera asientos existentes; la reversión usa las cuentas originales.
- El asiento de un evento lleva `origin_kind` = código del evento y `origin_id` del evento del módulo; repetirlo no lo duplica.

## Domain rules / invariants
- **INV-01** (nueva) El catálogo de eventos/roles es fijo; ninguna API crea, edita o borra eventos o líneas.
- **INV-02** (nueva) Una cuenta asignada a un rol cumple: de la empresa, activa, clasificación habilitada e igual a la del rol. Categoría de Gastos: su cuenta es de Gastos (el id de la categoría es opaco para Contabilidad). Método: cuenta de Activo (sin exigir tipo de cuenta), activa y en BOB. Se valida al asignar y al resolver cada evento.
- **INV-03** (nueva) Un evento contabilizable con configuración incompleta no se omite: error `PostingConfigurationMissing`; sin cobertura, no se exige configuración y no se crea asiento.
- **INV-04** (existente, CONT-02) Idempotencia por `(empresa, origen)`; reversión con cuentas originales; fecha en período abierto.
- **INV-05** (existente) Dinero en `Decimal`, moneda BOB de los flujos, sin conversión.
- **INV-06** (nueva) Modificar la configuración nunca modifica asientos existentes.

## Acceptance criteria
- **AC-01** `GET posting-config/?module=sales|purchases|inventory|expenses|receivables` devuelve solo los eventos de ese módulo con vista previa y estado; módulo desconocido → 404.
- **AC-02** Asignar un rol con una cuenta válida lo guarda (y quitarla con `null`); la vista previa y `ready` reflejan el cambio.
- **AC-03** (tarjeta AC-4) Cuenta de **otra empresa**, inexistente, inactiva, de **clasificación inválida** para el rol, o, para una categoría de Gastos, una cuenta que no es de Gastos → 400 por `account_id` con mensaje accionable; no se guarda.
- **AC-04** El mapeo de método a cuenta (`PUT payment-methods/<code>/`) rechaza cuentas que no sean de Activo (sin exigir tipo Caja/Banco/Billetera); lo ya configurado sigue resolviendo.
- **AC-05** (tarjeta AC-1) Con un asiento ya contabilizado, cambiar el mapeo (p. ej. Banco → Caja) no modifica sus líneas; `reverse_automatic_entry` revierte con las cuentas originales aunque estén deshabilitadas o ya no estén en la configuración.
- **AC-06** (tarjeta AC-2) Con Contabilidad habilitada y cobertura, configuración incompleta: `check_posting_ready` → `ready=False` con issues; `post_automatic_entry` lanza `PostingConfigurationMissing` y no crea asiento.
- **AC-07** (tarjeta AC-2) Cuenta configurada luego deshabilitada o reclasificada: mismo bloqueo, con el nombre de la cuenta/rol y la ruta del módulo donde corregir.
- **AC-08** (tarjeta AC-3) Contabilidad deshabilitada, operación anterior al corte o en hueco: `required=False`, `posted=False` con razón, sin exigir cuentas; tras deshabilitar y volver a habilitar, las operaciones del tramo sin cobertura no generan asientos.
- **AC-09** Dos llamadas con el mismo evento y `origin_id` crean un solo asiento (`created=False` en la segunda); mismos origen con datos distintos → conflicto; el asiento guarda `origin_kind` = código del evento.
- **AC-10** Aislamiento: la configuración y los asientos de una empresa no aparecen ni se pueden usar desde otra.
- **AC-11** Solo administradores de la empresa acceden a la API (otros → 403, sin sesión → 401).
- **AC-12** El panel muestra solo los eventos de su módulo, recalcula la vista previa Debe/Haber en vivo, muestra faltantes con aviso, indica cuando Contabilidad está deshabilitada y explica que los cambios aplican a operaciones futuras.
- **AC-13** El panel está montado como pestaña «Asientos automáticos» en Ventas, Compras e Inventario y en una nueva «Configuración» de Gastos (ruta y menú).
- **AC-14** Sin texto hardcodeado (es/en/pt con las mismas claves), accesible (labels, foco, `role="alert"`), usable a 375 px y en tema oscuro. Los avisos de configuración faltante, los problemas de cada fila y los errores 400 se muestran **traducidos al idioma activo** a partir de `code`/`params`/`problem`; el mensaje del servidor (español) solo es respaldo.

## Edge cases / Error cases
- **EDGE-01** Rol compartido (INVENTORY, RECEIVABLE): cambiarlo desde un módulo cambia el otro; la UI lo indica.
- **EDGE-02** Método inactivo o sin cuenta usado en un evento con método → issue `method_unconfigured` con el nombre del método.
- **EDGE-03** Categoría de gasto sin cuenta → issue `category_unconfigured` (con su nombre si el módulo lo informa); sin categoría en la operación → `category_required`.
- **EDGE-04** Empresa sin cuentas de la clasificación requerida: el selector queda vacío y enlaza a Cuentas.
- **EDGE-05** Importe ≤ 0 o no `Decimal`, o fecha fuera de período abierto: error del motor (400 `JournalValidationError`, `DateOutsideFiscalPeriod`, `FiscalPeriodClosed`) sin asiento parcial.
- **EDGE-06** Empresa con cuentas heredadas sin clasificar: no se pueden elegir para roles nuevos; mensaje indica clasificarlas en Cuentas.

## Authorization / permissions
Permiso por defecto de la API (administrador de la empresa activa). La empresa sale del usuario autenticado, nunca del cliente. Sin `required_modules = ('accounting',)` en la configuración (se prepara antes de habilitar Contabilidad); sí lo aplican las rutas de asientos existentes.

## API contract
- **API-01** `GET /api/accounting/posting-config/?module=<clave>` → `200 {module, module_label, accounting_enabled, ready, events:[{code, label, preview:[{side:'DEBIT'|'CREDIT', role, label, account:{id,code,name,is_active}|null, status:'ok'|'missing'|'invalid'|'by_method'|'by_category'}], issues:[{code, role, subject, module, message, params, problem}]}], roles:[{role, label, account_class, account|null, issue, problem, shared_with:[{module,label}]}], methods:[{code, label, is_active, account|null, issue, problem}], categories:[{category_id, account, issue, problem}]}`. `methods` solo si el módulo tiene eventos con método y `categories` solo en Gastos (únicamente las categorías con cuenta; el nombre y el estado son de Gastos). `problem` = `{code, params, message}` con la causa estructurada de una cuenta no válida (`account_missing`, `account_inactive`, `currency`, `no_code_class`, `wrong_class`, `class_disabled`, `method_account_missing`); `issues[].code` ∈ `role_unconfigured`, `account_invalid`, `method_unconfigured`, `method_required`, `category_unconfigured`, `category_required`. 404 módulo desconocido.
- **API-02** `PUT /api/accounting/posting-config/roles/<role>/` `{account_id: uuid|null}` → `200` (la fila del rol); 400 `{account_id:[…], problem:{code, params}}` (el `problem` solo cuando la cuenta no es válida para el rol; el mensaje en español es el respaldo); 404 rol desconocido.
- **API-03** `PUT /api/accounting/posting-config/categories/<category_id>/` `{account_id: uuid|null}` → `200 {category_id, account, issue}`; 400 como API-02; el id de la categoría es opaco (cualquier UUID; no hay 404 por categoría).
- **API-04** (cambio de comportamiento) `PUT /api/accounting/payment-methods/<code>/`: nuevo 400 por `account_id` si la cuenta no es de Activo (el tipo de cuenta no se exige). Forma de respuesta sin cambios.
- **Fachada (no HTTP)** `describe_posting_config`, `check_posting_ready`, `post_automatic_entry`, `reverse_automatic_entry`, `set_role_account`, `set_category_account` (ADR §5). Compatibilidad: todo es aditivo salvo API-04.

## UI behavior
Según DDR.
- **UI-01** Panel `app-posting-config-panel` con aviso de estado, sección Cuentas, sección Métodos (si aplica), sección Categorías (Gastos) y Asientos previstos (plantilla «Configuración con listados en pestañas y diálogo» + «Variante con previsualización» de `design-system.md` §5).
- **UI-02** Pestaña «Asientos automáticos» en `module-settings` de Ventas/Compras/Inventario; página y menú «Configuración» de Gastos (`/expenses/settings`).
- **UI-03** Estados: cargando, error con «Reintentar», guardando/guardado/error por fila, vacío del selector.

## Non-functional requirements
Resolución de un evento ≤ 6 consultas; lectura de configuración por módulo ≤ 8 consultas (sin N+1 por categoría/método). Todo filtrado por `company_id`. Sin dependencias nuevas.

## Out of scope
Migrar Ventas/Cobros/Compras/Inventario/Gastos a contabilizar (VEN-01, COM-01/02, INV-01, GAS-xx); pantalla para Cobros/Servicios; reglas definidas por la persona; eventos de más de dos líneas, impuestos o descuentos; historial de cambios de configuración; conversión de divisas; quitar la pantalla heredada de Métodos de pago (CONT-13).

## Open questions
- (No bloquea) ¿Ventas y Servicios deben poder separar sus cuentas por cobrar? Hoy comparten `RECEIVABLE`; separarlo es un rol nuevo sin migración.

# Test Specification

## Unit tests
Dominio `domain/posting.py` (sin BD): catálogo coherente (código ≤ 30, cada rol existe, ninguna línea repetida), `validate_role_account`, `preview`, issues. Dominio de método (Activo; sin exigir tipo).

## Integration tests (backend, `accounting/tests/`)
- `test_posting_config_api.py`: API-01..04, AC-01..04, AC-10, AC-11; número de consultas de API-01.
- `test_posting_service.py`: `check_posting_ready`, `post_automatic_entry`, `reverse_automatic_entry` (AC-05..AC-09, INV-03/06), con `module_gate` habilitado/deshabilitado, corte y huecos de cobertura, cuenta desactivada/reclasificada, idempotencia/conflicto, fecha en período cerrado, importe inválido.
- Ajustes a `test_api.py`/`test_classifications.py` si asignan métodos a cuentas no válidas (AC-04); `test_boundaries` sin cambios (solo fachada).
- `makemigrations --check` sin pendientes; `0011` solo `CreateModel`.

## Frontend tests
Specs de `posting-config-api.service`, del panel (vista previa en vivo, faltantes, error 400 por fila, Contabilidad deshabilitada, vacío del selector), de `module-settings` (pestaña) y de la página de Configuración de Gastos; `sidebar-menu.spec` y `i18n` (es/en/pt iguales; `npm run i18n:check`).

## E2E
**NO** — no es un flujo crítico de punta a punta: ningún módulo contabiliza todavía; la cobertura la dan integración backend y specs de componentes. Sin Playwright. Revisión visual en navegador (escritorio, 375 px, tema oscuro) durante la publicación.

## Regression tests
Suites de `accounting`, `modularity`, `shared` (fronteras) y frontend completa; mapeo de métodos y regularización (usan `MethodMapping`).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | `test_posting_config_api` (módulos, 404) |
| AC-02 | `test_posting_config_api` (PUT roles, `null`, vista previa/`ready`) |
| AC-03 | `test_posting_config_api` (ajena, inexistente, inactiva, clase inválida, cuenta que no es de Gastos para una categoría) |
| AC-04 | `test_posting_config_api` + `test_api.py` (método: no Activo → 400; Activo sin tipo → 200) |
| AC-05 | `test_posting_service` (cambio de mapeo, líneas intactas, reversión con cuentas originales deshabilitadas) |
| AC-06 | `test_posting_service` (`check_posting_ready`, `PostingConfigurationMissing`, sin asiento) |
| AC-07 | `test_posting_service` (cuenta desactivada/reclasificada; mensaje con rol y módulo) |
| AC-08 | `test_posting_service` (módulo off, antes del corte, hueco; deshabilitar/habilitar) |
| AC-09 | `test_posting_service` (idempotencia, conflicto, `origin_kind`) |
| AC-10 | `test_posting_config_api` / `test_posting_service` (dos empresas) |
| AC-11 | `test_posting_config_api` (403/401) |
| AC-12 | spec del panel + revisión en navegador |
| AC-13 | specs de `module-settings`, Gastos y menú; revisión en navegador |
| AC-14 | `i18n:check`, spec de i18n, revisión visual (375 px, tema oscuro) |

# Implementation Plan

## Architecture considerations
Capas: dominio puro (`posting.py`), casos de uso (`application/posting.py`), repositorio Django, fachada. Los módulos de negocio no importan `accounting` en backend en esta tarea. Cumple `docs/architecture/ddd.md` (fachada con DTO inmutables, `company_id` primer argumento).

## Proposed solution
Ver ADR. Resumen: catálogo en código; tabla `accounting_posting_account` para roles y categorías; `MethodMapping` para métodos; resolución en vivo; helpers de fachada sobre `post_journal_entry`/`reverse_journal_entry`.

## Files/components affected
- Backend (`backend/modules/accounting/`): `domain/posting.py`; `application/posting.py`; `infrastructure/django/models.py` (`PostingAccountModel`) + `repositories.py` (`DjangoPostingConfigRepository`); `migrations/0011_posting_account.py`; `services.py` (+ `__all__`); `api/posting_serializers.py`, `api/posting_views.py`, `api/urls.py`; endurecimiento en `domain/account.py` (`MethodMapping.configure`) o `ConfigureMethod`; tests nuevos y ajustes.
- Frontend (`frontend/panel_admin/src/app/`): `features/accounting/models/posting-config.ts`, `services/posting-config-api.service.ts`, `components/posting-config-panel/*`; `features/settings/pages/module-settings` (pestaña); `features/expenses/pages/expense-settings/*`, `expenses.routes.ts`; `assets/data/routes.json` (Gastos › Configuración); `assets/i18n/{es,en,pt}.json` (`ACCOUNTING.POSTING.*`, menú); `testing/` fixtures; specs.
- Docs: `docs/design/design-system.md` (§5 patrón y §6 menú), `docs/architecture/ddd.md` (nota de la fachada, si aplica).

## Implementation steps
1. **Dominio** (INV-01/02): `domain/posting.py` con catálogo de roles/eventos, `PostingIssue`, `validate_role_account`, `build_preview`; tests unitarios. → AC-01, AC-03.
2. **Persistencia**: modelo + migración `0011` + repositorio (`get/save/clear` por rol y categoría, lectura por módulo en una consulta). → AC-02, AC-10.
3. **Casos de uso** `application/posting.py`: `DescribePostingConfig`, `SetRoleAccount`, `SetCategoryAccount`, `ResolveEvent` (valida en vivo), todo por `company_id`. → AC-02, AC-03, AC-06, AC-07.
4. **Endurecer método → cuenta** (Activo, solo usos nuevos; sin exigir tipo); ajustar tests existentes. → AC-04.
5. **Fachada** en `services.py`: `describe_posting_config`, `set_*`, `check_posting_ready`, `post_automatic_entry` (cobertura → resolución → `post_journal_entry`), `reverse_automatic_entry`, excepciones públicas. → AC-05..AC-09, INV-03/04/06.
6. **API** (API-01..03) con serializers de forma, `_run` de errores, 404/400; rutas. → AC-01..AC-03, AC-11.
7. **Pruebas backend** (ver mapeo) + `makemigrations --check`, flake8.
8. **Frontend servicio y modelos** (`posting-config-api.service`, tipos sin `any`, fixtures). → AC-12.
9. **Panel** `app-posting-config-panel` (Reactive Forms por fila, vista previa en vivo, estados, a11y, `tr()`/pipe `translate`). → AC-12, AC-14.
10. **Montaje**: pestaña en `module-settings` para sales/purchases/inventory; página y ruta `/expenses/settings` + ítem de menú; `routes.json`, i18n es/en/pt, `sidebar-menu.spec`. → AC-13.
11. **Pruebas frontend**, `npm run lint`, `i18n:check`, `ng build`, suite completa.
12. **Docs**: `design-system.md`; revisar `ddd.md`. Revisión visual (escritorio, 375 px, tema oscuro) en publicación.

## Database / migrations
`0011_posting_account` solo `CreateModel` (unicidad `(company_id, scope, key)`, FK `PROTECT` a cuenta, índice por empresa). Nunca editar `0001-0010`. Rollback: `migrate accounting 0010`.

## Risks
- Endurecer método → cuenta rompe tests/datos heredados (mitigado: solo usos nuevos, mensaje accionable).
- Que el panel (en `features/accounting`) cree dependencias entre features (aceptado, DDR).
- Cobertura perezosa de `coverage_status` abre transacción: llamarlo dentro de `post_automatic_entry` dentro de la transacción del llamante; cubrir con prueba.
- Alcance de UI en cuatro módulos: reutilizar el mismo componente; lo que no encaje se reporta como deuda, no se inventa.

## New dependencies
Ninguna.

## Changelog
- **v1** (2026-11-16): versión inicial.
- **v2** (2026-11-17): [Specification] INV-02, AC-04 y API-04: el mapeo de método de pago (rol `MONEY`) ya no exige tipo de cuenta Caja/Banco/Billetera; basta clasificación Activo, moneda BOB, cuenta activa y con código. Cambio **solicitado explícitamente por la persona en el chat** (el tipo de cuenta se retirará eventualmente). [Implementation Plan] sin cambios de pasos; se ajustan pruebas y textos de la UI.
- **v3** (2026-11-17): [Specification] la cuenta de gasto se configura **por categoría de Gastos** y no por clasificación de egreso: INV-02 (categoría), AC-03, EDGE-03, API-01 (`categories:[{category_id, account, issue}]`, solo las con cuenta) y API-03 (`categories/<category_id>/`, id opaco). La fachada recibe `category_id`/`category_label` en lugar de `classification_id`. [Implementation Plan] `ExpenseSettingsComponent` carga las categorías de Gastos y las entrega al panel; Contabilidad no importa Gastos. Cambio **solicitado explícitamente por la persona en el chat** (elegida la opción «por categoría de Gastos»).
- **v4** (2026-11-17): [Specification] cierra REV-05 con aprobación explícita de la persona ("arregla REV-05"): API-01 describe la forma real de la respuesta (`issues[]` con `subject`/`module`/`params`/`problem`, `preview[]` con `role` y `account{}`, `module_label`, `problem` en las filas) y API-02 el `problem` de los 400; AC-14 exige mostrar los avisos de faltantes, problemas de fila y errores 400 traducidos al idioma activo. [Implementation Plan] el backend devuelve causas estructuradas (`Problem`: código y parámetros, con el mensaje en español de respaldo) y el frontend las traduce (`posting-messages.ts`, claves `ACCOUNTING.POSTING.ISSUES/PROBLEMS/WHERE/MODULES`).
