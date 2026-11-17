# TASK-contabilizar-ventas-cobros-sin-duplicar: Contabilizar ventas y cobros por partida doble sin duplicar ingresos (VEN-01)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-contabilizar-ventas-cobros-sin-duplicar
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/87
**Fuente:** https://trello.com/c/D5Lgicru/16-ven-01-configurar-y-contabilizar-ventas-y-cobros-sin-duplicar-ingresos

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-17 | (nuevo) → INVESTIGATION | Task creado; base = rama `task/TASK-configurar-asientos-automaticos-modulo` (CONT-12, PR #86), no `main` | delivery-start |
| 2026-11-17 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (lógica financiera, frontera Ventas↔Contabilidad, cambios de reglas de estado); 4 decisiones de negocio resueltas por la persona | delivery-start |
| 2026-11-17 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |
| 2026-11-17 | ENGINEERING (parcial) | Código y pruebas escritos; pruebas de backend sin ejecutar (falta `.env` local) | delivery-build |

## Investigación

### Requerimiento
Tarjeta Trello VEN-01 (insumo, no Specification aprobada). Aclaración de la persona: usar como base `task/TASK-configurar-asientos-automaticos-modulo`.
- **Objetivo:** integrar Ventas con partida doble distinguiendo reconocimiento de venta y cobro.
- Configuración en Ventas: cuenta de Ingresos por ventas, Cuentas por cobrar y cuentas de cobro por método.
- Un único evento existente confirma la venta: Debe Cuentas por cobrar / Haber Ingresos, una sola vez. Cobro: Debe Caja/Banco / Haber Cuentas por cobrar.
- Venta y pago simultáneos: se admite asiento directo Caja/Banco contra Ingresos si no se generó reconocimiento separado; nunca ambos caminos por el mismo importe.
- Pagos parciales y mixtos, vínculos a venta/pago, transacción atómica, idempotencia; conservar controles de saldo y concurrencia.
- Costo/stock queda como evento de INV-01. Adaptar anulaciones existentes sin introducir reembolsos. Preservar descuentos existentes; no ampliar alcance tributario.
- Aceptación: (1) venta 1.000 a crédito + cobro 300 → Ingresos 1.000, CxC 700, Caja 300; (2) venta al contado de 500 → Ingresos 500, no 1.000; (3) reintentos y dos pagos concurrentes no duplican asientos ni exceden saldo.
- Dependencias: CONT-12 (configuración, `task/TASK-configurar-asientos-automaticos-modulo`), CONT-10 (períodos, ya en esa base). Transversal: API y UI, aislamiento por empresa, permisos existentes, `Decimal`, BOB, sin conversión de divisas; trabajar sobre `accounting` (no está en `main`).

### Hechos encontrados
- **La fachada ya existe y nadie la usa:** `post_automatic_entry`, `check_posting_ready`, `reverse_automatic_entry` (`backend/modules/accounting/services.py:505-575`) con eventos `SALE_RECOGNITION` (Debe `RECEIVABLE` / Haber `SALES_INCOME`) y `SALE_PAYMENT` (Debe `MONEY` por método / Haber `RECEIVABLE`) (`accounting/domain/posting.py:70-71`). El panel de configuración de Ventas ya está montado (CONT-12, `TASK-configurar-asientos-automaticos-modulo.md:101`).
- **Evento que confirma la venta:** `StartOrderPreparation` («Confirma el pedido (NEW → IN_PREPARATION)», `sales/application/commands.py:144-153`; `Order.start_preparation`, `sales/domain/order.py:320-325`). Los mensajes ya hablan de «pedido confirmado» (`order.py:302`).
- **Cobro actual:** `RegisterPayment` (`commands.py:211-238`) corre dentro de `transaction.atomic` con la fila del pedido bloqueada (`_run`, `sales/api/views.py:80-89`), valida saldo (`order.py:370-371`), es idempotente por `idempotency_key` con huella (`commands.py:227-233`) y llama a `PaymentLedgerAdapter.record` → `record_entry` del libro anterior, origen `PRODUCT` (`sales/infrastructure/adapters.py:169-198`). `OrderPaymentView` usa `PaymentLedgerAdapter` (`views.py:264-271`).
- **Un cobro es posible en cualquier estado salvo CANCELLED** con saldo > 0, incluido NEW (`order.py:270-272`, `362-363`).
- **El total puede cambiar tras confirmar:** ítems, cantidades y descuento son editables en NEW/IN_PREPARATION/READY (`OPEN_STATUSES`, `order.py:30`, `ensure_editable` `order.py:391-393`); solo se impide bajar el total por debajo de lo pagado (`order.py:314-315`, `408-414`). El total = subtotal − descuento (`order.py:234-235`); no hay impuestos.
- **Cancelar** es posible desde NEW/IN_PREPARATION/READY y **conserva los pagos** (no hay reembolsos): `order.py:345-353`, prueba `sales/tests/test_api.py:486`. `PaymentStatus.REFUNDED` existe pero ningún flujo lo produce (`sales/domain/enums.py:14-22`).
- **Entrega** registra salidas de inventario (`commands.py:166-197`); no contabiliza nada (el costo es INV-01).
- **Libro anterior vs. motor:** el motor rechaza un origen ya presente en el libro anterior (`ORIGIN_IN_LEGACY_LEDGER`, `accounting/domain/journal.py:24`) y `record_entry` documenta que, al migrar un origen, su llamante deja de usarlo (`accounting/services.py:229-231`). `journal_balances` no incluye el libro anterior (`services.py:448-455`).
- **Cobertura:** `coverage_status` decide por fecha si una operación debe contabilizarse (módulo deshabilitado, anterior al corte o hueco ⇒ no) (`services.py:165-175`); `post_automatic_entry` es idempotente por `(empresa, evento, origin_id)` y su reintento no se revalida (`services.py:540-548`).
- **Fronteras:** `ALLOWED_DEPENDENCIES['sales']` ya incluye `accounting` (`sales/tests/test_boundaries.py:15-20`); solo desde `infrastructure/adapters.py` y por `services`.
- **Frontend:** detalle de pedido y componente de pagos en `features/sales/pages/order-detail` y `components/order-payments` (clave de idempotencia por formulario según `ADR-pagos-ventas-libro-entradas-integracion-e-idempotencia`); los 409 de Ventas tienen la forma `{code, detail}` (`views.py:65-69, 95-96`).

### Hipótesis / supuestos no confirmados
- La fecha contable del reconocimiento es la **fecha de confirmación** (`Clock.today()`), no `order_date`; la del cobro es `payment_date`. Si la persona necesitara reconocer en `order_date`, es un cambio de Specification.
- Pedidos de total 0 (descuento = subtotal) no generan asiento (el motor exige importe > 0); no hay nada que cobrar.
- El mensaje de configuración faltante se muestra tal como lo devuelve Contabilidad (español); la traducción de esos mensajes es la deuda ya declarada en CONT-12 REV-05.

### Decisiones resueltas (persona, 2026-11-17)
1. **Evento de reconocimiento = confirmar el pedido** (NEW → IN_PREPARATION), con el total vigente. Desde ahí, con el pedido contabilizado, no se admiten cambios que alteren el total (ítems, cantidades, descuento).
2. **Cobrar un pedido NUEVO** (sin confirmar), cuando Contabilidad cubre la fecha: **se exige confirmarlo antes** (409). Por eso **no se implementa el asiento directo Caja/Ingresos** que la tarjeta «admite»: el cobro nunca ocurre sin reconocimiento, así que el contado = reconocimiento + cobro (Ingresos 500, CxC 0, Caja 500) y nunca hay dos caminos para el mismo importe.
3. **Cancelar** con Contabilidad cubriendo: **se bloquea si el pedido tiene cobros** (hasta que exista reembolso); sin cobros se revierte el reconocimiento con las cuentas originales.
4. **Libro anterior:** los cobros que se contabilizan por partida doble **dejan de crear entrada en el libro anterior** (`PRODUCT`).
- Resto por criterio, documentado en ADR/PLAN (selección de camino por existencia de reconocimiento, fecha del reconocimiento, etc.).

### Módulos y dependencias relacionadas
`sales` (comandos, puerto, adaptador, vistas, frontend), `accounting` (una función de fachada aditiva: `find_automatic_entry`). Sin migraciones ni dependencias nuevas (`sales → accounting` ya permitida).

### Implementaciones similares existentes
`RegisterPayment` + `PaymentLedgerAdapter` (puerto y adaptador del libro anterior), `DeliverOrder` + `StockOutput` (integración opcional dentro de la transacción), fachada CONT-12.

### Comportamiento actual
Con Contabilidad habilitada, cada cobro crea una entrada de una cuenta (libro anterior); confirmar no genera nada; sin configuración de cuenta del método el cobro se rechaza. No hay reconocimiento de ingresos por partida doble.

### Restricciones
`CLAUDE.md`: `Decimal`, aislamiento por `company_id`, dominio sin Django, Ventas solo usa la fachada `accounting.services` desde infraestructura, sin texto hardcodeado en frontend (es/en/pt), sin `any`, avisar antes de instalar dependencias (ninguna). Moneda BOB sin conversión.

### Riesgos identificados
- **Cambio de reglas de estado** con Contabilidad cubriendo (total bloqueado, cobro exige confirmar, cancelar con cobros bloqueado): documentado y acotado a empresas con cobertura; sin Contabilidad el comportamiento no cambia.
- **Doble camino por pedido** (pedido confirmado antes de la cobertura y cobrado después): se resuelve eligiendo el camino por la existencia del reconocimiento (ADR §3); prueba explícita de «nunca ambos».
- **Concurrencia:** dos cobros simultáneos; se apoya en el bloqueo de la fila del pedido + idempotencia por `origin_id` = id del pago; prueba con hilos.
- **Período cerrado / fecha fuera de cobertura al cobrar** deshace el cobro con mensaje accionable (EDGE).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — lógica financiera nueva sobre dos módulos, cambios de transiciones/reglas de pedido y decisión sobre libros coexistentes; se fija en un ADR.

### Diseño requerido
**SI** — el detalle del pedido debe mostrar los rechazos de contabilización (configuración faltante, pedido sin confirmar, total bloqueado, cancelación bloqueada) de forma accionable; sin pantallas nuevas.

## Diseño
`docs/design/DDR-contabilizar-ventas-cobros-sin-duplicar-errores-accionables-en-detalle-de-pedido.md`

## Arquitectura
`docs/adr/ADR-contabilizar-ventas-cobros-sin-duplicar-puerto-reconocimiento-y-cobro.md`

## Plan
`docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
Implementado según PLAN v1, sin cambios de Specification.

- **Fachada** (`accounting/services.py`): `find_automatic_entry` (INV-01/02).
- **Puerto y adaptador** (`sales/application/ports.py`, `sales/infrastructure/adapters.py`): `SalesPosting` / `SalesPostingAdapter` reemplazan a `PaymentLedger`; reconocimiento, cobro por un único camino (asiento si el pedido está reconocido; libro anterior si es anterior a la cobertura), reversión y traducción de errores del motor (AC-01..AC-10).
- **Comandos** (`sales/application/commands.py`): `StartOrderPreparation` reconoce al confirmar; `RegisterPayment` contabiliza antes de guardar; `AddOrderItem`/`ChangeOrderItemQuantity`/`RemoveOrderItem`/`ApplyOrderDiscount` bloquean el total reconocido (AC-07); `CancelOrder` revierte o rechaza con cobros (AC-08). `OrderRuleViolation` gana `extra` (para `issues`).
- **Vistas** (`sales/api/views.py`): cablean el adaptador y exponen `extra` en el 409 (API-01..04).
- **Frontend** (AC-14): `OrderRuleError.postingIssues`, alerta con enlace a la configuración de Ventas en el detalle (patrón de alerta existente; sin pantalla nueva), claves es/en/pt en `SALES.ORDER_DETAIL.*`.
- **Pruebas:** `sales/tests/test_sales_posting.py` (AC-01..AC-13, con hilos), `FindTests` en `test_posting_service`, ajuste de `test_payment_ledger.py` (corte futuro para ejercitar el camino anterior); specs de `order-detail` y `orders-api.service`.

**Desviaciones respecto al plan:** ninguna de alcance. `StartOrderPreparation`/`CancelOrder` reciben además `actor` (y `Clock`) para fechar y atribuir los asientos.

**Estado de verificación (propia, no es el Quality Gate):** frontend: `ng lint` OK, `i18n:check` 2178 claves y 0 faltantes, suite completa 1574 OK. **Backend: las pruebas NO se han ejecutado** — el worktree no tiene `backend/.env` y copiarlo de otro worktree fue denegado; solo se comprobó sintaxis y flake8 de lo nuevo. Pendiente de correr: `manage.py test modules.sales modules.accounting modules.receivables`, `makemigrations --check` (no hay migraciones nuevas).

**Deuda técnica / pendiente:** mensajes de configuración faltante solo en español (deuda de CONT-12 REV-05); sin endpoint de verificación previa; revisión visual en navegador pendiente para `delivery-publish`.

## Review
_Pendiente_

## Publicación
_Pendiente_
