# TASK-consultar-flujo-dinero-contabilidad: Consultar el detalle de flujo de dinero desde Contabilidad (CONT-14)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-consultar-flujo-dinero-contabilidad (base: `accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/103 (base `accounting`)
**Fuente:** https://trello.com/c/akzAhY3U/21-cont-14-consultar-el-detalle-de-flujo-de-dinero-desde-contabilidad

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-18 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-14 | delivery-start |
| 2026-11-18 | INVESTIGATION → DESIGN | Pantalla nueva y cambio en la tarjeta de Reportes | delivery-start |
| 2026-11-18 | DESIGN → PLANNING | DDR escrito; sin ADR (extiende módulo y fachada existentes) | delivery-start |
| 2026-11-18 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-11-18 | ENGINEERING → REVIEW | Implementación completa; pruebas de integración con BD sin ejecutar (sin credenciales) | delivery-build |
| 2026-11-18 | REVIEW (sin cambio) | Quality Gate 1 FAIL: REV-01/02/04 corregidos; REV-03 resuelto con enmienda aprobada de la Specification (PLAN v2) | delivery-publish |
| 2026-11-18 | REVIEW → PUBLISH | Quality Gate 2: PASS (REV-03 resuelto con PLAN v2) | delivery-publish |

## Investigación

### Requerimiento
Fuente: tarjeta Trello CONT-14 (insumo, no Specification aprobada). Aclaración del usuario: **usar la rama `accounting` como base**.

Historia: como usuario de Contabilidad, consultar saldos y movimientos de Caja y Bancos en una sola página para verificar los importes de la tarjeta «Flujo de dinero» y rastrearlos hasta el asiento.

Comportamiento pedido: página independiente **Contabilidad → Flujo de dinero**; la tarjeta de Reportes conserva su diseño y su enlace «Ver por cuenta» abre la página con el mismo período; resumen (saldo inicial, entradas, salidas, flujo neto, saldo final); desglose por cuenta (saldo inicial, entradas/salidas externas, transferencias recibidas/enviadas, saldo final) que al seleccionarse filtra el detalle; detalle con fecha contable, cuenta, concepto, documento de origen, importe y enlace al asiento, filtrable por período, cuenta y tipo (entrada, salida, transferencia); reutilizar la lógica de CONT-05 (cuentas de dinero, fecha contable, corte, reversiones), permisos y aislamiento por empresa.

Criterios de aceptación de la tarjeta: (1) acceso desde submenú y «Ver por cuenta» conservando período y coincidiendo con la tarjeta; (2) saldos inicial/final por cuenta = mayor contable y detalle respalda totales; (3) 0 + 2.477 − 1.750 → neto y final 727,00; (4) transferencia Caja→Banco de 500 aparece enviada/recibida y el consolidado no cambia; (5) desde un movimiento se abre el asiento. Dependencia: CONT-05.

### Hechos encontrados
- `backend/modules/accounting/domain/ledger_report.py:60-90` — `build_cash_flow`: por asiento, neto de sus líneas de dinero >0 entrada, <0 salida, =0 transferencia (no suma a entradas/salidas). `AccountFlow` solo tiene `opening`, `net`, `closing` (sin entradas/salidas/transferencias por cuenta).
- `backend/modules/accounting/application/ledger_report.py:56-77` — `GetLedgerReport.execute`: cuentas de dinero = `account_class == ASSET and kind is not None`; apertura desde `movements_by_account(..., since=cutoff)`; líneas desde `max(date_from, cutoff)`.
- `backend/modules/accounting/infrastructure/django/repositories.py:606-612` — `money_lines` agrega por `(entry_id, account_id)` por `accounting_date` en rango; no devuelve fecha, concepto ni origen.
- `backend/modules/accounting/infrastructure/django/models.py:198-265` — `JournalEntryModel` (`accounting_date`, `description`, `origin_kind`, `origin_id`, `reverses`) y `JournalLineModel`.
- `backend/modules/accounting/services.py:471-521` — fachada `get_ledger_report(company_id, date_from, date_to)`; Reporting la consume vía `backend/modules/reporting/infrastructure/adapters.py:74-88` (`/api/reports/ledger/`, `required_modules = ('reporting','accounting')`, `backend/modules/reporting/api/views.py:75`).
- `backend/modules/accounting/api/journal_serializers.py:45-59` — `_origin(kind, origin_id, enabled, detail)` produce el origen `{kind, available, label, module, id}`; `backend/modules/accounting/api/journal_views.py:57-90` lista paginada (`page_size` 20, máx. 100) con `required_modules = ('accounting',)`.
- `backend/config/permissions.py` — permiso por defecto `CompanyModulePermission` (admin de empresa + módulos requeridos, 403 `module_disabled`); `company_id_from(request)` da la empresa.
- `frontend/panel_admin/src/app/features/reporting/pages/reports/reports.component.html:39-72` — tarjeta «Flujo de dinero»; el «Ver por cuenta» actual es el `<summary>` de un `<details>` con tabla por cuenta (nombre, variación, saldo final, `data-testid="ledger-accounts-details"`).
- `reports.component.ts:45,87-93,120` — la selección de período (`PeriodSelection`) la resuelve el servidor; la respuesta trae `period.dateFrom/dateTo` efectivos.
- `frontend/panel_admin/src/app/app.routes.ts:129-160` — rutas `accounting/journal`, `accounting/balances`, etc. con `moduleGuard` y `data.module='accounting'`; `frontend/panel_admin/src/assets/data/routes.json:320-360` submenú Contabilidad (`adminOnly`); `sidebar-menu.spec.ts:64` lista las rutas esperadas.
- `frontend/panel_admin/src/app/features/accounting/models/journal.ts:132-136` — `journalOriginLink(origin)` (solo `PRODUCT` → pedido); detalle de asiento en `/pocketbiz/accounting/journal/:id`.
- `docs/design/design-system.md:166-172` — plantilla «Lista de solo lectura con filtros» (y variante compacta < 992 px); §6 describe los submenús de Contabilidad.
- Rama base: `origin/accounting` está 29 commits por delante de `main` (contiene CONT-05, PR 100–102); este task se crea desde ella.

### Hipótesis / supuestos no confirmados
- «Alcance» del reporte = período + cuentas de dinero configuradas (el reporte no tiene otros filtros). Si el producto añade filtros al reporte, el enlace deberá propagarlos.
- Un asiento mixto (neto ≠ 0 con líneas de dinero de signo opuesto, p. ej. cobro con una devolución simultánea a otra cuenta) es raro; se resuelve con la regla INV-04 del PLAN, sin cambiar totales consolidados.

### Módulos y dependencias relacionadas
`accounting` (dominio, aplicación, API, fachada), `reporting` (solo frontend: enlace de la tarjeta), módulos de origen (`sales`, `purchases`, `expenses`…) solo por el enlace del origen ya existente.

### Implementaciones similares existentes
Reporte CONT-05 (`GetLedgerReport`), libro de movimientos (`journal-list`, filtros + paginación + origen), saldos (`balances-page`), `inventory/movement-list` (lista de solo lectura con filtros y tarjetas compactas).

### Comportamiento actual
La tarjeta muestra totales y una tabla por cuenta con solo variación y saldo final; no hay forma de ver los movimientos que componen el flujo ni de separar transferencias por cuenta.

### Restricciones
Aislamiento por `company_id`; `Decimal` para dinero; el dominio no importa Django; módulos no se importan entre sí (accounting no importa reporting); i18n es/en/pt sin texto hardcodeado; sin nuevas dependencias.

### Riesgos identificados
- Divergencia entre la tarjeta y la página si cada una calcula por su cuenta → mitigación: ambas usan `GetLedgerReport`/`build_cash_flow`.
- Reglas de asientos mixtos y reversiones mal clasificadas → pruebas de dominio explícitas.
- Consultas lentas en rangos grandes → paginación en servidor y agregados en BD (índice `company_id, account` existente).

### Veredicto de complejidad
**NEEDS_PLAN** — extiende el módulo accounting y su fachada con dos endpoints de lectura y una pantalla, sin migraciones, módulos nuevos ni cambios de seguridad; hay lógica financiera (modo COMPLETO) pero sin decisión arquitectónica nueva.

### Diseño requerido
**SI** — pantalla nueva, cambio de la tarjeta de Reportes y nuevo submenú.

## Diseño
Ver `docs/design/DDR-consultar-flujo-dinero-contabilidad-pagina-flujo-de-dinero.md`.

## Arquitectura
No aplica según veredicto (sin ADR: se amplía `accounting` con la fachada y arquitectura de CONT-05; los endpoints viven en `accounting`, no en `reporting`, para que el submenú funcione con Contabilidad habilitada aunque Reportes no lo esté).

## Plan
`docs/plans/PLAN-2026-11-18-consultar-flujo-dinero-contabilidad.md` (v2, COMPLETO, READY; v2 enmendó con aprobación del usuario el requisito de paginación).

## Implementación
**Backend** (`accounting`): `domain/ledger_report.py` clasifica cada asiento (`classify_entry`, INV-02/INV-04) y `build_cash_flow` ahora devuelve por cuenta entradas, salidas y transferencias recibidas/enviadas (campos aditivos; INV-03); `application/cash_flow.py` (`ListCashFlowMovements`), `money_entries` en el repositorio, fachada `list_cash_flow_movements`, y vistas `GET /api/accounting/cash-flow/` y `/cash-flow/movements/` (`api/cash_flow_*.py`, API-01/02). El resumen reutiliza `GetLedgerReport`, por lo que coincide con la tarjeta (AC-01..AC-04, AC-06..AC-08).
**Frontend:** modelo, servicio y página `features/accounting/pages/cash-flow` (resumen, tabla de cuentas seleccionable, movimientos con enlace al asiento y origen, filtros en la URL, variante compacta con tarjetas), ruta `accounting/cash-flow` con `moduleGuard`, ítem de menú y claves es/en/pt; la tarjeta de Reportes reemplaza el `<details>` por el enlace «Ver por cuenta» con las fechas efectivas (AC-01, AC-05, UI-01..03). `design-system.md` §6 ya actualizado.
**Pantalla de referencia:** `journal-list` / `inventory/movement-list` (Lista de solo lectura con filtros); sin componentes nuevos compartidos.

**Desviaciones respecto al plan**
- La paginación de movimientos es en memoria sobre las partes ya clasificadas (la clasificación necesita todas las líneas del asiento); las líneas se agregan por (asiento, cuenta) en BD y las cabeceras se piden una sola vez. Deuda: si los rangos crecen mucho, mover la clasificación a SQL.
- La tabla de movimientos y la de cuentas son tablas Bootstrap simples (`table table-sm`) en vez de `ngx-datatable`, porque la paginación es del servidor y el volumen por página es 20; la variante compacta usa tarjetas y `ngb-pagination` como en el DDR.
- El desempate del reparto proporcional (INV-04) es por importe, luego nombre de cuenta, luego id.
- `build_cash_flow.transfers` pasa a ser Σ de transferencias recibidas (incluye la parte de transferencia de asientos mixtos); en asientos de neto 0 es idéntico al cálculo de CONT-05.

**Verificación propia (no es el Quality Gate):** pruebas de dominio del backend en verde (10); suite de Angular completa 1702/1702, `ng lint` y `ng build` sin errores, `npm run i18n:check` sin claves faltantes; ruff/flake8 sin avisos nuevos en lo cambiado. Las pruebas de integración con BD se ejecutaron después (ver Review): 497/497.

## Review
**Quality Gate 1: FAIL** (subagente aislado). No ejecutado: pruebas de integración con BD (sin `DATABASE_URL`) e inspección visual. Hallazgos:
- REV-01 (High, IMPLEMENTATION) aserciones de `count` erróneas en pruebas → corregido.
- REV-02 (Medium, IMPLEMENTATION) reparto de centavos de INV-04 podía dar un movimiento negativo → corregido (reparto de uno en uno) con prueba nueva.
- REV-03 (Medium, SPECIFICATION) la paginación en memoria contradice el requisito no funcional «paginación en BD» → resuelto: el usuario aprobó enmendar la Specification (PLAN v2).
- REV-04 (Low, IMPLEMENTATION) orden de desempate por cuenta y texto de `design-system.md` §6 → corregidos; el fallback HEX en el scss sigue igual que en `journal-list`.

**Revisión visual (2026-11-18, navegador integrado, backend sobre BD de prueba temporal ya eliminada con datos sembrados: 2.477,00 de entradas netas, 1.750,00 de salidas, transferencia de 500 Caja→Banco y una reversión):** verificada a 1440 px y 390 px, tema claro y oscuro. La tarjeta de Reportes enlaza «Ver por cuenta» con `date_from=2026-11-01&date_to=2026-11-30` y muestra neto 727,00; la página abre con el mismo período y el mismo resumen (saldo inicial 0,00, entradas 2.567,00, salidas 1.840,00, neto y final 727,00). Transferencia: «enviada» en Caja y «recibida» en Banco. Elegir Banco filtró los movimientos (3 de 3) con chip y totales del filtro; la reversión se ve con badge «Reversión». En 390 px: filtros plegados con chip del período, cuentas y movimientos como tarjetas, sin desbordamiento horizontal (scrollWidth = clientWidth). Tema oscuro legible, con badges con texto. No se probó con un usuario sin permiso ni el módulo deshabilitado en el navegador (cubiertos por pruebas de API). Nota: los acentos rotos del dato sembrado («UniÃ³n») venían del script de siembra, no de la app.

**Quality Gate 2: PASS** (subagente aislado, sobre el estado actual). Backend `manage.py test modules.accounting modules.reporting` con PostgreSQL: 497 OK; `manage.py check`, ruff, flake8 y bandit sin hallazgos. Frontend: `ng test` 1702/1702, `ng lint`, `ng build` e `i18n:check` (0 faltantes) OK. Sin hallazgos nuevos; REV-01..04 verificados como resueltos (REV-04 deja el fallback HEX del scss igual que `journal-list`, Low). No ejecutado: **inspección visual en navegador: ver «Revisión visual» abajo**, `npm audit` en la 2.ª pasada (la 1.ª reportó 2 vulnerabilidades moderadas en `hono`, transitiva y ajena al diff) y E2E (el plan dice NO).

## Publicación
PR #103 (base `accounting`) completo y listo para aprobación humana; no se mergea. Sin ADR. Sin cambios de autenticación, base de datos ni infraestructura (sin migraciones). Pendiente humano: aprobar el merge.
