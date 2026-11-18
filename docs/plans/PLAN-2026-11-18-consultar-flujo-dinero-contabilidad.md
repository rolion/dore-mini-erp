# PLAN-2026-11-18-consultar-flujo-dinero-contabilidad (v2)

**Task:** TASK-consultar-flujo-dinero-contabilidad · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-consultar-flujo-dinero-contabilidad-pagina-flujo-de-dinero · Ninguno

## Objective
Dar a Contabilidad una página «Flujo de dinero» con el resumen del período, el desglose por cuenta de dinero y el detalle de movimientos hasta el asiento, calculados con la misma lógica de CONT-05 que la tarjeta de Reportes, y conectar la tarjeta mediante «Ver por cuenta».

## Context
Ver `docs/tasks/TASK-consultar-flujo-dinero-contabilidad.md`. Base: rama `accounting`.

# Specification

## Domain context
Bounded context `accounting` (libro de partida doble). `reporting` solo cambia en frontend (enlace de la tarjeta).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Cuenta de dinero | Cuenta de clase Activo con `kind` configurado (Caja, Banco, Billetera) | `application/ledger_report.py:56` |
| Entrada / Salida | Asiento cuyo neto de líneas de dinero es > 0 / < 0 (flujo externo) | `domain/ledger_report.py:1-5` |
| Transferencia | Movimiento entre cuentas propias: neto 0 en el asiento; no suma a entradas ni salidas | `domain/ledger_report.py:1-5` |
| Fecha contable | `JournalEntry.accounting_date` | `models.py:203` |
| Corte | Fecha desde la que el libro es fuente; anterior = cobertura parcial | `domain/ledger_report.py:90` |

## Current behavior
Ver TASK → Comportamiento actual. `AccountFlow` solo tiene apertura, neto y cierre (`domain/ledger_report.py:34-39`).

## Expected behavior
1. **Resumen:** para `[date_from, date_to]` devuelve saldo inicial, entradas, salidas, flujo neto (= entradas − salidas), saldo final, transferencias (informativo) y cobertura, idénticos a `get_ledger_report` para el mismo rango.
2. **Por cuenta de dinero:** saldo inicial, entradas externas, salidas externas, transferencias recibidas, transferencias enviadas, neto y saldo final (= inicial + neto).
3. **Movimientos:** una fila por (asiento, cuenta de dinero, clase de movimiento) con fecha contable, cuenta, concepto del asiento, origen (como en el libro), importe, tipo, `entry_id` e indicador de reversión; filtrables por rango, cuenta y tipo; paginados; con totales del filtro.
4. **Pantalla** `/pocketbiz/accounting/cash-flow` y enlace «Ver por cuenta» desde la tarjeta conservando período (DDR).

## Domain rules / invariants
- **INV-01 (existente)** Cuentas de dinero, fecha contable, corte y reversiones como CONT-05: una reversión cuenta en su propia fecha contable con las líneas invertidas (sale como movimiento normal, marcado «Reversión»). Las líneas anteriores al corte no se incluyen (`start = max(date_from, cutoff)`).
- **INV-02 (existente)** Entrada/salida/transferencia se decide por el neto del asiento sobre sus líneas de dinero.
- **INV-03 (nueva)** Por cuenta: `closing = opening + net`; `net = inflow − outflow + transfers_in − transfers_out`. Σ de `inflow` de cuentas = entradas consolidadas; Σ `outflow` = salidas consolidadas; Σ `transfers_in` = Σ `transfers_out` = transferencias del consolidado.
- **INV-04 (nueva, asiento mixto)** En un asiento con neto ≠ 0 y líneas de dinero de ambos signos, la parte de transferencia `T = min(Σ positivas, Σ |negativas|)` se reparte como recibida (líneas positivas) y enviada (líneas negativas), y el resto `|neto|` es entrada (neto > 0) o salida (neto < 0). El reparto entre líneas del mismo signo es proporcional a su importe, con el resto de centavos a la línea mayor (desempate: nombre de cuenta, luego id). Un asiento con neto 0 es transferencia pura; uno con todas sus líneas de dinero del mismo signo es entrada o salida pura.
- **INV-05** Todo es de la empresa del usuario (`company_id` del token); la cuenta filtrada debe ser una cuenta de dinero de esa empresa.
- **INV-06** Dinero en `Decimal` y serializado como texto con dos decimales.

## Acceptance criteria
- **AC-01** El submenú «Flujo de dinero» y el enlace «Ver por cuenta» de la tarjeta abren la página; desde la tarjeta se conservan las fechas efectivas del período y el resumen coincide con los importes de la tarjeta.
- **AC-02** Saldo inicial y final por cuenta coinciden con el mayor (`journal_balances`/saldos) al inicio y fin del rango (respetando el corte); Σ de movimientos por tipo = entradas, salidas y transferencias del resumen para el mismo rango y cuenta(s).
- **AC-03** Con saldo inicial 0,00, entradas 2.477,00 y salidas 1.750,00: flujo neto y saldo final = 727,00.
- **AC-04** Una transferencia de 500 Caja → Banco aparece como «enviada» en Caja y «recibida» en Banco; entradas, salidas y flujo neto consolidados no cambian.
- **AC-05** Cada movimiento trae `entry_id` y la pantalla enlaza a `/pocketbiz/accounting/journal/:id`; el origen enlaza solo si está disponible.
- **AC-06** Filtros: por cuenta (seleccionándola en la tabla), tipo (`inflow`, `outflow`, `transfer`) y rango; combinables; cuenta ajena o no de dinero → 400.
- **AC-07** Reversión: el asiento de reversión de un cobro aparece como salida en su fecha contable con la marca de reversión; el original sigue como entrada.
- **AC-08** Otra empresa no ve datos de esta; módulo `accounting` deshabilitado → 403 `module_disabled`; no admin → 403.

## Edge cases / Error cases
- Rango sin movimientos: totales 0 y lista vacía. Rango invertido o fecha mal formada: 400 por parámetro. Faltan `date_from`/`date_to`: 400.
- Sin cuentas de dinero: resumen en 0, lista de cuentas vacía (la pantalla lo explica).
- Rango anterior al corte o parcialmente anterior: `coverage.partial = true` y aviso; no se incluyen líneas anteriores al corte.
- Cuenta de dinero desactivada con movimientos: aparece si tiene saldo o movimientos del rango (misma lista que el reporte: `accounts.list()`).
- Asientos del mismo día: orden estable (fecha contable ↓, `created_at` ↓, id ↓, cuenta).

## Authorization / permissions
Permiso por defecto (`CompanyModulePermission`: admin de empresa) y `required_modules = ('accounting',)`. Menú `adminOnly` con `moduleGuard`.

## API contract
- **API-01** `GET /api/accounting/cash-flow/?date_from=AAAA-MM-DD&date_to=AAAA-MM-DD` →
  `{period:{date_from,date_to}, coverage:{cutoff_date, partial}, summary:{opening, inflow, outflow, net, closing, transfers}, accounts:[{account_id, name, opening, inflow, outflow, transfers_in, transfers_out, net, closing}]}`.
- **API-02** `GET /api/accounting/cash-flow/movements/?date_from&date_to&account_id&type&page&page_size` →
  paginado estándar (`count`, `next`, `previous`, `results`) más `totals:{inflow, outflow, transfers_in, transfers_out}` del filtro; cada resultado: `{entry_id, accounting_date, account:{id,name}, description, origin:{kind,available,label?,module?,id}|null, kind:'inflow'|'outflow'|'transfer_in'|'transfer_out', amount, is_reversal}`. `type` ∈ `inflow|outflow|transfer` (transfer = recibida y enviada).
- Compatible hacia atrás: `/api/reports/ledger/` no cambia.

## UI behavior
- **UI-01** Pantalla y submenú según el DDR (plantilla «Lista de solo lectura con filtros» + resumen en `card`); ruta `/pocketbiz/accounting/cash-flow` con `moduleGuard` y `data.module = 'accounting'`.
- **UI-02** La tarjeta de Reportes reemplaza el `<details>` por el enlace «Ver por cuenta» con `date_from`/`date_to` efectivos; el resto no cambia.
- **UI-03** Variante compacta < 992 px, estados §4, textos `translate` en es/en/pt, filtros en la URL (`date_from`, `date_to`, `account`, `type`) para que el enlace y «volver» conserven el contexto.

## Non-functional requirements
Las líneas de dinero se agregan por (asiento, cuenta) en la base de datos y la clasificación y la paginación de movimientos se hacen en memoria sobre ese resultado (enmienda v2, aprobada por el usuario; si los rangos crecen, mover la clasificación a SQL); pruebas de aislamiento por empresa; accesibilidad mínima §7 (botón de cuenta con `aria-pressed`, badges con texto, no solo color).

## Out of scope
Exportación, gráficos, edición de asientos desde la página, cambiar el cálculo de CONT-05, el selector hoy/semana/mes en la página, nuevos filtros del reporte, cambios de migración.

## Open questions
- (No bloquea) Si el producto quiere conservar la tabla por cuenta dentro de la tarjeta además del enlace.

# Test Specification

## Unit tests
- Dominio `build_cash_flow` extendido y `build_cash_flow_movements`: entrada pura, salida pura, transferencia 500 (Caja→Banco), asiento mixto (INV-04), reparto con redondeo, reversión, invariantes INV-03.

## Integration tests
- Fachada/API con asientos reales (`post_journal_entry`, automáticos, `reverse_journal_entry`): AC-02..AC-08, paridad `summary` = `get_ledger_report`, corte/cobertura, filtros, paginación, fuga entre empresas, módulo deshabilitado, no admin, parámetros inválidos.
- Frontend: servicio API (mapeo snake→camel), página (resumen, selección de cuenta que filtra, tipo, estados cargando/error/vacío, enlace al asiento, compacta), tarjeta de Reportes (enlace con fechas), menú/rutas, claves i18n (`npm run i18n:check`, prueba de claves es/en/pt).

## E2E
**NO** — el flujo se cubre con integración backend y pruebas de componente; no es crítico de punta a punta ni justifica instalar Playwright.

## Regression tests
`test_ledger_report`, `test_ledger_api` y las pruebas de la tarjeta de Reportes se mantienen en verde (ajustando solo lo del «Ver por cuenta»).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Componente: enlace y ruta/menú; spec de reports (fechas efectivas); paridad resumen = `get_ledger_report` |
| AC-02 | Integración: saldos por cuenta vs `journal_balances`; Σ movimientos = totales |
| AC-03 | Unit/integración con los importes del escenario |
| AC-04 | Unit + integración (transferencia 500) |
| AC-05 | Integración API (`entry_id`, origen) + componente (enlace) |
| AC-06 | Integración API (filtros, 400) + componente (selección de cuenta/tipo) |
| AC-07 | Integración con `reverse_journal_entry` |
| AC-08 | Integración (empresa, módulo, permiso) |

# Implementation Plan

## Architecture considerations
Los endpoints viven en `accounting` (`api/cash_flow_views.py`), no en `reporting`: así el submenú de Contabilidad no depende del módulo Reportes, `accounting` no importa `reporting` y la lógica de cálculo es una sola. Reporting y la página usan `GetLedgerReport`/`build_cash_flow`, por lo que coinciden por construcción. Como el selector «hoy/semana/mes» resuelve fechas en el servidor de Reportes, la página trabaja con fechas explícitas; la tarjeta pasa las fechas efectivas ya resueltas. Sin ADR: no hay decisión estructural nueva.

## Proposed solution
1. Dominio: ampliar `AccountFlow` (campos aditivos con valor por defecto `ZERO` para no romper constructores existentes) y construir en `build_cash_flow` las cifras por cuenta (INV-03/04); nueva función pura `build_cash_flow_movements(lines)` que clasifica filas.
2. Aplicación: `GetCashFlowDetail` (resumen + cuentas, reutiliza `GetLedgerReport`) y `ListCashFlowMovements` (puerto para líneas con cabecera: fecha, concepto, origen, reversión).
3. Infraestructura: método del repositorio del libro que devuelve las líneas de dinero del rango con datos del asiento (`select_related`), respetando corte y `company_id`.
4. API y fachada: dos vistas + serializers con paginación; `_origin` reutilizado; rutas en `accounting/api/urls.py`; función de fachada en `services.py`.
5. Frontend: modelo + servicio, página `accounting/pages/cash-flow`, ruta, ítem de menú, claves i18n; cambio del enlace en la tarjeta; update de `design-system.md` §6 y §5.

## Files/components affected
- Backend: `modules/accounting/domain/ledger_report.py`, `application/cash_flow.py` (nuevo), `application/ledger_report.py` (ajuste mínimo), `infrastructure/django/repositories.py`, `services.py`, `api/cash_flow_views.py` + `cash_flow_serializers.py` (nuevos), `api/urls.py`, pruebas en `modules/accounting/tests/`. `reporting` sin cambios de código (verificar que su adaptador ignora los campos nuevos).
- Frontend: `features/accounting/{models,services,pages/cash-flow,testing}`, `app.routes.ts`, `assets/data/routes.json`, `assets/i18n/{es,en,pt}.json`, `features/reporting/pages/reports/reports.component.{html,ts,spec.ts}`, `layout/sidebar/sidebar-menu.spec.ts`.
- Docs: `docs/design/design-system.md`.
- Migraciones: ninguna.

## Implementation steps
1. Pruebas de dominio y ampliación de `build_cash_flow` + `build_cash_flow_movements` (INV-01..04; AC-03, AC-04, AC-07).
2. Aplicación + repositorio + fachada (AC-02, AC-05, INV-05).
3. Vistas/serializers/URLs y pruebas de API (AC-06, AC-08, parámetros inválidos, paginación, totales).
4. Frontend: modelos, servicio y pruebas.
5. Página de Flujo de dinero con estados y variante compacta (UI-01, UI-03; AC-05, AC-06).
6. Ruta, menú, i18n (es/en/pt) y cambio del enlace en la tarjeta (AC-01, UI-02).
7. Actualizar `design-system.md`; correr lint, `i18n:check`, pruebas backend y frontend.

## Database / migrations
Sin migraciones. Consulta sobre `accounting_journal_line` con el índice `(company_id, account)` y rango por `entry__accounting_date`.

## Risks
- Reparto proporcional de INV-04 (documentado, solo afecta asientos mixtos; no cambia totales consolidados).
- Cambiar la tarjeta rompe pruebas de `reports.component.spec.ts` que miran `ledger-accounts-details`; se actualizan.
- Rangos muy grandes: la paginación mitiga; el resumen agrega en BD.

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-18): [Specification] Requisito no funcional: la paginación de movimientos es en memoria sobre líneas agregadas por asiento y cuenta en BD (antes: paginación en BD). Cambio aprobado explícitamente por el usuario en el chat; origen: REV-03 del Quality Gate 1. [Implementation Plan] Desempate de INV-04 y orden de movimientos aclarados (REV-02, REV-04).
