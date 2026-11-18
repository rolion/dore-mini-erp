# PLAN-2026-11-18-adaptar-reportes-libro-partida-doble (v1)

**Task:** TASK-adaptar-reportes-libro-partida-doble · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-adaptar-reportes-libro-partida-doble-seccion-contable-en-reportes.md` · `docs/adr/ADR-adaptar-reportes-libro-partida-doble-lectura-contable-en-reporting.md`

## Objective
Hacer que Reportes lea el libro de partida doble: flujo de dinero por variación de cuentas Caja/Banco (sin transferencias internas) y resultado contable Ingresos − Costos − Gastos, con cobertura por corte, sin duplicar compras ni cobros y sin añadir submenú.

## Context
Ver TASK. Base de ramas: `task/TASK-revertir-asiento-al-anular-gasto` (ya incluye `origin/accounting`); el PR se abre contra `accounting`.

# Specification
## Domain context
Bounded contexts: **Reporting** (consumidor) y **Accounting** (dueño del libro). Relacionados solo como emisores de asientos: Sales, Receivables, Inventory, Purchases, Expenses (no se tocan).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Cuenta de dinero | Cuenta de Activo con `kind` (CASH/BANK/WALLET) | `accounting/domain/account.py:128` |
| Flujo | Variación (Debe − Haber) de cuentas de dinero | Trello CONT-05 |
| Transferencia interna | Asiento cuyas líneas de dinero netean 0 | ADR |
| Resultado contable | Ingresos − Costos − Gastos por clase | Trello CONT-05 |
| Fecha contable | `accounting_journal_entry.accounting_date` | `models.py:203` |

## Current behavior
- Ventas: total de pedidos no cancelados por fecha de pedido (`reporting/application/criteria.py`, `sales/services.py:70`); Gastos vigentes por `expense_date` (`expenses/services.py:34`). Reporting no consulta el libro (`reporting/infrastructure/adapters.py`).
- El libro solo expone Debe/Haber acumulado por cuenta sin fechas (`accounting/services.py:459`, `repositories.py:572`) y por rango en sumas y saldos (`repositories.py:581`), sin agrupar por asiento.
- Eventos del libro: compra reconoce Inventario/Por pagar y el pago mueve Por pagar/Dinero; cobro mueve Dinero/Por cobrar; costo de ventas por salida (`accounting/domain/posting.py:89-108`).

## Expected behavior
Nuevo reporte contable (endpoint + sección UI) calculado solo del libro por fecha contable y empresa, con cobertura. Reportes operativos intactos y rotulados.

## Domain rules / invariants
- INV-01 (existente, INV-01 de inventario): el costo de ventas se reconoce una vez; el reporte solo lee, no recalcula costo.
- INV-R1 Flujo = Σ(Debe − Haber) de cuentas de dinero; por asiento, neto >0 entrada, <0 salida, =0 transferencia (no suma a entradas/salidas).
- INV-R2 Resultado = Haber−Debe de INCOME − (Debe−Haber de COST) − (Debe−Haber de EXPENSE).
- INV-R3 Cobrar deuda o pagar proveedor mueven Activo/Pasivo: no tocan INCOME/COST/EXPENSE.
- INV-R4 Una reversión cuenta en su propia fecha contable y corrige el concepto original (invierte líneas).
- INV-R5 Toda lectura filtra por `company_id`; el libro anterior al corte no se suma.

## Acceptance criteria
- AC-01 Venta 150 / costo 100 y cobro posterior → ingresos 150, costos 100, margen 50; el cobro no suma ingresos.
- AC-02 Compra de inventario 1.000 y pago de 300 → flujo con salida 300 y gastos 0 (resultado no cambia por 1.000 ni por 300).
- AC-03 Transferencia Caja→Banco 200 → entradas 0, salidas 0, neto 0; se informa transferencias 200.
- AC-04 Conciliación: totales del reporte = Σ líneas del libro del rango; otra empresa no aparece; reversión en otro periodo se cuenta en su fecha.
- AC-05 Rango anterior al corte (parcial o total) → `partial=true` con `cutoffDate` y sin sumar lo anterior; módulo `accounting` deshabilitado → «No disponible» y 403/estado de fuente deshabilitada en API según patrón de Reporting.
- AC-06 Los reportes operativos muestran criterio «Operativo» y sus respuestas no cambian de forma.

## Edge cases / Error cases
Periodo inválido → 400 como el resto de reportes; sin movimientos → ceros; cuentas de dinero sin `kind` nulo no cuentan; cuenta de dinero inactiva con historial sí cuenta; contra-cuentas netas en su clase; moneda única existente (sin conversión).

## Authorization / permissions
Mismos permisos de Reportes; módulo `reporting` requerido y `accounting` como fuente opcional; empresa del token.

## API contract
- API-01 `GET /api/reports/ledger/?period=… | date_from&date_to` → `{period, accountingEnabled, coverage:{cutoffDate, partial}, cashFlow:{opening, inflow, outflow, net, closing, transfers, accounts:[{accountId,name,opening,inflow,outflow,net,closing}]}, result:{income, cost, margin, expense, result}, criteria}` (decimales como cadena). Aditivo; sin cambio a endpoints existentes.

## UI behavior
- UI-01 Bloque «Libro contable» en `/pocketbiz/reports` según el DDR (plantilla Dashboard y reportes): tarjetas Flujo y Resultado, aviso de cobertura, estados cargando/vacío/error/no disponible.
- UI-02 Etiqueta «Operativo» en criterios de ventas/gastos; sin nuevo submenú.

## Non-functional requirements
`Decimal` siempre; consultas agregadas acotadas por empresa y fechas; textos `translate` es/en/pt.

## Out of scope
Estados financieros legales, cierre de resultados, conversión de divisas, cambios en emisión de asientos, retiro de reportes operativos.

## Open questions
- Billeteras (WALLET) cuentan como dinero (decidido; reversible cambiando el filtro).

# Test Specification
## Unit tests
Dominio del flujo/resultado puro (clasificación entrada/salida/transferencia, signos por clase, contra-cuentas).
## Integration tests
Fachada `get_ledger_report` con asientos reales (post_journal_entry/automáticos): AC-01..05; fuga entre empresas; reversión entre periodos; vista API (`/api/reports/ledger/`), módulo deshabilitado; prueba de fronteras actualizada.
## E2E
NO — flujo de lectura cubierto por integración y pruebas de componente; no es flujo crítico de punta a punta.
## Regression tests
Suite de `reporting` y `accounting` sin cambios de contrato.
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | integración fachada + unit resultado |
| AC-02 | integración fachada (compra + pago) |
| AC-03 | integración fachada + unit transferencia |
| AC-04 | integración fachada/API (empresas, fechas, reversión) |
| AC-05 | integración API + componente (aviso/no disponible) |
| AC-06 | spec de componente Reportes + prueba API existente |

# Implementation Plan
## Architecture considerations
ADR: puerto `LedgerReader` en Reporting, adaptador sobre `accounting/services.py`; Accounting sigue sin importar Reporting.
## Proposed solution
Consulta por asiento (suma Debe−Haber de líneas de cuentas de dinero agrupada por entry) + agregación por clase; dominio puro que clasifica y arma el DTO; cobertura con `domain/coverage`.
## Files/components affected
- Backend: `accounting/services.py` (+DTOs), `accounting/application/ledger_report.py` y `domain/ledger_report.py` (nuevos), repositorio `DjangoJournalRepository` (consultas de lectura), `reporting/application/{ports,queries}.py`, `reporting/infrastructure/adapters.py`, `reporting/api/{views,urls,serializers}.py`, `modularity` (fuente), `modules/sales/tests/test_boundaries.py`, `docs/architecture/ddd.md`, tests.
- Frontend: `features/reporting/{models,services,pages/reports}`, `assets/i18n/{es,en,pt}.json`, specs.
## Implementation steps
1. Dominio puro del flujo/resultado (INV-R1..R4) + unit tests.
2. Consultas del repositorio y fachada `get_ledger_report` + integración (AC-01..04).
3. Cobertura y módulo deshabilitado (AC-05).
4. Puerto/adaptador/caso de uso/vista/serializer de Reporting (API-01) + pruebas API y fronteras; actualizar `ddd.md`.
5. Frontend: modelo, servicio, sección y textos i18n (UI-01/02) + specs; `npm run i18n:check`.
6. Rotular criterios operativos (AC-06) y documentar.
## Database / migrations
Ninguna.
## Risks
Rendimiento en rangos largos; cuentas sin `kind` que sean dinero real quedarían fuera del flujo (se muestra la lista de cuentas incluidas); divergencia operativo vs contable explicada en el criterio.
## New dependencies
Ninguna.
