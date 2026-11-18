# TASK-adaptar-reportes-libro-partida-doble: Adaptar reportes al libro de partida doble sin duplicar compras y cobros (CONT-05)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-adaptar-reportes-libro-partida-doble (base: `task/TASK-revertir-asiento-al-anular-gasto`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/100 (base `accounting`)
**Fuente:** https://trello.com/c/r2KUm3GG/9-cont-05-adaptar-reportes-al-libro-de-partida-doble-sin-duplicar-compras-y-cobros

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-18 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-05 | delivery-start |
| 2026-11-18 | INVESTIGATION → DESIGN | Pantalla de Reportes afectada | delivery-start |
| 2026-11-18 | DESIGN → ARCHITECTURE | Nueva dependencia reporting → accounting y contrato API | delivery-start |
| 2026-11-18 | ARCHITECTURE → PLANNING | ADR y DDR escritos | delivery-start |
| 2026-11-18 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-11-18 | ENGINEERING → REVIEW | Implementación completa; integración con BD sin ejecutar | delivery-build |

## Investigación

### Requerimiento
Fuente: tarjeta Trello CONT-05 (insumo, no Specification aprobada). Aclaraciones del usuario: usar la rama `task/TASK-revertir-asiento-al-anular-gasto` como base y que el PR se mergee a `accounting`.

Objetivo de la tarjeta: reportes coherentes con el libro de partida doble que distingan flujo de dinero de resultado. Comportamiento esperado: revisar consumidores del contrato anterior (migrar o retirar consultas incompatibles; sin quinto submenú); flujo por variación de cuentas Caja/Banco configuradas, no por todos los débitos/créditos, y una transferencia entre cuentas propias no es ingreso, gasto ni flujo neto; resultado = Ingresos − Costos − Gastos, diferenciando reportes operativos de resultado contable y mostrando cobertura por corte; comprar inventario y pagar proveedor no son gasto, costo de ventas una vez (INV-01); cobrar deuda no reconoce ingreso otra vez; reversiones corrigen el concepto original según fecha contable; sin estados legales ni cierre automático. Pruebas de aceptación: (1) venta 150/costo 100 + cobro → ingreso 150, costo 100, margen 50; (2) compra 1.000 y pago 300 → salida 300 sin gasto; (3) transferir 200 Caja→Banco → flujo neto 0; (4) conciliar con libro, empresa, fechas y reversiones entre periodos. Dependencias: CONT-04, VEN-01, SRV-01, INV-01, COM-01, COM-02, GAS-01, GAS-02. Reglas: API y UI con aislamiento por empresa y permisos existentes; precisión decimal sin divisas; verificar el código real en `accounting`.

### Hechos encontrados
- `backend/modules/reporting/infrastructure/adapters.py` (1-113) solo conoce Sales, Expenses, Customers y módulos habilitados; no lee el libro.
- `backend/modules/sales/services.py:70` y `backend/modules/expenses/services.py:34`: ventas por pedido y gastos vigentes por fecha de gasto; ninguna es contable.
- `backend/modules/reporting/application/criteria.py`: texto de criterio de ventas («No equivale a lo cobrado»); `reporting/api/urls.py`: endpoints `dashboard, sales, expenses, sales-by-channel, top-products, top-customers, pending`.
- `backend/modules/accounting/services.py:459` `journal_balances` (Debe/Haber acumulado sin fechas); `infrastructure/django/repositories.py:572,581` totales y movimientos por rango (sumas y saldos, sin agrupar por asiento).
- Modelo del libro: `JournalEntryModel` (`accounting_date`, `origin_kind`, `reverses`) y `JournalLineModel` (`debit`/`credit`, una sola cara por línea) en `accounting/infrastructure/django/models.py:198,245`; cuentas con `account_class` y `kind` (`models.py:8-26`); los cuentas de dinero son Activo con `kind` (`domain/account.py:128`).
- Eventos y roles en `accounting/domain/posting.py:89-108`: `PURCHASE_RECOGNITION` (Inventario/Por pagar), `PURCHASE_PAYMENT` (Por pagar/Dinero), `SALE_DELIVERY` (Por cobrar/Ingresos), `SALE_PAYMENT` (Dinero/Por cobrar), `INVENTORY_SALE_COST` (Costo/Inventario), `EXPENSE_RECORD` (Gasto/Dinero).
- Corte/cobertura: `accounting/domain/coverage.py:52` `coverage_status`, `gaps`; el libro anterior al corte no suma (ADR modularidad-corte, TASK-diagnostico-transicion).
- `account_balances`/`journal_balances` no se usan fuera de Accounting (Grep); no hay consumidores de Reporting del libro anterior que migrar.
- Frontend: Reportes en `features/reporting/pages/reports/` (plantilla Dashboard y reportes, `docs/design/design-system.md:133`); el menú ya tiene Reportes y Contabilidad (`layout/sidebar/sidebar-menu.spec.ts`).
- Dependencias de la tarjeta: ramas `accounting` con CONT-04 y emisión de asientos ya mergeadas; GAS-02 en la rama base (`task/TASK-revertir-asiento-al-anular-gasto`).

### Hipótesis / supuestos no confirmados
- Billeteras (WALLET) cuentan como dinero junto a Caja/Banco (decisión del plan; la tarjeta solo dice Caja/Banco).
- Una moneda por empresa (sin conversión), según las reglas transversales.

### Módulos y dependencias relacionadas
Reporting (nuevo consumidor), Accounting (fachada nueva); Sales, Receivables, Inventory, Purchases, Expenses solo como emisores de asientos.
### Implementaciones similares existentes
Sumas y saldos (CONT-04) en `accounting/application/trial_balance.py` y API `balance_views.py`; patrón de fuentes opcionales de Reporting con `SourceAvailability`.
### Comportamiento actual
Reportes operativos (ver hechos); el libro no alimenta Reporting.
### Restricciones
`CLAUDE.md`: fachadas por `services.py`, `company_id` primero, `Decimal`, textos con `translate`, Reporting solo lee; no tocar `.env`; PR hacia `accounting`, no `main`.
### Riesgos identificados
Rendimiento por rango largo; cuentas de dinero sin `kind`; cifras operativas ≠ contables por diseño (se explica en criterios).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nueva dependencia entre bounded contexts, contrato API nuevo y lógica financiera con signos y transferencias.

### Diseño requerido
**SI** — se añade una sección a la pantalla de Reportes con estados y avisos de cobertura.

## Diseño
`docs/design/DDR-adaptar-reportes-libro-partida-doble-seccion-contable-en-reportes.md`.

## Arquitectura
`docs/adr/ADR-adaptar-reportes-libro-partida-doble-lectura-contable-en-reporting.md`.

## Plan
`docs/plans/PLAN-2026-11-18-adaptar-reportes-libro-partida-doble.md` (v1, COMPLETO, READY).

## Implementación
**Resumen.** Reportes lee el libro de asientos por una fachada nueva de Accounting y la expone en `GET /api/reports/ledger/` y en una sección «Libro contable» de `/pocketbiz/reports`.
- **Dominio** (`accounting/domain/ledger_report.py`): flujo por asiento (entrada / salida / transferencia, INV-R1), resultado por clase (INV-R2), cobertura (AC-05). Aplicación `accounting/application/ledger_report.py`; consulta `DjangoJournalRepository.money_lines`; fachada `accounting.services.get_ledger_report` (INV-R3..R5: solo lee el libro, por fecha contable y `company_id`; las reversiones son asientos con su propia fecha).
- **Reporting:** puerto `LedgerReader`, adaptador `LedgerReaderAdapter`, caso de uso `GetLedgerReport`, serializer y vista `LedgerReportView` (`required_modules = ('reporting', 'accounting')`); `LEDGER_CRITERIA`. Mapa de fronteras y `ddd.md` actualizados (AC-04).
- **Frontend:** modelo, `ReportingApiService.ledger`, recurso y bloque de dos tarjetas con aviso de cobertura, estados y «No disponible» (UI-01); etiqueta «Operativo» en ventas y gastos (UI-02, AC-06); claves es/en/pt. Pantalla de referencia: la propia de Reportes (plantilla Dashboard y reportes); reutiliza `app-period-selector`, `app-report-card` y el pipe `money`; sin componentes nuevos.
- **Cobertura de AC:** AC-01..05 en `accounting/tests/test_ledger_report.py` y `reporting/tests/test_ledger_api.py`; AC-05/06 y UI en los specs de `features/reporting`.

**Desviaciones respecto al plan.** (1) La respuesta usa snake_case como el resto de `/api/reports/*` (el plan decía camelCase); el servicio Angular la mapea a camelCase. (2) Con `accounting` deshabilitado la API responde 403 `{module}` como Gastos (patrón existente), no un estado de fuente. (3) El saldo inicial/final del flujo sale solo del libro de asientos (el `opening_balance` de cuenta del libro anterior no entra; coherente con el ADR).

**Verificación propia (no es el Quality Gate).** Ejecutado: pruebas unitarias del dominio (4 OK), `modules.sales.tests.test_boundaries` (8 OK), `ng test` de `features/reporting` (53 OK, ChromeHeadless), `npm run i18n:check` (0 faltantes), ruff/flake8 sin avisos en lo nuevo. **No ejecutado:** las pruebas de integración con PostgreSQL (`test_ledger_report.LedgerReportTests`, `test_ledger_api`) porque este entorno no tiene `DATABASE_URL` y no se leen credenciales; deben correrse en `delivery-publish`. ESLint del frontend no pudo ejecutarse (configuración incompatible del entorno).

**Deuda técnica.** Ninguna nueva.

## Review
_Pendiente_

## Publicación
_Pendiente_
