# TASK-contabilizar-ventas-cobros-sin-duplicar: Contabilizar ventas y cobros por partida doble sin duplicar ingresos (VEN-01)

**Etapa actual:** PUBLISH
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
| 2026-11-17 | ENGINEERING → REVIEW | Implementación completa según PLAN v1; pruebas propias en verde | delivery-build |
| 2026-11-17 | REVIEW (corrección) | REV-01 resuelto por PLAN v2 (AC-15) aprobado por la persona; sin repetir el Gate | delivery-start / delivery-build |
| 2026-11-17 | REVIEW → PUBLISH | Quality Gate PASS (0 Critical/High; REV-01..02 Medium y REV-03..09 Low abiertos) | delivery-publish |
| 2026-11-17 | PUBLISH → PLANNING → ENGINEERING | Cambio de Specification pedido por la persona: reconocer al entregar y anticipos de clientes; PLAN v3, ADR nuevo | delivery-start |
| 2026-11-17 | ENGINEERING → REVIEW | Implementación completa según PLAN v3; pruebas propias en verde | delivery-build |
| 2026-11-17 | REVIEW → PUBLISH | Quality Gate PASS (PLAN v3; 0 Critical/High; REV-10/11 Medium y Low abiertos) | delivery-publish |

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

### Actualización 2026-11-17 — reconocimiento al entregar y anticipos (PLAN v3)
Instrucción de la persona (cambio de Specification explícito): el ingreso se reconoce al **entregar** (LISTO → ENTREGADO) y los cobros anteriores a la entrega son **anticipos de clientes** (rol nuevo de Pasivo, configurable). Confirmar y marcar listo no generan asiento; el total sigue estable tras confirmar; cobrar un pedido NUEVO sigue rechazado; los cobros previos: Debe Caja/Bancos / Haber Anticipos; la entrega: Haber Ingresos por el total, Debe Anticipos por los vigentes del pedido y Debe Cuentas por cobrar por el resto (sin líneas de importe cero); cobros posteriores: Debe Caja/Bancos / Haber Cuentas por cobrar; cancelar sin entregar y sin cobros: sin asiento, con cobros: `order_has_payments_posted`. Transición explícita para pedidos con reconocimiento anterior y para cobros fuera de cobertura. Sin pagos obligatorios y sin «Entregar y cobrar» (no existe en la interfaz).

**Hechos nuevos (verificados en el código):**
- `Event` solo admite una línea de Debe y una de Haber (`accounting/domain/posting.py:52-66`) y `post_automatic_entry` arma exactamente dos líneas (`accounting/services.py:556-560`): la entrega necesita una línea extra de Debe y omitir líneas de importe cero.
- El panel y la API de configuración son dirigidos por datos (rol/eventos del catálogo): el rol y los eventos nuevos aparecen sin tocar el componente (`accounting/application/posting.py:157-189`, fixtures del panel).
- `DeliverOrder` ya ejecuta el cambio de estado y la salida de almacén dentro de la transacción con la fila del pedido bloqueada (`sales/application/commands.py:166-197`, `sales/api/views.py:234-241`); el asiento de entrega se suma ahí.
- El estado contable de un pedido se puede deducir del libro por origen (`find_automatic_entry`, `services.py`), sin bandera ni migración: `SALE_RECOGNITION` ⇒ reconocido al confirmar (histórico), `SALE_DELIVERY` ⇒ reconocido al entregar.
- No existe una acción «Entregar y cobrar» en el frontend ni en el backend (búsqueda en `features/sales` y `modules/sales`).
- Pedidos entregados no se cancelan (`OPEN_STATUSES`, `sales/domain/order.py:30`, `345-353`).

**Decisiones adoptadas por criterio (documentadas en ADR v2/PLAN v3):** fecha contable de la entrega = fecha de entrega efectiva; bloqueo de total con cobertura y estado ≠ NUEVO; ruteo de cada cobro por el estado contable del pedido; los casos sin tratamiento definido se **bloquean** con error claro (`order_has_unposted_payments`, `delivery_date_not_covered`).

**Decisiones pendientes (no bloquean):** tratamiento de pedidos con cobros fuera de cobertura entregados con cobertura (hoy bloqueados); tratamiento de pedidos ya reconocidos al confirmar y cancelados con cobros (hoy bloqueado).

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
`docs/adr/ADR-contabilizar-ventas-cobros-sin-duplicar-reconocimiento-al-entregar-y-anticipos.md` (vigente; reemplaza parcialmente a `docs/adr/ADR-contabilizar-ventas-cobros-sin-duplicar-puerto-reconocimiento-y-cobro.md`)

## Plan
`docs/plans/PLAN-2026-11-17-contabilizar-ventas-cobros-sin-duplicar.md` (v3, COMPLETO) · Specification readiness: READY

## Implementación
Implementado según **PLAN v3** (reconocer al entregar y anticipos de clientes), sin cambios adicionales de Specification. Las notas de implementación de v1/v2 (reconocer al confirmar) quedan reemplazadas.

- **Catálogo de Contabilidad** (`accounting/domain/posting.py`; AC-01): rol `CUSTOMER_ADVANCES` (Pasivo, sin códigos ni IDs fijos), eventos `SALE_ADVANCE` y `SALE_DELIVERY` (primer evento con dos líneas de Debe: `Event.extra_debit_role`), `SALE_RECOGNITION` queda como evento histórico (`active=False`: no se muestra ni se configura, pero se reconoce para cobrar y revertir pedidos antiguos); `events_for`/`modules_using` ajustados. Resolución de cuentas solo para las líneas que existen (`resolve_event(..., skip_roles)`).
- **Fachada** (`accounting/services.py`; INV-02/03/07, AC-06/07): `post_automatic_entry(..., advance_applied=None)` (línea extra y sin líneas de importe cero; valida coherencia del importe) y `automatic_entry_origins(...)` (una consulta, solo de la empresa; `DjangoJournalRepository.origins_with`). Sin migraciones.
- **Puerto y adaptador de Ventas** (`sales/application/ports.py`, `sales/infrastructure/adapters.py`; AC-02..AC-16): `SalesPosting` rediseñado (`recognition_state`, `locks_total`, `has_posted_payments`, `record_payment`, `recognize_delivery`, `reverse_recognition`); estado contable deducido del libro (`AT_CONFIRM`/`AT_DELIVERY`), ruteo de cada cobro (cobro/anticipo/libro anterior), entrega con anticipos aplicados, bloqueos de transición (`order_has_unposted_payments`, `delivery_date_not_covered`) y traducción de errores del motor; los `issues` del 409 llevan `code`, `role`, `subject`, `message` y `params`.
- **Comandos y vistas** (`commands.py`, `views.py`): `StartOrderPreparation` vuelve a no contabilizar; `DeliverOrder` reconoce en la misma transacción que la salida de almacén; `CancelOrder` bloquea con cobros contabilizados y revierte solo reconocimientos anteriores; el bloqueo de total usa `locks_total`.
- **Frontend** (AC-17): el diálogo de entrega muestra los faltantes de configuración con enlace a la configuración de Ventas; el detalle del pedido ya lo hacía (v1). Panel de configuración sin cambios: muestra el rol y los eventos nuevos por datos.
- **Pruebas:** `sales/tests/test_sales_posting.py` (reescrito: AC-02..AC-16 con Contabilidad real y concurrencia con hilos), `test_sales_posting_application.py` (comandos con puerto falso), `DeliveryEventTests` y ajustes en `accounting/tests/test_posting_*`; spec del diálogo de entrega.

**Desviaciones respecto al plan:** ninguna de alcance. Los `issues` del 409 incluyen además `role` y `params` (para que el cliente pueda traducirlos más adelante).

**Verificación propia (no es el Quality Gate):** backend `manage.py test` 2018 OK (+8 de comandos con puerto falso), `makemigrations --check` sin cambios; frontend `ng lint` OK, `i18n:check` 2180 claves y 0 faltantes, suite completa 1590 OK, `ng build` OK.

**Deuda técnica / pendiente:** decisiones pendientes de negocio (pedidos con cobros sin asiento entregados con cobertura; pedidos reconocidos al confirmar y cancelados con cobros: hoy se bloquean); mensajes de configuración faltante solo en español; el aviso de «método inactivo» y el panel de Ventas (REV-03..09 y mejora del mensaje) siguen pendientes; revisión visual pendiente para `delivery-publish`.

## Review
**Quality Gate (PLAN v3): PASS** (subagente aislado, 2026-11-17). Backend: `manage.py test` 2026 OK, `makemigrations --check` sin cambios, bandit sin hallazgos; flake8/ruff no instalados (no realizado; revisión manual de líneas >120). Frontend: `npm run lint` OK, `i18n:check` 2180 claves y 0 faltantes, `npm run build` OK, `ng test` 1590 de 1590 OK; `npm audit` 2 moderate preexistentes (`hono`). Fronteras DDD, aislamiento por empresa, forma del 409 y los puntos (a)-(l) verificados. **Revisión visual: no verificada** (no se levantó la aplicación con sesión).
- Resueltos: REV-01 (PLAN v2, ya reemplazado por v3), REV-02 (ADR), REV-03 (pruebas con puerto falso).
- Abiertos Medium (huecos de pruebas, no de comportamiento): REV-10 (falla del asiento con salida de almacén), REV-11 (cobro concurrente con la entrega); REV-05 (spec del cobro con `issues`) sigue abierto como Low.
- Abiertos Low: REV-04, 05, 06, 07, 08, 09, 12, 13, 14, 15.

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/87 (base `accounting`) listo para aprobación humana; no se mergea. Incluye ADR (reconocer al entregar y anticipos de clientes) y cambia reglas de pedidos contabilizados: lo aprueba una persona. Sin migraciones. Pendientes: decisiones de negocio (cobros sin asiento entregados con cobertura; pedidos reconocidos al confirmar y cancelados con cobros), hallazgos REV-10/11 (Medium, pruebas) y Low, revisión visual y flake8 no realizados.
