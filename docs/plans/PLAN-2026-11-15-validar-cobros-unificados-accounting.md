# PLAN-2026-11-15-validar-cobros-unificados-accounting (v1)

**Task:** TASK-validar-cobros-unificados-accounting · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno / Ninguno

## Objective
Demostrar con pruebas y una guía manual que configuración, libro, cobros de productos y servicios, regularización y reporte funcionan como un único recorrido, completando solo las brechas de prueba, y dejar el runbook de activación de accounting. Sin cambios de comportamiento de producto.

## Context
Ver TASK. Insumo: tarjeta PB-ACC-005; depende de PB-ACC-001..004 y PB-COB-002 (en `main`).

# Specification

## Domain context
Validación transversal de `accounting` con `sales`, `receivables`, `dentistry`, `inventory`, `reporting`. Ningún módulo cambia.

## Expected behavior
Con accounting habilitado y cuentas/métodos configurados, un pedido de productos de Bs 300 cobrado en 100+200 y una proforma de servicios de Bs 300 cobrada en 100+50+150 dejan en el libro 5 entradas, total Bs 600 (PRODUCT 300, SERVICE 300), sin duplicados; el resto de criterios de la tarjeta se cumplen y quedan respaldados por una prueba o por un paso de la guía manual.

## Domain rules / invariants
Existentes, sin nuevas: una entrada por pago (INV de ACC-003/COB-002), idempotencia por origen, atomicidad pago+entrada, el libro no presenta saldos.

## Acceptance criteria
- AC-01 Productos 100+200 y servicios 100+50+150 en la misma empresa: libro con 5 entradas, `totals` 600 y `by_origin` PRODUCT 300 / SERVICE 300; sin duplicados al reintentar los mismos cobros.
- AC-02 Un pago de servicios distribuido en varias líneas conserva una sola entrada (ya cubierto; se referencia, no se duplica).
- AC-03 Reintento, fallo contable, falta de mapeo y concurrencia: coherencia sin pagos huérfanos ni sobrepago (ya cubierto en ambos orígenes; la revisión lo confirma en la matriz de cobertura).
- AC-04 Cambiar el mapeo conserva los destinos históricos y aplica el nuevo al próximo pago, en productos y en servicios (cobertura existente; se confirma en el recorrido).
- AC-05 Perfil odontológico con Ventas deshabilitado cobra; cobrar un pedido no genera `StockMovement`; ningún campo del libro contiene notas clínicas.
- AC-06 Regularización repetida no altera totales ni saldos; tras regularizar, listado y totales del libro coinciden con los filtros sobre todas las páginas.
- AC-07 El reporte ventas − gastos devuelve los mismos resultados y etiqueta con el libro habilitado y con entradas; la API del libro no expone saldos.
- AC-08 Con accounting deshabilitado, cobros de productos y servicios se comportan como antes (cobertura existente; se confirma).
- AC-09 Existe una guía de activación con: configurar cuentas y métodos, validar contratos y permisos, previsualizar regularización, aplicar, comprobar totales; cobertura histórica, pendientes y reversiones fuera de alcance.
- AC-10 Verificación en interfaz documentada para productos y odontología (incluido Ventas deshabilitado) con el resultado de la corrida.

## Edge cases / Error cases
Pago anterior a la habilitación (se regulariza), método sin mapeo (pendiente con motivo), otra empresa (no se ve ni se toca).

## Authorization / permissions
Sin cambios; las pruebas confirman admin vs no admin y aislamiento por empresa en el recorrido.

## Non-functional requirements
Las pruebas nuevas usan BD real (`TransactionTestCase` donde haya hilos) y no dependen de reloj ni de orden.

## Out of scope
Cambiar comportamiento, reporting, reversiones, partida doble, fiscal, egresos, transferencias, saldos iniciales; desplegar o regularizar producción; instalar Playwright.

# Test Specification

## Integration tests
Nuevo `backend/modules/accounting/tests/test_unified_journey.py` (ubicado en `accounting` por ser el consumidor; usa fixtures de Ventas y Cobros ya existentes): AC-01, AC-05, AC-06, AC-07, AC-04 (mapeo cambiado en ambos orígenes dentro del recorrido). Se comprueban brechas antes de escribir: si una brecha ya está cubierta, no se duplica.
## E2E
**NO** — la verificación de interfaz es manual (guía) porque Playwright no está instalado y no se instala sin confirmación.
## Regression tests
Suites existentes de `accounting`, `sales`, `receivables`, `reporting`, `modularity` y `test_boundaries` completas.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | `test_unified_journey` (nuevo) |
| AC-02 | `receivables/tests/test_payment_ledger.py:58` (existente) |
| AC-03 | `sales/tests/test_payment_ledger.py:123,138,305,311`; `receivables/tests/test_payment_ledger.py:119,140,162,180` (existentes) |
| AC-04 | `sales/.../test_payment_ledger.py:155`, `receivables/.../:58` (existentes) + paso del recorrido |
| AC-05 | `test_unified_journey` (nuevo) + `receivables/.../:248` (existente) |
| AC-06 | `test_unified_journey` (nuevo) + `accounting/tests/test_entries_api.py:60` (existente) |
| AC-07 | `test_unified_journey` (nuevo) + suite de `reporting` |
| AC-08 | `sales/.../:162`, `receivables/.../:210` (existentes) |
| AC-09 | `docs/deployment/activar-accounting.md` (revisión) |
| AC-10 | `docs/tests/MANUAL-validar-cobros-unificados-accounting.md` con resultado de la corrida en navegador |

# Implementation Plan

## Proposed solution
Matriz de cobertura en el TASK; pruebas solo para brechas; runbook y guía manual en `docs/`.

## Files/components affected
- Backend (solo pruebas): `backend/modules/accounting/tests/test_unified_journey.py`.
- Docs: `docs/deployment/activar-accounting.md`, `docs/tests/MANUAL-validar-cobros-unificados-accounting.md`, TASK.
- Sin cambios en `backend/` de producción, frontend, migraciones ni `.env`.

## Implementation steps
1. Confirmar cada brecha del TASK leyendo los fixtures (`sales/tests/test_payment_ledger.py`, `receivables/tests/test_payment_ledger.py`, `reporting/tests`) y registrar la matriz AC→prueba en el TASK.
2. Escribir `test_unified_journey` para las brechas confirmadas (AC-01, 05, 06, 07).
3. Ejecutar suites de `accounting`, `sales`, `receivables`, `reporting`, `modularity`; si aparece un defecto, registrarlo como hallazgo (corrección mínima solo si está en alcance).
4. Escribir `activar-accounting.md` con pasos concretos (API/pantallas/comando `regularize_ledger`), cobertura histórica, pendientes y reversiones fuera de alcance.
5. Escribir la guía manual y ejecutarla en el navegador integrado con datos de desarrollo (productos, odontología con Ventas deshabilitado); anotar resultados.

## Database / migrations
Ninguna.

## Risks
Defecto real descubierto (se reporta); datos de desarrollo insuficientes para la verificación visual (se anota qué no se pudo probar).

## New dependencies
Ninguna.
