# TASK-periodos-fiscales-por-empresa: Crear y cerrar períodos fiscales por empresa (CONT-10)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-periodos-fiscales-por-empresa
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/82
**Fuente:** https://trello.com/c/tW9uE3gz/13-cont-10-crear-y-cerrar-per%C3%ADodos-fiscales-por-empresa

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-16 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-16 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Veredicto NEEDS_ARCHITECTURE, diseño SI; decisiones de negocio resueltas por la persona (reapertura, cobros actuales) | delivery-start |
| 2026-11-16 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |
| 2026-11-16 | ENGINEERING → REVIEW | Implementación completa; pruebas propias en verde | delivery-build |
| 2026-11-16 | REVIEW → PUBLISH | Quality Gate PASS | delivery-publish |

## Investigación

### Requerimiento
Tarjeta Trello CONT-10 (insumo, no Specification aprobada). Objetivo: administrar períodos fiscales desde Configuración.
- Nombre, inicio, fin y estado abierto/cerrado; inicio ≤ fin y períodos sin superposición por empresa.
- Todo asiento nuevo debe tener fecha en período abierto; misma regla para automáticos y reversiones.
- Bloquear cambios de límites que dejen asientos fuera de su período. Cerrar no genera asientos de cierre de resultados.
- Una reversión de un asiento de período cerrado se registra en un período abierto con fecha explícita; no altera el original.
- Serializar cierre y contabilización para impedir inserciones simultáneas en un período que acaba de cerrar.
- Pruebas de aceptación de la tarjeta: (1) rechazar fechas fuera de período, períodos solapados y registros en período cerrado; (2) mismos rangos permitidos en empresas distintas; (3) cierre concurrente con contabilización no deja un asiento insertado tras el cierre.
- Dependencia: CONT-07 (hecha). Reglas transversales: API y UI, aislamiento por empresa, permisos existentes, decimales/moneda existentes.

**Decisiones de la persona (2026-11-16):**
1. Un período cerrado **puede reabrirse**, solo por administrador (la API de negocio ya es solo admin; ver Restricciones).
2. Los cobros actuales (`record_entry`: Ventas/Servicios) **no** exigen período: la regla rige para los asientos del motor CONT-02.

### Hechos encontrados
- Contabilidad hoy es un libro de **entradas de una sola cuenta** (no hay asientos, líneas ni reversión): `backend/modules/accounting/domain/entry.py:59` (`Entry`, con `payment_date`), `infrastructure/django/models.py:43` (`EntryModel`, inmutable). El motor de partida doble es CONT-02 (por hacer), que depende de períodos: su cabecera lleva «período» y valida «período abierto».
- No existe ningún concepto de período fiscal en el código (búsqueda de `período fiscal|FiscalPeriod|journal`: sin resultados fuera de iconos).
- Fachada pública `backend/modules/accounting/services.py:88` (`record_entry`) exige transacción abierta (`connection.in_atomic_block`) y lanza `EntryContractError`; patrón a seguir para el contrato de períodos.
- Aislamiento por empresa: repositorios `Django…Repository(company_id)` (`infrastructure/django/repositories.py:23`); bloqueo por empresa con `select_for_update` sobre cuentas (`repositories.py:87`) y bloqueo advisory por empresa con namespace en `infrastructure/adapters.py:49`.
- Vistas de configuración: `_ConfigView` con `required_modules = ()` (`api/views.py:101`) para configurar sin tener Contabilidad habilitada; errores de negocio como 409 con `code` (`api/views.py:61`). Rutas en `api/urls.py:16`.
- Permiso por defecto de la API: `CompanyModulePermission` → `CompanyAdminPermission` (rol `ADMIN`, empresa activa): `config/permissions.py`, `modules/accounts/api/permissions.py:11`. Un `createsuperuser` sin empresa recibe 403 en la API de negocio.
- Frontend: configuración de Contabilidad en `features/accounting/pages/accounting-settings` con pestañas Cuentas / Métodos (`accounting-settings.component.ts:7`), ruta `accounting/settings` (`app.routes.ts:105`); servicios API en `features/accounting/services/`.
- Migraciones accounting: 0001, 0002, 0003 (`backend/modules/accounting/migrations/`). Las tarjetas CONT-08/09 (clasificaciones, cuentas con código) viven en otras ramas y pueden añadir migraciones: la numeración de la nueva puede requerir ajuste al integrar.
- Pruebas de concurrencia reutilizables: `tests/test_concurrency.py::_run_together`, `tests/test_entry_concurrency.py`.

### Hipótesis / supuestos no confirmados
- «Asientos fuera de su período» se evalúa por **fecha contable**: un cambio de límites es inválido si algún asiento hoy dentro del período quedaría fuera del nuevo rango. Como aún no hay asientos, se define un puerto de uso y CONT-02 aporta el adaptador real.
- Un período cerrado no se edita (ni nombre ni límites); hay que reabrirlo. No se pide eliminar períodos; no se incluye.

### Módulos y dependencias relacionadas
`accounting` (nuevo agregado `FiscalPeriod`). Consumidores futuros: CONT-02 (motor de asientos, vía `accounting.services`), CONT-11 (menú Configuración → Períodos fiscales), CONT-12. Sin dependencias nuevas entre módulos.

### Implementaciones similares existentes
Cuentas (`Account`, `CreateAccount`/`UpdateAccount`, `AccountConflict`) y su pestaña/diálogo (`accounts-tab`, `account-dialog`, `deactivate-dialog`).

### Comportamiento actual
No hay períodos; ninguna fecha se valida contra períodos.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, dominio sin Django, módulos sin importarse infraestructura, nunca editar migraciones aplicadas, i18n es/en/pt, sin dependencias nuevas sin aviso.

### Riesgos identificados
- Carrera cierre/contabilización y creación simultánea de períodos solapados (mitigado en el ADR).
- Colisión de numeración de migraciones con otras ramas de accounting.
- Que el puerto de «uso del período» quede sin adaptador real hasta CONT-02 (declarado en Out of scope).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nueva tabla y migración, contrato de concurrencia que consumirá otro módulo-épica (CONT-02) y serialización con bloqueos en base de datos.

### Diseño requerido
**SI** — pestaña nueva con listado, diálogos y acciones de cierre/reapertura.

## Diseño
`docs/design/DDR-periodos-fiscales-por-empresa-pestana-periodos-fiscales.md`

## Arquitectura
`docs/adr/ADR-periodos-fiscales-por-empresa-agregado-y-bloqueo.md`

## Plan
`docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
Implementado según PLAN v1 (sin cambios de Specification ni de plan).

- **Dominio** `accounting/domain/fiscal_period.py`: agregado `FiscalPeriod` (INV-01..05), errores y excepciones del contrato (`DateOutsideFiscalPeriod`, `FiscalPeriodClosed`, `FiscalPeriodContractError`).
- **Infraestructura**: `FiscalPeriodModel` + migración `0004_fiscal_period` (checks de fechas y estado, único `(company_id, lower(name))`, índice); `DjangoFiscalPeriodRepository` con bloqueo advisory por empresa y `FOR UPDATE` (INV-03, INV-08); `NoJournalPeriodUsage` (puerto `PeriodUsage`, AC-08).
- **Aplicación** `application/fiscal_periods.py`: crear, editar (solapamiento + puerto de uso), cerrar, reabrir, listar, obtener (AC-01..05, AC-08, INV-07).
- **Fachada** `services.py`: `lock_open_period`, `period_for`, `PeriodRef` (AC-06, AC-07, INV-08).
- **API** `/api/accounting/fiscal-periods/` (API-01..05) con el permiso por defecto (admin de empresa): cerrar y reabrir solo administradores.
- **Frontend** (AC-10, UI-01/02): tercera pestaña «Períodos fiscales» en `accounting-settings` (plantilla «Configuración con listados en pestañas y diálogo», referencia `accounts-tab`/`account-dialog`/`deactivate-dialog`), `periods-tab`, `period-dialog`, `period-status-dialog`, servicio y modelo, claves i18n es/en/pt (`ACCOUNTING.FISCAL_PERIODS`). Sin componentes compartidos nuevos.
- **Docs**: nota en `docs/architecture/ddd.md`.

**Desviaciones:** ninguna de alcance. Detalles: la lista del repositorio se llama `all()` (no `list()`, que sombrea el builtin en la clase); `FiscalPeriod.create` valida el nombre con `validate_name` de cuentas, por lo que ese error es `AccountValidationError` (superclase de `FiscalPeriodValidationError`) y la API lo traduce igual a 400.

**Pruebas añadidas:** `test_fiscal_period_domain`, `test_fiscal_periods_api`, `test_fiscal_period_facade`, `test_fiscal_period_concurrency` (backend); specs del servicio, pestaña, diálogos y ajuste del spec de pestañas (3 pestañas) en el frontend.

**Corridas propias (no son el Quality Gate):** backend `manage.py test` 1678 OK, `makemigrations --check` sin cambios; frontend `ng test` 1430 OK, `ng lint` limpio, `i18n:check` 0 faltantes, `ng build` OK.

**Deuda / pendiente para CONT-02:** cablear el adaptador real de `PeriodUsage` (hoy `NoJournalPeriodUsage` devuelve 0) y probar AC-08/AC-09 con asientos reales; renumerar la migración si otra rama de accounting ya usó `0004`.

## Review
**Quality Gate: PASS** (subagente aislado, 2026-11-16). Sin hallazgos Critical/High.
- Backend: `manage.py test modules.accounting` 120 OK; suite completa 1678 OK; `makemigrations --check` sin cambios; bandit sin hallazgos; ruff/flake8 solo estilo (sin configuración de lint en el repo); mypy no concluyente (`import-untyped`).
- Frontend: `ng test` 1430 OK (con cobertura: líneas 88,35 %, ramas 77,89 %); en una de tres corridas falló `screens-i18n.spec.ts:58-65` (flake preexistente por orden aleatorio, ajeno al diff); `ng lint` limpio; `i18n:check` 0 faltantes; `ng build` OK; `npm audit`: 2 moderadas transitivas (hono), ajenas al cambio.
- DDD/aislamiento: dominio sin Django, consultas filtradas por `company_id`, sin importar `accounts`.
- Conformidad: AC-01..AC-10, INV y API verificados; AC-08/AC-09 con asientos reales quedan para CONT-02 (declarado).
- Visual: checklist §8 revisada sobre el código; **verificación en navegador no realizada**.
- Hallazgos abiertos no bloqueantes: REV-2026-11-16-periodos-fiscales-por-empresa-01 a -09 (Medium: 01 prueba de concurrencia con `sleep`, 02 prueba de 403 por rol; el resto Low).

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/82 listo para aprobación humana (no se mergea). Cambio con migración de base de datos (ADR `ADR-periodos-fiscales-por-empresa-agregado-y-bloqueo`): requiere aprobación explícita de una persona.
