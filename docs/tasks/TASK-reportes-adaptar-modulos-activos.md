# TASK-reportes-adaptar-modulos-activos: Adaptar dashboard y reportes a los módulos activos

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-reportes-adaptar-modulos-activos
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/41
**Fuente:** https://trello.com/c/WkIaIpdz/ (PB-REP-001)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado desde Trello PB-REP-001 | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN | NEEDS_ARCHITECTURE, diseño requerido | delivery-start |
| 2026-10-30 | DESIGN → ARCHITECTURE → PLANNING | DDR y ADR escritos | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY, PR abierto | delivery-start |
| 2026-10-30 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-10-30 | REVIEW → ENGINEERING | Quality Gate ciclo 1 FAIL (REV-01 High) | delivery-publish |
| 2026-10-30 | ENGINEERING → REVIEW | Corrección de REV-01, 02 y 04 | delivery-build |

## Investigación

### Requerimiento
Fuente: tarjeta Trello PB-REP-001 (Reportes, P1, dependencia PB-MOD-003). **Insumo, no Specification aprobada.**

> Como usuario, quiero ver indicadores disponibles para mi empresa sin depender de módulos deshabilitados.

- Dashboard y Reportes existentes; se adaptan tarjetas y secciones a las fuentes activas.
- Se conservan ventas, gastos, ganancia estimada, pedidos y pendientes cuando existan sus fuentes. Cada indicador muestra etiqueta, periodo y unidad (monetaria o cantidad).
- Fuente deshabilitada: «No disponible: módulo deshabilitado» donde haga falta explicar una ausencia. Módulo activo sin datos: cero o «Sin registros» según el indicador.
- Ganancia estimada: «Ventas menos gastos registrados; no incluye costo de producción ni costo de ventas». Si falta Ventas o Gastos, no se calcula. Compras y pagos a proveedores no se incorporan como gasto.
- Aceptación de interfaz: cambiar periodo conserva las definiciones del MVP; una fuente deshabilitada no provoca tarjetas rotas, errores de carga ni ganancia engañosa.
- Criterios: (1) Reportes usa solo fuentes activas, Ventas/Gastos ausentes = no disponibles, nunca cero; (2) se conserva ventas por fecha de pedido y ganancia = ventas − gastos cuando ambas están activas; (3) Compras, sus pagos y entradas de stock no se suman a Gastos ni a la ganancia.

**Aclaración del usuario (2026-10-30):** (a) Ventas y Gastos pasan a ser dependencias **opcionales** de Reportes; (b) Reportes puede quedar activo sin ninguna de las dos fuentes.

### Hechos encontrados
- `backend/modules/modularity/domain/modules.py:21-22` — Reportes **requiere** `sales` y `expenses`; `check_can_disable` (`:77-83`) impide apagarlas con Reportes activo. Hoy «fuente ausente» es inalcanzable.
- `backend/modules/modularity/tests/test_domain.py:26`, `test_api.py:75,89`, `test_settings_api.py:120` — pruebas que fijan o usan esa dependencia.
- `backend/modules/reporting/api/views.py:30,85` — `required_modules = ('reporting',)`; `top-customers` agrega `customers` (precedente de integración opcional con 403 `module_disabled`).
- `backend/config/permissions.py:27-37` — permiso por módulo, fail-closed; 403 `{code: module_disabled, module}`.
- `backend/modules/reporting/infrastructure/adapters.py:71-85` — `CustomerNamesAdapter` ya consulta `module_gate` (patrón a seguir); Reporting lee Sales/Expenses solo por `services.py`.
- `backend/modules/reporting/application/queries.py:156-181` — `GetDashboardSummary` siempre lee ambas fuentes; `estimated_profit = ventas − gastos`.
- `backend/modules/reporting/api/serializers.py:21-33` — contrato del dashboard con importes no nulos.
- `frontend/.../reporting/pages/dashboard/dashboard.component.html:21-84,97-167` — 6 tarjetas + pendientes; nota actual `ESTIMATE_NOTE` en `dashboard.component.ts:13` distinta del texto pedido.
- `frontend/.../reporting/pages/reports/reports.component.ts:46-49,51-55` y `.html:18-154` — solo Clientes se oculta; las demás tarjetas piden datos siempre; vacíos dicen «Sin datos para este periodo.».
- `frontend/.../core/interceptor/error.interceptor.ts:20-41` — un 403 `module_disabled` navega a «Módulo no habilitado» (REV-01 de PB-MOD-002): la UI no debe pedir datos de fuentes apagadas.
- `docs/design/DDR-bloquear-api-modulos-deshabilitados-integraciones-opcionales-ui.md:18` — regla: una pantalla no pide datos de una integración opcional deshabilitada.
- `backend/modules/modularity/domain/modules.py:23` — Compras requiere Gastos (sin cambio); las compras/pagos/entradas no crean gastos (`docs/producto/modulos-implementados.md:175`).

### Hipótesis / supuestos no confirmados
- PB-MOD-003 (ocultar tarjetas por módulo) se cubre aquí solo para Reportes/Dashboard; no hay documento accesible de esa historia (los enlaces de Google Docs de la tarjeta no se leyeron).
- Qué indicadores muestran «0» y cuáles «Sin registros» no está listado en la tarjeta: se decide en el DDR (totales y conteos = 0; listas, desgloses, rankings y ticket promedio = «Sin registros»).

### Módulos y dependencias relacionadas
`modularity` (catálogo), `reporting` (lectura), `sales`, `expenses`, `customers` (por fachadas), `purchases` (solo regresión: no entra a Gastos).

### Implementaciones similares existentes
Integración opcional de Clientes en Reporting/Ventas (ADR-bloquear-api-modulos-deshabilitados-permiso-por-modulo §6; DDR integraciones-opcionales-ui).

### Comportamiento actual
Dashboard y Reportes asumen Ventas y Gastos siempre activos; el catálogo lo garantiza.

### Restricciones
Dinero en `Decimal`/texto 2 decimales; aislamiento por `company_id`; Reporting solo lee; sin dependencias nuevas; sin migraciones (el catálogo vive en código).

### Riesgos identificados
- Contrato del dashboard cambia a campos anulables (consumidor único: el panel Angular, mismo PR).
- Empresas con Reportes activo y Ventas/Gastos desactivables por primera vez: sin migración de datos.
- Pruebas existentes que fijan `requires['reporting']`.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia la regla de dependencias del catálogo de módulos (impacto en `modularity`, `reporting`, pantalla de módulos) y el contrato API del dashboard.

### Diseño requerido
**SI** — estados nuevos («No disponible», «Sin registros») en Dashboard y Reportes.

## Diseño
Ver `docs/design/DDR-reportes-adaptar-modulos-activos-estados-de-fuente.md`.

## Arquitectura
Ver `docs/adr/ADR-reportes-adaptar-modulos-activos-fuentes-opcionales.md`.

## Plan
`docs/plans/PLAN-2026-10-30-reportes-adaptar-modulos-activos.md` (v1, COMPLETO, READY).

## Implementación
**Backend.** `modularity/domain/modules.py`: Reportes sin `requires`, con `optional` Ventas/Gastos/Clientes (AC-11, API-03). `reporting`: puerto `SourceAvailability` + `SourceAvailabilityAdapter` sobre `module_gate` (una consulta por petición), `GetDashboardSummary` que solo lee fuentes habilitadas y no calcula la ganancia si falta una (INV-02/03, AC-02..04), serializer con `sources` y nulos (API-01), `required_modules` por vista (API-02, AC-12).
**Frontend** (`features/reporting`): modelo/servicio con `sources` y campos anulables; `app-report-card` con `unavailable` y `UNAVAILABLE_MESSAGE`; dashboard con estado por tarjeta, periodo y unidad, nota de ganancia exacta, «Sin registros» y sin pedir pendientes con Ventas apagado (AC-02..08); reportes con tarjetas por fuente y sin peticiones a fuentes apagadas (AC-08, AC-09). Referencia seguida: plantilla «Dashboard y reportes» (`features/reporting`); componentes reutilizados: `app-report-card`, `app-period-selector`, pipe `money`.
**Docs:** `modulos-implementados.md`, `design-system.md` §5.
**Pruebas:** unit y API de Reporting y Modularity, specs de dashboard, reportes, tarjeta y servicio. AC-10 queda cubierto por `purchases/tests/test_payment_api.py:144-155` y `test_receipt_api.py:145-151` (pagar/recibir no crea gastos) y porque Reporting solo lee Gastos; no se añadió prueba nueva.

**Verificación propia (no es el Quality Gate):** backend `modules.modularity.tests.test_domain` y `modules.reporting.tests.{test_application,test_domain}` OK (37). **Las pruebas de API con base de datos (reporting `test_api`, modularity `test_api`/`test_enforcement`) NO se ejecutaron** por falta de `DATABASE_URL` en el worktree (no se lee `.env`). Frontend: specs de `features/reporting` 49/49 OK y `ng build` OK; la suite completa no corre por un error previo en `app.component.spec.ts` (deuda conocida).

**Desviaciones respecto al plan:** `top-customers` exige también `sales` (ya estaba en el ADR); «Gastos por categoría» y la tarjeta de clientes usan `ModulesService.isDisabled` además de `sources` del dashboard. Sin cambio de alcance.
**Deuda técnica:** `app.component.spec.ts` no compila (previo).

## Review
**Ciclo 1: FAIL.** REV-01 (High, IMPLEMENTATION): `test_settings_api` asumía que Reportes bloquea deshabilitar Ventas. Low: REV-02 (docs desactualizadas), REV-03 (fallo de carga de módulos sin spec), REV-04 (periodo del selector en Reportes), REV-05 (sin test de regresión de Compras en reporting; dos consultas de módulos por petición).
Corregidos en el ciclo 2: REV-01, REV-02, REV-04. REV-03 y REV-05 quedan abiertos como Low (limitaciones conocidas).
Detalle en `docs/reviews/REV-2026-10-30-reportes-adaptar-modulos-activos-0[1-5].md`.

## Publicación
_Pendiente_
