# TASK-consultar-flujo-dinero-contabilidad: Consultar el detalle de flujo de dinero desde Contabilidad (CONT-14)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-consultar-flujo-dinero-contabilidad (base: `accounting`)
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/akzAhY3U/21-cont-14-consultar-el-detalle-de-flujo-de-dinero-desde-contabilidad

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-18 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-14 | delivery-start |
| 2026-11-18 | INVESTIGATION → DESIGN | Pantalla nueva y cambio en la tarjeta de Reportes | delivery-start |
| 2026-11-18 | DESIGN → PLANNING | DDR escrito; sin ADR (extiende módulo y fachada existentes) | delivery-start |
| 2026-11-18 | PLANNING → ENGINEERING | Specification READY | delivery-start |

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
`docs/plans/PLAN-2026-11-18-consultar-flujo-dinero-contabilidad.md` (v1, COMPLETO, READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
