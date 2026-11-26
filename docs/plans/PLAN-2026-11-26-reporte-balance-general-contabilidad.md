# PLAN-2026-11-26-reporte-balance-general-contabilidad (v1)

**Task:** TASK-reporte-balance-general-contabilidad · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-reporte-balance-general-contabilidad-pantalla-balance · Ninguno (ADR)

## Objective
Agregar a Contabilidad un reporte de Balance general (Activo, Pasivo, Patrimonio) calculado desde el libro de asientos, filtrable por fecha de inicio y fin.

## Context
Ver TASK. Existe «Saldos» (sumas y saldos por cuenta) pero no un estado agrupado por clasificación. Se reutiliza `movements_by_account`.

# Specification

## Domain context
Bounded context `accounting`. Sin otros contextos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Balance general | Estado de Activo, Pasivo y Patrimonio a una fecha de corte | pedido del usuario |
| Saldos | Sumas y saldos por cuenta (CONT-04); otra pantalla | `pages/balances` |
| Saldo inicial | Acumulado antes de «Desde» | `AccountMovements.opening_*` |
| Movimiento | Variación dentro de [Desde, Hasta] | `AccountMovements.debit/credit` |
| Resultado del período | Ingresos − Costos − Gastos dentro del rango | `ledger_report.build_result` |

## Current behavior
No existe el reporte. `balances/` devuelve sumas y saldos por cuenta (`api/urls.py:65`).

## Expected behavior
`GET /api/accounting/balance-sheet/?date_from=&date_to=` devuelve tres secciones con sus cuentas, subtotales y la verificación de la ecuación contable. «Hasta» es la fecha de corte de los saldos finales; «Desde» separa saldo inicial y movimiento.

## Domain rules / invariants
- **INV-01** Naturaleza: Activo = Debe − Haber; Pasivo y Patrimonio = Haber − Debe. Cuentas correctoras o de saldo contrario salen negativas y restan en el subtotal.
- **INV-02** Saldo final = Saldo inicial + Movimiento, por cuenta y por sección.
- **INV-03** Resultado del Patrimonio: *Resultados de ejercicios anteriores* = Ingresos − Costos − Gastos de las fechas anteriores a «Desde» (0 sin «Desde»); *Resultado del período* = los del rango. Mismo cálculo por clasificación que `build_result`.
- **INV-04** Total Patrimonio = suma de cuentas EQUITY + ambas líneas de resultado. Diferencia = Total Activo − (Total Pasivo + Total Patrimonio). `balanced` ⇔ diferencia = 0.
- **INV-05** Las cuentas sin clasificación quedan fuera de las secciones; su neto (Debe − Haber) se informa como `unclassified_balance` y explica una diferencia ≠ 0.
- **INV-06** Se omiten las cuentas con saldo inicial, movimiento y saldo final todos en 0.
- **INV-07** Todo importe en `Decimal`; toda consulta filtrada por `company_id`.

## Acceptance criteria
- **AC-01** Con asientos de ASSET, LIABILITY, EQUITY, INCOME y EXPENSE/COST, cada cuenta aparece en su sección con signo según INV-01 y los subtotales suman sus filas.
- **AC-02** Sin fechas, el reporte cubre todo el libro; con «Hasta», excluye asientos posteriores; el saldo final es acumulado hasta esa fecha.
- **AC-03** Con «Desde», cada cuenta muestra saldo inicial (previo a «Desde»), movimiento (en el rango) y saldo final = inicial + movimiento; sin «Desde», saldo inicial = 0 y movimiento = saldo final.
- **AC-04** *Resultados de ejercicios anteriores* y *Resultado del período* se calculan según INV-03 y se suman al Patrimonio; con un libro balanceado, `balanced = true` y diferencia 0 para cualquier par de fechas válido.
- **AC-05** Cuentas sin clasificación con saldo → `unclassified_balance ≠ 0`, `balanced = false`; sin saldo → no afectan.
- **AC-06** `date_from > date_to` → 400 con error en `date_from`; fecha inválida → 400.
- **AC-07** Solo se ven datos de la empresa del usuario; sin módulo Contabilidad → rechazado como en los demás endpoints del módulo.
- **AC-08** La pantalla muestra filtros Desde/Hasta (en la URL), las tres secciones, totales, badge Cuadra/No cuadra y aviso de cuentas sin clasificar; estados cargando, error con «Reintentar» y vacío con «Limpiar filtros».
- **AC-09** Las columnas Saldo inicial y Movimiento solo aparecen con «Desde».
- **AC-10** La entrada «Balance general» está en el menú de Contabilidad y todos los textos existen en es/en/pt.

## Edge cases / Error cases
- Empresa sin asientos: tres secciones vacías, totales 0, `balanced = true` («Sin registros»).
- Asientos de reversión: cuentan por su fecha contable (como Saldos).
- «Desde» = «Hasta»: válido (saldo inicial hasta el día anterior, movimiento del día).
- Cuenta desactivada con saldo: aparece (como Saldos), con etiqueta «Deshabilitada».

## Authorization / permissions
`required_modules = ('accounting',)`; empresa tomada del usuario autenticado (`company_id_from`). Solo lectura (GET).

## API contract
**API-01** `GET /api/accounting/balance-sheet/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` (ambos opcionales). 200:
```json
{"date_from": null, "date_to": null, "has_opening": false,
 "sections": [{"key": "ASSET", "rows": [{"account_id": "…", "code": "1.1", "name": "Caja", "is_active": true,
                "opening": "0.00", "movement": "100.00", "closing": "100.00"}], "total": "100.00"},
              {"key": "LIABILITY", …}, {"key": "EQUITY", …,
               "previous_result": "0.00", "period_result": "0.00"}],
 "totals": {"assets": "…", "liabilities": "…", "equity": "…", "liabilities_and_equity": "…",
            "difference": "0.00", "balanced": true, "unclassified_balance": "0.00"}}
```
Importes como cadena decimal; `previous_result`/`period_result` también traen `opening/movement/closing` implícitos en `total` de Patrimonio. Compatibilidad: endpoint nuevo, sin cambios a los existentes.

## UI behavior
- **UI-01** Plantilla «Lista de solo lectura con filtros» (design-system §5) según el DDR: filtros Desde/Hasta + Limpiar, nota explicativa.
- **UI-02** Tres tablas (Activo, Pasivo, Patrimonio) con pie «Total …»; Patrimonio con las dos filas de resultado.
- **UI-03** Cierre con Total Activo, Total Pasivo + Patrimonio y badge Cuadra/No cuadra (+ diferencia); aviso `alert-warning` de cuentas sin clasificar.
- **UI-04** Estados cargando/error/vacío; negativos con `text-danger` y signo; móvil sin desplazamiento horizontal.
- **UI-05** Ruta `/pocketbiz/accounting/balance-sheet` con `data.module = 'accounting'` y entrada de menú.

## Non-functional requirements
Una sola consulta agregada (`movements_by_account`); sin paginación (el plan de cuentas es acotado). Sin texto hardcodeado.

## Out of scope
Selector de período fiscal, comparativo entre períodos, exportación, estado de resultados, aplicar el corte contable, cambiar Saldos.

## Open questions
Convención de rango (supuestos del TASK): confirmar con el usuario en la revisión del PR; no bloquea.

# Test Specification

## Unit tests
Dominio `balance_sheet` (sin Django): INV-01..INV-06 con casos numéricos (AC-01, AC-03, AC-04, AC-05, edge sin asientos, cuenta correctora negativa).
## Integration tests
Caso de uso con repositorios en memoria (AC-02, AC-03, AC-06); API con BD de pruebas (`test_balance_sheet_api.py`): AC-01, AC-02, AC-03, AC-04 (libro balanceado con asientos antes y dentro del rango), AC-05, AC-06, AC-07 (empresa B no aparece; módulo deshabilitado).
Frontend: modelo (mapeo DTO → vista, `bigint`/strings sin `float`), servicio (query params), componente (AC-08, AC-09: filtros en URL, columnas condicionales, estados, badge), menú (`sidebar-menu.spec.ts`), paridad i18n (AC-10).
## E2E
**NO** — reporte de solo lectura cubierto por pruebas de API y de componente; no es flujo crítico de punta a punta.
## Regression tests
Suites `modules.accounting` y frontend completas, `ng lint`, `i18n:check`, `ng build`.
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | dominio + API |
| AC-02 | caso de uso + API |
| AC-03 | dominio + API |
| AC-04 | dominio + API (libro balanceado) |
| AC-05 | dominio + API |
| AC-06 | caso de uso + API |
| AC-07 | API (multiempresa y módulo) |
| AC-08 | componente |
| AC-09 | componente |
| AC-10 | `sidebar-menu.spec.ts` + prueba de paridad i18n |

# Implementation Plan

## Architecture considerations
Mismo patrón que Saldos e Ingresos y egresos: dominio puro → caso de uso con puertos → vista/serializer. Reutiliza `movements_by_account`; no toca infraestructura Django.

## Proposed solution
Caso de uso `GetBalanceSheet(accounts, journal, periods?)` (no se necesitan períodos): valida el rango, lee cuentas y `movements_by_account(date_from, date_to)`, y delega en `domain/balance_sheet.py` (funciones puras) el armado de secciones, resultados y totales.

## Files/components affected
- Backend: `domain/balance_sheet.py` (nuevo), `application/balance_sheet.py` (nuevo), `api/balance_sheet_serializers.py` y `api/balance_sheet_views.py` (nuevos), `api/urls.py` (ruta `balance-sheet/`), tests `tests/test_balance_sheet_domain.py`, `test_balance_sheet_use_case.py`, `test_balance_sheet_api.py`.
- Frontend (`features/accounting/`): `models/balance-sheet.ts`, `services/balance-sheet-api.service.ts`, `pages/balance-sheet/` (componente, html, scss), `testing/balance-sheet-fixtures.ts`, specs; `app.routes.ts`, `assets/data/routes.json`, `sidebar-menu.spec.ts`, `assets/i18n/{es,en,pt}.json`.
- Docs: TASK, DDR, PLAN.

## Implementation steps
1. Dominio `balance_sheet.py`: naturaleza por clase, secciones, resultados, totales, `balanced` (INV-01..06). Pruebas unitarias.
2. Caso de uso con validación de rango (AC-02, AC-03, AC-06) y pruebas.
3. Serializer de filtros, serializer de salida, vista y ruta (API-01, AC-07) y pruebas de API.
4. Frontend: modelo y servicio con pruebas (importes sin `float`).
5. Frontend: página, ruta, menú, i18n es/en/pt (UI-01..05, AC-08..10) y pruebas.
6. Lint backend (`ruff`/`flake8` en lo cambiado), suite del módulo, lint/build/test/`i18n:check` del frontend.

## Database / migrations
Sin migraciones ni cambios de modelo.

## Risks
- Interpretación del rango (ver supuestos del TASK): se explica en pantalla y es fácil de ajustar (solo dominio).
- Datos antiguos sin clasificación: aviso en pantalla.

## New dependencies
Ninguna.
