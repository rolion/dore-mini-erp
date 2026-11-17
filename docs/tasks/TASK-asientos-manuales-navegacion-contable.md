# TASK-asientos-manuales-navegacion-contable: Simplificar navegación contable y registrar/consultar asientos manuales (CONT-11)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-asientos-manuales-navegacion-contable
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/84
**Fuente:** https://trello.com/c/WvLdLyky/14-cont-11-simplificar-navegaci%C3%B3n-y-registrar-consultar-asientos-manuales

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-17 | (nuevo) → INVESTIGATION | Task creado; base = rama `accounting` (`origin/accounting`, PR #83 ya integrado), no `main` | delivery-start |
| 2026-11-17 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN, diseño SI; 3 decisiones de negocio resueltas por la persona | delivery-start |
| 2026-11-17 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |
| 2026-11-17 | ENGINEERING → REVIEW | Implementación completa; pruebas propias en verde | delivery-build |

## Investigación

### Requerimiento
Tarjeta Trello CONT-11 (insumo, no Specification aprobada). Aclaración de la tarjeta: trabajar sobre `accounting`; lo terminado allí no está en `main`.
- Cuatro submenús contables: **Cuentas, Movimientos, Saldos, Configuración**. Configuración contiene Clasificaciones y Períodos fiscales; la configuración de automatismos queda en el módulo de origen.
- **Movimientos**: lista paginada por fecha contable desc, desempate por creación e ID desc; filtros de fechas, cuenta y origen.
- **Formulario** (fecha y descripción obligatorias; tabla Cuenta/Debe/Haber; dos filas iniciales; agregar/eliminar). Muestra Total Debe, Total Haber y Diferencia; no se confirma con diferencia ≠ 0 ni validaciones pendientes; la API valida igual.
- **Detalle**: líneas, origen, usuario y reversión vinculada. Un confirmado no se edita ni borra. Confirmación de reversión con fecha y motivo (CONT-02).
- Aceptación: (1) servicio 500 = Caja Debe 200, Banco Debe 300, Ingresos servicios Haber 500; (2) diferencia 0 confirma, diferencia 1 no guarda y no deja escrituras parciales; (3) paginación estable con fechas iguales, filtros preservados, otra empresa no ve el asiento; (4) un automático lleva a su origen sin permitir editar sus líneas.
- Dependencias CONT-02, CONT-09, CONT-10 (hechas en `accounting`). Transversal: aislamiento por empresa, permisos existentes, decimales y moneda existentes, sin conversión de divisas.

### Hechos encontrados
- El motor existe sin API HTTP ni UI: fachada `backend/modules/accounting/services.py` (`post_journal_entry`, `reverse_journal_entry`, `get_journal_entry`; exigen transacción abierta). Dominio `domain/journal.py` (`JournalEntry.post/reverse`, ≥2 cuentas distintas, Σ Debe = Σ Haber > 0, moneda derivada de las cuentas); casos de uso `application/journal.py`; modelos `JournalEntryModel`/`JournalLineModel` (`infrastructure/django/models.py:198-265`) con orden `['-accounting_date','-created_at','-id']` (`models.py:224`) y índice `(company_id, accounting_date)`.
- **No hay consulta de listado** del libro de asientos: `DjangoJournalRepository` solo tiene `get`, `get_by_origin`, `reversal_of`, `totals_by_account`, `count_outside` (`repositories.py:475-550`). Hay que añadir `list` con filtros y paginación.
- `api/urls.py:18-58`: `entries/` y `entries/<id>/` son el libro **anterior** (una cuenta por fila, `EntryModel`); no hay rutas de asientos. Convención de vistas: `required_modules = ('accounting',)`, `company_id_from(request)`, `_run` convierte errores de dominio (`api/views.py:119`); paginación `EntryPagination` (`views.py:367`), 409 con `Conflict` (`views.py:95`).
- Errores del motor: `JournalValidationError(errors)` (campo → mensajes, p. ej. `lines`), `JournalConflict`, `JournalEntryNotFound` (`domain/journal.py:26-45`); fechas fuera de período → `DateOutsideFiscalPeriod`, `FiscalPeriodClosed` (`services.py:296-311`).
- Enlace al origen en el libro anterior: `ORIGIN_MODULES` + `source.available` (`api/serializers.py:117-146`); el vocabulario `origin_kind` del nuevo motor aún no lo definen los módulos (TASK-motor-central…, «Hipótesis»).
- Frontend: rutas `accounting/settings`, `accounting/entries`, `accounting/entries/:id`, `accounting/regularization` (`app.routes.ts:104-124`); menú en `assets/data/routes.json:308-352` (3 submenús; prueba `layout/sidebar/sidebar-menu.spec.ts:56-61` fija sus rutas); `accounting-settings` tiene 7 pestañas (Cuentas, Métodos de pago, Clasificaciones, Clasificaciones contables, Egresos, Corte y cobertura, Períodos fiscales) con `onTabKeydown`; sus componentes `app-accounts-tab`, `app-account-classes-tab`, `app-periods-tab`, etc. son reutilizables. Servicios `entries-api.service.ts` (libro anterior), `accounting-api.service.ts`.
- Plantillas de diseño aplicables (`docs/design/design-system.md` §5): «Lista de solo lectura con filtros» (l.159), «Formulario con líneas y paso de resumen» (l.148) y «variante de un solo paso con totales calculados» (l.155), «Diálogo de acción irreversible con motivo» (l.198), detalle con reversión (l.198-202). Menú: §6 (l.203).
- Acceso: ítem `adminOnly` con `module: accounting`; permisos de API por `CompanyModulePermission` (`config/settings/base.py:97`).

### Hipótesis / supuestos no confirmados
- «Origen» (filtro) = `source` MANUAL/AUTOMATIC más, opcionalmente, `origin_kind`.
- Un asiento manual no lleva clave de idempotencia (no tiene origen); el doble envío se evita deshabilitando el botón; riesgo residual aceptado (ver PLAN).
- El enlace al origen de un asiento automático solo se ofrece si el módulo propietario está habilitado y el tipo es conocido; hoy no hay automáticos reales porque los módulos aún no migran (VEN-01…).
- La fecha de reversión se propone como hoy y debe caer en un período abierto.

### Decisiones de negocio resueltas por la persona (2026-11-17)
1. **Pantallas actuales**: conservar sin submenú propio. Métodos de pago, Egresos, Corte y cobertura, Entradas (libro anterior) y Regularizar siguen operativas por URL y con enlaces desde Configuración/Movimientos hasta CONT-12/13.
2. **Saldos**: pantalla «Próximamente» (sin lógica; saldos reales son CONT-04/05).
3. **Clasificaciones** de Configuración = las seis clasificaciones contables (CONT-08). Las categorías de ingreso/egreso quedan con los automatismos.

### Módulos y dependencias relacionadas
Solo `accounting` (API + repositorio de lectura) y frontend `features/accounting`. Sin dependencias nuevas entre módulos ni de paquetes.

### Comportamiento actual
Existe el motor pero no hay forma de ver ni registrar asientos desde la web; Contabilidad muestra el libro de entradas anterior.

### Restricciones
`CLAUDE.md`: dinero `Decimal`, aislamiento por `company_id`, dominio sin Django, serializers validan forma, sin texto hardcodeado (claves es/en/pt), sin `any`, Reactive Forms, sin suscripciones colgadas, nunca editar migraciones aplicadas (no se prevé migración).

### Riesgos identificados
- Doble envío del formulario manual crea dos asientos idénticos (sin origen no hay idempotencia).
- Romper el acceso a configuraciones existentes al reorganizar el menú.
- Paginación inestable si el orden no es total (mitigado: `-accounting_date, -created_at, -id`).
- Una lista grande por cuenta: el filtro por cuenta requiere subconsulta sobre líneas (índice `(company_id, account)` existe).

### Veredicto de complejidad
**NEEDS_PLAN** — API nueva y pantallas nuevas, pero sin migración, sin módulos nuevos ni decisión arquitectónica: reutiliza el motor, los patrones de vistas y el sistema de diseño.

### Diseño requerido
**SI** — pantallas nuevas (lista, formulario con totales, detalle, diálogo de reversión, Saldos, Configuración) y cambio de navegación.

## Diseño
`docs/design/DDR-asientos-manuales-navegacion-contable-pantallas.md`

## Arquitectura
No aplica según veredicto (sin ADR; el contrato del motor es el de CONT-02).

## Plan
`docs/plans/PLAN-2026-11-17-asientos-manuales-navegacion-contable.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
Implementado según PLAN v1 (sin cambios de Specification).

- **Backend** (`accounting`): `DjangoJournalRepository.search` + `JournalFilters` (orden total `-accounting_date,-created_at,-id`, `EXISTS` por cuenta, aislado por empresa; INV-04/05, AC-03/04); `api/journal_serializers.py` y `api/journal_views.py` con API-01..04 (lista paginada, alta manual atómica por `post_journal_entry`, detalle, reversión por `reverse_journal_entry`; 400 por campo, 404 ajeno, 405 en PUT/PATCH/DELETE; INV-06, AC-01/02/05/06/07); rutas `journal-entries/`. Sin migración.
- **Frontend** (`features/accounting`): `models/journal.ts` (aritmética en centavos, bloqueos de confirmación, mapeo de errores), `journal-api.service.ts`, `journal-filters-state.ts`; páginas Movimientos (lista), Nuevo asiento (formulario con Total Debe/Haber/Diferencia), detalle con bloque Reversión, diálogo de reversión, Cuentas, Saldos «Próximamente» y Configuración (Clasificaciones contables + Períodos fiscales); la pantalla anterior pasa a `/accounting/settings/legacy` (Métodos de pago, Clasificaciones de ingreso/egreso, Egresos, Corte y cobertura). Menú: Cuentas, Movimientos, Saldos, Configuración (AC-08, AC-09, UI-01..06). Enlaces de `classification-hint`, diálogo de módulos y cobertura del libro apuntan a las nuevas rutas. i18n es/en/pt (AC-10).
- **Pantallas de referencia:** «Lista de solo lectura con filtros» (`movement-list`/`entry-list`), «Formulario con líneas… variante de un solo paso con totales calculados» (`purchase-form`), Detalle y «Diálogo de acción irreversible con motivo» (`movement-reverse-dialog`); reutiliza `AccountsTabComponent`, `AccountClassesTabComponent`, `PeriodsTabComponent`.

**Desviaciones:** (1) el selector de cuenta es un `select` nativo (como el filtro de `entry-list`), no `ng-select`. (2) `Entradas` y `Regularizar` siguen accesibles por URL; la lista de Movimientos enlaza a Entradas con una nota, y Configuración enlaza a «Otras configuraciones»; `Regularizar` solo por URL directa (sin enlace nuevo). (3) El filtro «origen» usa `source` (Manual/Automático); `origin_kind` queda disponible en la API pero sin control en la UI.

**Pruebas añadidas:** backend `test_journal_api` (18); frontend `journal.spec`, `journal-api.service.spec`, specs de lista, formulario, detalle, diálogo, Configuración y Configuración heredada; `sidebar-menu.spec` actualizado. Corridas propias (no son el Quality Gate): `accounting` 309 OK, `makemigrations --check` sin cambios; frontend lint OK, `ng build` OK, `i18n:check` 0 faltantes, specs de accounting/layout/settings/shared en verde.

**Deuda / pendiente:** idempotencia de asientos manuales (doble envío solo mitigado en UI); retirar la pantalla heredada con CONT-12/13; definir el vocabulario `origin_kind` de los módulos para los enlaces a origen; actualizar `design-system.md` §6 (submenú de Contabilidad) — hecho en este PR.

## Review
_Pendiente_

## Publicación
_Pendiente_
