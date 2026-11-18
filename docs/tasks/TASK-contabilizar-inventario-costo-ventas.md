# TASK-contabilizar-inventario-costo-ventas: Contabilizar inventario y costo de ventas (INV-01)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-contabilizar-inventario-costo-ventas
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/91
**Fuente:** https://trello.com/c/B8wT5K34/18-inv-01-configurar-y-contabilizar-inventario-y-costo-de-ventas

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-17 | (nuevo) → INVESTIGATION | Task creado; base = `origin/accounting` (PR #88 integrado), no `main` | delivery-start |
| 2026-11-17 | INVESTIGATION → PLANNING | NEEDS_ARCHITECTURE (ledger de costo nuevo, contrato entre Ventas/Compras/Costeo/Contabilidad); Diseño NO; 2 decisiones de negocio resueltas por la persona | delivery-start |
| 2026-11-17 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |
| 2026-11-18 | ENGINEERING → REVIEW | Implementación completa según PLAN v1; pruebas propias en verde | delivery-build |
| 2026-11-18 | REVIEW → PUBLISH | Quality Gate PASS (0 Critical/High; REV-01 y REV-02 Medium, REV-03 Low abiertos) | delivery-publish |
| 2026-11-18 | PUBLISH (corrección) | REV-01..03 corregidos a pedido de la persona; suite completa 2138 OK; el Quality Gate no se repitió | delivery-build |

## Investigación

### Requerimiento
Tarjeta Trello INV-01 (insumo, no Specification aprobada). Aclaración de la persona: usar la rama `accounting` como base.
- **Objetivo:** registrar los efectos patrimoniales del stock aunque no se mueva dinero.
- Configuración en Inventario: Inventario (Activo) y Costo de ventas (Costos). Identificar y reutilizar la política de valoración/costos existente y documentarla antes de contabilizar.
- Salida por venta: Debe Costo de ventas / Haber Inventario por **costo** de salida (no precio), una sola vez por evento.
- Coordinar la recepción con COM-02: un mismo ingreso de mercadería no genera dos asientos.
- Ajustes solo con contrapartida explícita y justificada por motivo; si falta configuración o costo, bloquear la contabilización y explicar, sin inventar valores.
- Reversiones/devoluciones existentes conservan el costo original, el vínculo y la atomicidad con el stock. Mantener concurrencia y la prohibición de stock negativo.
- Aceptación: (1) vender por 150 con costo 100 → costo 100 e inventario −100 (el ingreso 150 es de VEN-01); (2) reintentar la salida no duplica costo ni stock; (3) recibir una compra integrada no duplica el asiento de COM-02; (4) un fallo contable no deja stock modificado sin asiento.
- Dependencias: CONT-12 (configuración de asientos) y CONT-10 (períodos), ya en `accounting`. Transversal: API y UI donde corresponda, aislamiento por empresa, permisos existentes, `Decimal`, sin conversión de divisas.

### Hechos encontrados
- El catálogo de CONT-12 ya define el evento `INVENTORY_SALE_COST` (Debe `COST_OF_SALES`, Haber `INVENTORY`) y los roles `INVENTORY` (Activo) y `COST_OF_SALES` (Costos): `backend/modules/accounting/domain/posting.py:41-42,70-93`. También `PURCHASE_RECOGNITION` (Debe Inventario/Haber CxP), de Compras (`posting.py:92`). El panel de configuración ya está montado en Inventario (CONT-12, `module-settings`).
- Fachada contable lista: `post_automatic_entry` (idempotente por `(empresa, evento, origin_id)`, exige transacción, nunca omite en silencio con cobertura; `accounting/services.py:535-565`), `check_posting_ready`, `reverse_automatic_entry`, `find_automatic_entry`.
- **No existe costo corriente.** `costing` solo guarda la adopción inicial inmutable (`costing/domain/valuation.py`, `costing/infrastructure/django/models.py`, ADR iniciar-valoracion §6, §9: «el costeo de consumos posteriores queda para tareas siguientes»), con método declarado `weighted_moving_average` y `unit_cost` a 6 decimales. Ningún otro módulo importa `costing` (grep en `backend/modules`). `catalog` no tiene costo de producto; `StockMovement` no lleva dinero (`inventory/domain/movement.py`).
- Las líneas de compra sí traen `unit_price` (`purchases/domain/purchase.py:98-141`), pero la recepción solo registra cantidades: `register_entries` llama `inventory_services.record_movement(..., source_type='purchase_receipt', source_id=receipt_id, source_line=product_id)` (`purchases/infrastructure/adapters.py:63-77`), y `reverse_entries` usa `reverse_source_movements` (`:79-90`).
- La salida por venta ocurre en `DeliverOrder.execute`: `register_outputs` (→ `inventory_services.record_outputs`, todas o ninguna, idempotente por `(sales_order, order_id, producto)`) y luego `posting.recognize_delivery` en la **misma transacción** de la vista (`sales/application/commands.py:196-232`, `sales/infrastructure/adapters.py:126-146,243-253`, `sales/api/views.py:88`). El asiento de ingreso `SALE_DELIVERY` ya lo hace VEN-01.
- No hay devolución de ventas: las salidas por venta no se revierten desde Inventario (`inventory/domain/movement.py:132-146`, «requieren una devolución, que aún no está disponible»); las de recepción se corrigen desde Compras (reversa `reverse_source_movements`).
- Los ajustes (`inventory/domain/adjustment.py:64-99`) tienen motivo de texto libre (≤200) sin catálogo ni cuenta; los movimientos manuales y de apertura no llevan costo.
- COM-02 (PURCHASE_RECOGNITION) está «En validación» en Trello y **ningún módulo de Compras llama todavía a `post_automatic_entry`** (solo Ventas, Cobros y Gastos: `grep post_automatic_entry`).
- `lock_company_stock(company_id)` y `get_company_stock/get_balances` en la fachada de Inventario (`inventory/services.py:98-256`), usadas por Costeo para conciliar bajo bloqueo.
- Migraciones: última de `costing` = `0001`.

### Hipótesis / supuestos no confirmados
- El costo unitario de recepción es el `unit_price` de la línea de compra (impuestos y gastos de compra fuera de alcance, «mantener políticas de costo e impuestos»).
- Productos que ganan stock por ajuste (sin costo) y luego reciben una compra: el promedio arranca con el costo de la recepción; las unidades previas sin costo se consideran al costo promedio resultante. Se marca como limitación visible en el PR.

### Módulos y dependencias relacionadas
`costing` (ledger de costo y fachada nueva), `sales` (orquesta la salida valorizada y el asiento), `purchases` (traslada el costo de cada recepción), `accounting` (sin cambios de contrato), `inventory` (solo lectura de saldos; sin cambios). Dependencias nuevas entre módulos: `sales → costing` y `purchases → costing` solo por la fachada `costing.services`, como opcionales (módulo habilitado).

### Implementaciones similares existentes
`SalesPosting`/`recognize_delivery` y `_posting_errors` (VEN-01), `ExpensePosting` y `ReceivablesPosting` (patrón de adaptador con `post_automatic_entry`), `AdoptValuation` (conciliación bajo `lock_company_stock`).

### Comportamiento actual
Entregar un pedido mueve stock y reconoce el ingreso, pero no registra costo ni asiento de costo de ventas; las recepciones suben stock sin valor.

### Restricciones
`CLAUDE.md`: `Decimal`, `company_id` desde el usuario, dominio sin Django, módulos solo por fachadas, migraciones nuevas, sin dependencias nuevas. Sin conversión de divisas (BOB).

### Riesgos identificados
- Costo desactualizado o ausente → se bloquea la entrega con mensaje accionable (nunca se inventa).
- Doble asiento de recepción con COM-02 → INV-01 **no** asienta recepciones (ver ADR).
- Concurrencia entre recepción y salida sobre el mismo promedio → el ledger se actualiza bajo `lock_company_stock`.
- Empresas con stock y Contabilidad cubierta pero sin Costeo adoptado quedan bloqueadas al entregar: es el comportamiento pedido («si falta costo, bloquear»); mitigación: mensaje que dirige a Costeo.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — tabla y migración nuevas (ledger de costo), contrato nuevo de fachada consumido por Ventas y Compras, y cálculo de dinero (promedio ponderado).

### Diseño requerido
**NO** — no hay pantallas nuevas: la configuración de cuentas ya existe (CONT-12) y los bloqueos se muestran por los avisos de error existentes de Entregar pedido; no se inventa pantalla de costos. Límite declarado: no hay vista del costo promedio por producto.

### Decisiones resueltas (persona, 2026-11-17)
1. **Costo de salida:** promedio móvil ponderado mantenido por Costeo (parte de la valoración inicial y se actualiza con cada recepción de compra).
2. **Ajustes de inventario:** fuera de alcance; siguen solo en stock. Quedan sin asiento y se documenta el límite.
3. Por criterio (documentado en ADR): COM-02 es dueño del asiento de recepción; INV-01 solo alimenta el costo.

## Diseño
No aplica (Diseño requerido: NO).

## Arquitectura
`docs/adr/ADR-contabilizar-inventario-costo-ventas-ledger-de-costo-y-salida-valorizada.md`

## Plan
`docs/plans/PLAN-2026-11-17-contabilizar-inventario-costo-ventas.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
Implementado según PLAN v1, sin cambios de Specification.

- **Dominio** (`costing/domain/cost.py`; INV-01/02/04, AC-03/09): promedio ponderado, costo de línea, `CostEvent` (IN/OUT/IN_REVERSAL) y `CostUnavailable`.
- **Persistencia** (INV-03/06, AC-10): `CostEventModel` + migración `costing/0002_cost_event` (solo `CreateModel`) + `DjangoCostEventRepository(company_id)`.
- **Casos de uso y fachada** (`costing/application/cost_use_cases.py`, `costing/services.py`; AC-02/03/05/07/09): `cost_receipt`, `reverse_receipt_cost`, `cost_outputs`, `is_valued`, bajo `lock_company_stock`. Nueva `inventory.services.get_product_totals`.
- **Compras** (INV-05, AC-03/07): `register_entries` recibe `unit_costs` (precio de la línea de compra) y `StockEntryAdapter` alimenta el costo; la reversa de recepción registra IN_REVERSAL. No crea asiento.
- **Ventas** (AC-01/02/04/05/08/09): `DeliveryCosting` + `DeliveryCostingAdapter`, invocado por `DeliverOrder` tras la salida y el reconocimiento, en la misma transacción. Errores: `inventory_cost_unavailable` y los de configuración/período ya existentes.
- **Pruebas:** `costing/tests/test_cost_ledger.py`, `sales/tests/test_delivery_cost.py`, `purchases/tests/test_receipt_cost.py`; `test_boundaries` permite `sales → costing` y `purchases → costing`.

**Desviaciones respecto al plan:**
1. La prueba existente `DeliveryWithStockTests.test_delivering_with_complete_configuration...` (VEN-01) ahora configura Costeo adoptado y las cuentas de Inventario/Costo de ventas: es el efecto previsto de AC-05 (con cobertura y stock, falta de costo bloquea).
2. Sin cobertura contable y con Costeo sin costo disponible, la entrega no se bloquea y no se registra evento de costo (el plan decía «se actualiza si Costeo está habilitado»; solo se registra cuando hay costo).
3. No se usó `check_posting_ready` previo: `post_automatic_entry` ya rechaza antes de escribir y la transacción de la entrega revierte stock y costo.

**Deuda técnica / límites:** ajustes de inventario sin asiento (decisión de la persona); sin devolución de ventas; unidades sin costo previo se promedian al costo de la primera recepción; sin vista del costo promedio; el frontend no se tocó (el mensaje de error 409 existente se muestra tal cual, pendiente de verificar en publish).

**Corridas propias (no son el Quality Gate):** suite completa del backend 2130 pruebas, 1 falla corregida (deviación 1); `modules.sales` 377 OK; `makemigrations --check` sin cambios; flake8/ruff sin avisos nuevos.

## Review
**Quality Gate: PASS** (subagente aislado, 2026-11-18, diff contra `origin/accounting`). Backend: `manage.py test` 2130 OK (en serie), `makemigrations --check` sin cambios, bandit sin hallazgos, sin secretos ni `float` en el diff. flake8: un aviso nuevo (E128 en `sales/api/views.py:248`) y E501 en la migración generada; ruff sin avisos nuevos. Frontend no tocado (Diseño NO): sin verificación visual ni pruebas de frontend. Límites DDD y aislamiento por `company_id` verificados; todos los AC cubiertos, AC-06 y AC-10 solo en parte.
- REV-01 (Medium, IMPLEMENTATION; **resuelto**): posible deadlock entre el bloqueo por almacén y el de la empresa (no reproducido con hilos).
- REV-02 (Medium, IMPLEMENTATION; **resuelto**): faltan pruebas de casos límite y concurrencia.
- REV-03 (Low, IMPLEMENTATION; **resuelto**, salvo el E501 de la migración generada): `get_product_totals` en memoria, fecha del evento de costo, estilo y límite del promedio tras reversa.
- **Corrección posterior (sin repetir el Quality Gate):** REV-01 con el bloqueo de la empresa antes que el del almacén en recepciones, su reversa y salidas por venta (con Costeo habilitado); REV-02 con pruebas nuevas (AC-06, aislamiento, entrega con fecha distinta, producto sin costo, reversa tras vender, entregas y recepciones simultáneas en dos almacenes); REV-03 con saldos filtrados en la consulta, fecha del evento de costo y E128. Suite completa 2138 OK. Producto repetido y cantidades fraccionarias en pedidos no son alcanzables (Ventas las rechaza). La concurrencia pasa con el arreglo, pero no se demostró que fallara antes.

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/91 (base `accounting`) listo para aprobación humana; no se mergea. **Sensible:** incluye ADR, migración nueva (`costing/0002`) y cálculo de dinero; lo aprueba una persona. REV-01..03 corregidos tras el Quality Gate sin repetirlo.
