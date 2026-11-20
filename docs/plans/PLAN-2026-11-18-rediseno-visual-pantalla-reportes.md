# PLAN-2026-11-18-rediseno-visual-pantalla-reportes (v1)

**Task:** TASK-rediseno-visual-pantalla-reportes · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-rediseno-visual-pantalla-reportes-jerarquia-analitica · ADR: Ninguno

## Objective
Mejorar la jerarquía y legibilidad de `/pocketbiz/reports` (solo frontend, sin cambios de API ni backend) siguiendo el DDR.

# Specification
## Current behavior
Ver TASK (`reports.component.html:18-218`).
## Expected behavior
Ver DDR «Pantallas/flujos afectados».
## Acceptance criteria
- **AC-01** Dos secciones con encabezado «Contable (libro de asientos)» y «Operativo (pedidos y gastos)», cada una con su chip («Contable»/«Operativo»); contenido en contenedor de ancho máximo 80 rem; tarjetas de igual altura por fila.
- **AC-02** Flujo de dinero y Resultado contable son los KPIs grandes; Total de ventas y Total de gastos van debajo, más pequeños.
- **AC-03** Los criterios largos (contable, ventas, gastos, operativo) están dentro de un `<details>` «¿Cómo se calcula?» cerrado por defecto; la tabla por cuenta, dentro de «Ver por cuenta».
- **AC-04** Resultado negativo: `text-danger` + etiqueta «Resultado negativo»; positivo `text-success`; cero sin color. Etiquetas «Resultado» y «Margen» intactas.
- **AC-05** Si `cashFlow.accounts` está vacía, aviso con enlace a `/pocketbiz/accounting/accounts`; con cuentas, no aparece.
- **AC-06** El aviso de cobertura tiene botón de cierre con `aria-label`; al cerrar desaparece y reaparece al cambiar de periodo.
- **AC-07** El gráfico de dona y los iconos llevan `aria-label` o `aria-hidden`; textos auxiliares ≥ 12 px con `text-body-secondary`; sin HEX nuevos.
- **AC-08** Se conservan estados cargando/error/módulo deshabilitado/«Sin registros» y todos los `data-testid` existentes.
## Edge cases
Contabilidad deshabilitada (sin avisos, tarjetas «No disponible»); `partial` sin corte (`AVISO_SIN_CORTE`); resultado «0.00»; ledger sin cuentas y con periodo parcial (ambos avisos).
## Out of scope
Series por día, backend, submenú, renombrar «Ganancia estimada», dashboard.
## Authorization / permissions
Sin cambios; el backend es la barrera.
## API contract
Sin cambios (API-01: se usa `cash_flow.accounts` ya existente).
## UI behavior
UI-01 Plantilla «Dashboard y reportes» (§5) con secciones; UI-02 plegables `<details>`; UI-03 avisos tenues con cierre; UI-04 chips informativos; UI-05 estados §4.

# Test Specification
| AC | Verification |
|---|---|
| AC-01, AC-02 | Spec de componente: encabezados/chips presentes, orden contable antes que operativo |
| AC-03 | Spec: `details` sin `open`, contiene criterio y tabla de cuentas |
| AC-04 | Spec: ledger con resultado `-30.00` → `text-danger` + etiqueta; `30.00` → `text-success` |
| AC-05 | Spec: `accounts: []` → aviso con `href` a cuentas; con cuentas → ausente |
| AC-06 | Spec: cerrar oculta; `onSelection` lo vuelve a mostrar |
| AC-07 | Spec: `aria-label` del gráfico; revisión de plantilla sin HEX; `i18n:check` |
| AC-08 | Specs existentes se mantienen verdes |
**E2E: NO** — cambio visual de una pantalla, sin flujo crítico de punta a punta.

# Implementation Plan
## Files/components affected
`reports.component.{html,ts,scss}` (+ spec), `period-selector.component.html` (alto táctil), `assets/i18n/{es,en,pt}.json`, `docs/design/design-system.md` (nota en «Dashboard y reportes»).
## Implementation steps
1. i18n: claves nuevas en las tres lenguas (AC-01,03,04,05,06,07).
2. TS: señal `coverageDismissed` (reinicio en `onSelection`), `isNegative/isPositive`, `noMoneyAccounts`; scss con ancho máximo.
3. HTML: reestructurar en secciones, KPIs, plegables, avisos, aria (AC-01..08).
4. Selector de periodo: botones ≥ 40 px.
5. Specs nuevas/actualizadas; `npm run i18n:check`, `npm test` de reporting, `npm run lint`.
6. Nota en design-system.md.
## Risks
Diff del PR incluye commits de #100 hasta su merge. Sin dependencias nuevas (node_modules por junction desde otro worktree).
