# TASK-reconocer-compras-mercaderia-deuda-proveedores: Reconocer compras de mercadería y deuda con proveedores (COM-02)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-reconocer-compras-mercaderia-deuda-proveedores
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/89
**Fuente:** https://trello.com/c/tocsSz1L/19-com-02-reconocer-compras-de-mercader%C3%ADa-y-deuda-con-proveedores

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-17 | (nuevo) → INVESTIGATION | Task creado; base = `origin/accounting` (indicación de la persona), no `main` | delivery-start |
| 2026-11-17 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (lógica financiera, frontera Compras↔Contabilidad↔Inventario, reglas de recepción/reversión) | delivery-start |
| 2026-11-17 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |

## Investigación

### Requerimiento
Tarjeta Trello COM-02 (insumo, no Specification aprobada). Aclaración de la persona: usar la rama `accounting` como base.
- **Objetivo:** separar adquisición de inventario y pago al proveedor.
- Configuración dentro de Compras: Inventario (Activo) y Cuentas por pagar (Pasivo).
- Revisar el flujo real de confirmación/recepción y definir **un único evento** de reconocimiento; borrador o pedido al proveedor no reconocen.
- A crédito: Debe Inventario / Haber Cuentas por pagar por el importe reconocido; COM-01 liquida la deuda. Coordinar recepciones parciales y reconocimiento previo a recepción; documentar diferencias temporales y cuentas; no inventar asientos al pagar.
- Sin Gastos operativos por comprar mercadería; mantener políticas de costo e impuestos sin ampliar alcance tributario; guardado atómico e idempotente; enlace compra/recepción/asiento; preservar el corte de CONT-07.
- Aceptación: (1) compra 1.000 → Inventario Debe 1.000 / Proveedores Haber 1.000; (2) pagar 300 deja Proveedores 700 sin segundo inventario ni gasto; (3) reintentar recepción y reconocer por ambos módulos no duplica; (4) borrador no altera cuentas; fallo del asiento no deja reconocimiento parcial.
- Dependencias: CONT-12, CONT-10. Coordinación INV-01 ↔ COM-02 sobre un único evento y dueño del asiento de recepción. Transversal: API y UI, aislamiento por empresa, `Decimal`, BOB, sin conversión de divisas.

### Hechos encontrados
- **El catálogo ya tiene los eventos:** `PURCHASE_RECOGNITION` (Debe `INVENTORY` / Haber `PAYABLE`) y `PURCHASE_PAYMENT` (Debe `PAYABLE` / Haber `MONEY`) y los roles `INVENTORY` (Activo) y `PAYABLE` (Pasivo) (`backend/modules/accounting/domain/posting.py:45-47, 94-95`). Nadie los usa; el panel de configuración es dirigido por datos (CONT-12).
- **Fachada disponible:** `check_posting_ready`, `post_automatic_entry` (idempotente por `(empresa, evento, origin_id)`, `services.py:530-573`), `find_automatic_entry`, `automatic_entry_origins`, `reverse_automatic_entry` (`services.py:507-612`), `coverage_status` (`services.py:167`) y errores `PostingConfigurationMissing`, `FiscalPeriodClosed`, `DateOutsideFiscalPeriod`, `JournalValidationError`, `JournalConflict` (usados por Ventas en `sales/infrastructure/adapters.py:300-316`).
- **Compras no contabiliza nada hoy:** `ConfirmPurchase` (`purchases/application/purchase_commands.py:121-134`), `RegisterReception` (`receipt_commands.py:55-103`) y `RegisterPayment` (`payment_commands.py:20-69`, solo guarda la clasificación de egreso) no llaman a `accounting`. No hay llamadas a `PURCHASE_PAYMENT` fuera del catálogo (la entrada de una cuenta del libro anterior no se usa desde Compras); el pago de Compras (COM-01) aún no genera asiento.
- **Flujo real:** borrador → confirmada (`Purchase.confirm`, `purchase.py:354-366`) → recepciones parciales/completas (`Purchase.receive`, `purchase.py:381-437`, cantidad ≤ pendiente) → pagos desde confirmada (`can_pay`, `purchase.py:338-342`; el monto no supera el saldo `total − pagado`, `purchase.py:452-461`). Cancelar solo sin actividad (`can_cancel`, `purchase.py:327-330`); líneas editables solo en borrador (`ensure_editable`, `purchase.py:313-316`). Costo por línea = `quantity × unit_price` redondeado a 2 decimales (`purchase.py:110-111`).
- **Recepción:** `RegisterReception` ejecuta bajo `purchases.get(for_update=True)` (`receipt_commands.py:71`), es idempotente por `receipt_id` (`receipt_commands.py:74-78`), registra entradas de stock con modo `INVENTORY`/`DOCUMENTAL` (`receipt_commands.py:89-103`) y se ejecuta dentro de `transaction.atomic` vía `_run` (`purchase_views.py:107-110`). `RevertReception` revierte stock y estado en la misma transacción (`receipt_commands.py:125-154`).
- **Inventario:** el movimiento de entrada usa `source_type='purchase_receipt'`, `source_id=receipt.id` (`purchases/infrastructure/adapters.py:44, 63-77`); Inventario no contabiliza (no importa `accounting`).
- **Fronteras:** `ALLOWED_DEPENDENCIES['purchases'] = {accounting, catalog, inventory}` (`sales/tests/test_boundaries.py:25`); `accounting` no puede depender de `purchases` (`accounting/tests/test_coverage.py:320-324`). `purchases/infrastructure/adapters.py:100-118` ya consume `accounting_services` (clasificaciones y cobertura).
- **Cobertura/CONT-07:** `coverage_status(fecha)` decide por fecha si crear asiento (módulo deshabilitado, anterior al corte o hueco ⇒ no) (`services.py:167-178`); un asiento publicado no se revalida al reintentar (`services.py:547-555`).
- **Precedente:** VEN-01 (`TASK-contabilizar-ventas-cobros-sin-duplicar`): puerto `SalesPosting`, adaptador, 409 `posting_configuration_missing` con `issues`, enlace a la configuración en el diálogo (`sales/infrastructure/adapters.py:177-317`, `frontend/.../sales/components/delivery-dialog`).
- **Frontend de Compras:** `features/purchases/pages/{reception-form,reception-detail}` y `components/receipt-revert-dialog` (manejo de 400/409 con `ReceiptApiError`, `reception-form.component.ts:254-263`, `receipt-revert-dialog.component.ts:64-69`).

### Hipótesis / supuestos no confirmados
- El evento de reconocimiento es la **recepción** (la tarjeta descarta borrador y pedido; no dice cuál otro). Se documenta en el ADR; si la persona prefiere «al confirmar», es un cambio de Specification.
- Se reconoce también sin Inventario habilitado y para líneas sin control de stock.
- La fecha contable es la fecha de la recepción; la reversión usa la fecha de hoy (patrón de Ventas).
- Pagos anticipados dejan Proveedores deudor temporalmente; no se crea cuenta de anticipos.
- Las recepciones históricas no se regularizan aquí.

### Módulos y dependencias relacionadas
`purchases` (dominio, comandos, adaptador, vistas, frontend), `accounting` (solo consumo de la fachada, sin cambios previstos), `inventory` (sin cambios; fija el dueño del asiento), dependencias CONT-12/CONT-10 ya integradas en `accounting`.

### Implementaciones similares existentes
`SalesPostingAdapter` y los comandos de pedido de VEN-01; `StockEntryAdapter` (integración opcional en la misma transacción).

### Comportamiento actual
Ver «Hechos». Con Contabilidad habilitada, recibir una compra no deja rastro contable.

### Restricciones
`CLAUDE.md`: `Decimal`, `company_id`, dominio sin Django, módulos solo por `services`, sin migraciones editadas, sin dependencias nuevas, sin texto hardcodeado en frontend (es/en/pt), sin `any`.

### Riesgos identificados
Doble asiento con INV-01 (mitigado por ADR §2 y prueba de origen); recibir exige configuración con cobertura (cambio acotado); reversión bloqueada por período cerrado; recepciones históricas sin asiento; saldo deudor temporal por pagos anticipados.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — lógica financiera nueva, frontera Compras↔Contabilidad↔Inventario con decisión de dueño del asiento y cambios de reglas de recepción/reversión.

### Diseño requerido
**SI** — rechazos accionables y enlace al asiento en recepción y reversión (sin pantallas nuevas).

## Diseño
`docs/design/DDR-reconocer-compras-mercaderia-deuda-proveedores-errores-accionables-y-asiento-en-recepcion.md`

## Arquitectura
`docs/adr/ADR-reconocer-compras-mercaderia-deuda-proveedores-evento-recepcion-y-asiento.md`

## Plan
`docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
