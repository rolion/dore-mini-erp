# PLAN-2026-11-17-contabilizar-inventario-costo-ventas (v1)

**Task:** TASK-contabilizar-inventario-costo-ventas · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** ADR-contabilizar-inventario-costo-ventas-ledger-de-costo-y-salida-valorizada

## Objective
Valorizar cada salida por venta al costo promedio móvil y asentar Debe Costo de ventas / Haber Inventario una sola vez, atómicamente con el stock, sin duplicar el asiento de recepción de COM-02.

## Context
Ver TASK. Base: `origin/accounting`. Decisiones de la persona: promedio móvil en Costeo; ajustes fuera de alcance.

# Specification

## Domain context
Contextos: `costing` (costo), `sales` (entrega), `purchases` (recepción), `accounting` (asientos, sin cambios de contrato), `inventory` (saldos).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Costo de salida | Cantidad × costo promedio vigente del producto | Trello INV-01, ADR |
| Costo promedio móvil | Promedio ponderado por producto y empresa, 6 decimales | `costing/domain/valuation.py` (METHOD) |
| Evento de costo | Hecho inmutable IN / OUT / IN_REVERSAL del ledger | ADR |

## Current behavior
Ver TASK «Comportamiento actual» (entrega sin costo ni asiento; recepciones sin valor).

## Expected behavior
Con Contabilidad cubierta y productos con stock controlado en el pedido, al entregar se registra el costo de salida y su asiento en la misma transacción. Las recepciones de compra alimentan el promedio. Sin costo o configuración, la entrega se bloquea con mensaje accionable.

## Domain rules / invariants
- INV-01: dinero siempre `Decimal`; costo unitario a 6 decimales y total de línea a 2 (`ROUND_HALF_UP`); importe del asiento = Σ totales de línea.
- INV-02: el costo de una salida es el promedio vigente, nunca el precio de venta; las salidas no cambian el promedio.
- INV-03: un evento de costo es único por `(empresa, tipo, origen, producto)`; reintentar no duplica costo, stock ni asiento.
- INV-04: costo ausente (sin Costeo adoptado o producto sin promedio) o configuración incompleta bloquea; nunca se inventa un valor. Costo cero solo si fue declarado en la adopción.
- INV-05: INV-01 no asienta recepciones; el único dueño es COM-02.
- INV-06: aislamiento por `company_id`.

## Acceptance criteria
- AC-01: pedido con producto a precio 150 y costo promedio 100, entrega con Contabilidad cubierta → asiento `INVENTORY_SALE_COST` Debe Costo de ventas 100 / Haber Inventario 100 (no 150); el ingreso 150 sigue siendo del asiento de VEN-01.
- AC-02: reintentar la entrega/salida no duplica movimiento de stock, evento de costo ni asiento.
- AC-03: recibir una compra con Costeo adoptado actualiza el promedio (`(saldo×avg + qty×precio)/(saldo+qty)`) y **no** crea ningún asiento.
- AC-04: si el asiento, la configuración, el costo o el período fallan, no queda stock descontado, evento de costo ni entrega.
- AC-05: producto sin costo (sin adopción o sin promedio) o rol de Inventario/Costo de ventas sin configurar → la entrega se bloquea con mensaje que indica qué configurar y dónde (409/400 existente de Ventas).
- AC-06: salida con stock insuficiente conserva la política de stock negativo existente y no deja costo.
- AC-07: revertir una recepción registra IN_REVERSAL al costo original, vinculado, y no cambia el promedio.
- AC-08: sin Contabilidad cubierta (deshabilitada, previa al corte o con hueco) la entrega funciona como hoy, sin asiento y sin exigir configuración; con Costeo habilitado el ledger sí se actualiza.
- AC-09: costo total cero declarado → se registra el evento y no se genera asiento.
- AC-10: aislamiento: un evento o promedio de otra empresa nunca se lee ni modifica.

## Edge cases / Error cases
- Pedido con varios productos: un solo asiento por el total; si un producto no tiene costo, falla todo (lista de productos).
- Entrega con anticipos y fecha sin cobertura: se mantiene el comportamiento de VEN-01.
- Recepción sobre stock sin costo previo: promedio arranca con el costo de recepción (limitación en PR).
- Recepciones/salidas simultáneas del mismo producto: serializadas por `lock_company_stock`.

## Authorization / permissions
Sin permisos nuevos: usa los de entrega de pedido y recepción existentes.

## API contract
- API-01: sin endpoints nuevos. Las vistas de entrega y de recepción devuelven los errores de bloqueo por los códigos/estructura de error existentes (nuevos `code`: `inventory_cost_unavailable`, `posting_not_configured`); compatible hacia atrás.

## UI behavior
Sin pantallas nuevas (Diseño NO). El frontend ya muestra el mensaje de error de Entregar pedido; se verifica que el nuevo mensaje sea legible. Claves i18n es/en/pt solo si el frontend traduce códigos de error (revisar al implementar).

## Non-functional requirements
Una consulta de promedio por producto de la entrega; ledger indexado por `(company_id, product_id, occurred_at)`.

## Out of scope
Ajustes de inventario, devolución de ventas, PEPS/UEPS, costo por almacén, impuestos/gastos de compra en el costo, asiento de recepción (COM-02), vista de costos en la UI, conversión de divisas.

## Open questions
- Ninguna que bloquee.

# Test Specification

## Unit tests
Dominio de costeo: promedio (AC-03, INV-01/02), redondeo, costo cero, producto sin costo (INV-04).

## Integration tests
Backend: `costing` servicio (idempotencia AC-02, concurrencia INV-03, AC-10), Ventas entrega con y sin cobertura (AC-01, 04, 05, 08, 09), Compras recepción/reversa (AC-03, 07), estructura de error de API.

## E2E
NO — flujo cubierto por integración de API; sin UI nueva.

## Regression tests
Suites existentes de `sales`, `purchases`, `costing`, `inventory`, `accounting` y `makemigrations --check`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración Ventas: entrega 150/costo 100, líneas del asiento |
| AC-02 | Integración: doble entrega/`cost_outputs` repetido |
| AC-03 | Unitaria del promedio + integración Compras: 0 asientos |
| AC-04 | Integración: fallo forzado del asiento/período revierte stock y ledger |
| AC-05 | Integración: sin adopción / sin rol configurado |
| AC-06 | Integración Ventas existente + sin evento de costo |
| AC-07 | Integración Compras: reversa de recepción |
| AC-08 | Integración: Contabilidad deshabilitada / antes del corte |
| AC-09 | Unitaria + integración: costo cero declarado |
| AC-10 | Integración multiempresa |

# Implementation Plan

## Architecture considerations
Ver ADR. Dominio puro de costo; fachada única `costing.services`; Ventas y Compras opcionales sobre ella.

## Proposed solution
Ledger inmutable + promedio derivado; la entrega orquesta salida de stock → costo → asiento en una transacción.

## Files/components affected
- backend: `costing/domain/` (costo y promedio), `costing/application/`, `costing/infrastructure/django/` (modelo, repositorio) + migración `0002`, `costing/services.py` (nuevo); `sales/infrastructure/adapters.py` y `sales/application/{ports,commands}.py` (valorización y asiento); `purchases/infrastructure/adapters.py` (+ puerto) para costo de recepción y reversa; tests por módulo.
- frontend: sin cambios previstos (verificar el mensaje de error).
- docs: TASK, ADR, PLAN, este PR.

## Implementation steps
1. Dominio de costo: promedio, redondeo, `CostUnavailable` (INV-01..04).
2. Modelo `CostEventModel` + migración `0002` + repositorio por `company_id` (INV-03, 06).
3. Casos de uso y fachada `costing.services` bajo `lock_company_stock` (AC-02, 03, 07, 09, 10).
4. Compras: trasladar el costo de cada recepción y de su reversa, sin asiento (AC-03, 07, INV-05).
5. Ventas: en `DeliverOrder`, tras `register_outputs`, valorizar y asentar `INVENTORY_SALE_COST` con `check_posting_ready` previo; mapear errores (AC-01, 04, 05, 08).
6. Pruebas de integración y regresión; documentar límites en el PR.

## Database / migrations
`costing/0002_cost_event` solo `CreateModel`; no edita migraciones aplicadas; reversible.

## Risks
Bloqueo de entregas en empresas con Contabilidad cubierta y sin Costeo adoptado; acoplamiento Compras→Costeo; ajustes sin valor desvían el promedio de forma aceptada y documentada.

## New dependencies
Ninguna.
