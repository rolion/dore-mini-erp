# ADR-ciclo-pedido-entrega-cobro-modelo-dominio: Agregado `Order` (ítems y pagos), máquina de estados y estado de pago derivado

**Estado:** Propuesto
**Task relacionado:** TASK-ciclo-pedido-entrega-cobro
**Fecha:** 2026-10-08

## Contexto
No existe `backend/modules/sales`. REQ-SAL-001..016 piden pedidos con ítems, descuento, estados logísticos, cancelación con motivo, pagos parciales y un `PaymentStatus` derivado e independiente del estado de entrega. `docs/architecture/ddd.md:327-511` define `Order` como agregado raíz (con `OrderItem` y `Payment`), los value objects `OrderStatus`, `PaymentStatus`, `SalesChannel`, `PaymentMethod`, las reglas y los métodos del agregado; `:880-912` pide separar entidad y modelo Django "especialmente en Sales". Patrón ya fijado por `catalog` y `customers` (dataclass de dominio sin Django, validadores que acumulan errores por campo, repositorio como interfaz de dominio, casos de uso con `execute`). La investigación dejó ambigüedades de negocio que el usuario resolvió en esta etapa (2026-10-08):

- **"Confirmar"** = pasar de NEW a IN_PREPARATION (no hay estado nuevo).
- **Editable hasta READY:** datos, ítems y descuento se editan en NEW, IN_PREPARATION y READY.
- **Transiciones lineales estrictas;** cancelar desde NEW, IN_PREPARATION o READY; DELIVERED y CANCELLED son terminales.
- **Pagos:** sin sobrepago; sin pagos nuevos en pedidos cancelados; los pagos existentes se conservan; REFUNDED existe en el modelo pero sin acción de reembolso (no hay REQ).
- **Alcance:** un solo task y un PR.

## Decisión

**Módulo y capas.** Nuevo bounded context `backend/modules/sales/` con `domain/`, `application/`, `infrastructure/django/`, `api/`, siguiendo el molde de `customers`. El dominio no importa Django.

**Agregado `Order`** (dataclass). `OrderItem` y `Payment` son entidades **internas** del agregado: solo se modifican por métodos de `Order`, porque las invariantes que los cruzan (total ≥ pagado, pago ≤ saldo, estado de pago) exigen consistencia conjunta.

- `Order`: `id` (UUID), `customer_id` (UUID o `None`), `status`, `payment_status`, `sales_channel`, `order_date`, `expected_delivery_date` (opcional), `delivered_date` (opcional), `discount`, `notes`, `cancellation_reason`, `cancelled_at`, `items`, `payments`, `created_at`, `updated_at`.
- **Derivados** (calculados por el agregado tras cada mutación; nunca se asignan desde fuera): `subtotal` (Σ subtotales de ítems), `total = subtotal − discount`, `paid_total` (Σ pagos), `balance = total − paid_total`, `payment_status`.
- `OrderItem`: `id`, `product_id`, `product_name` y `unit_price` (**snapshot** tomado en el servidor al agregar; el cliente HTTP nunca envía precio), `quantity`, `subtotal = unit_price × quantity`.
- `Payment`: `id`, `amount`, `payment_method`, `payment_date`, `reference` (opcional), `created_at`. Sin campo `status` ni anulación en el MVP (ver consecuencias).

**Value objects (enumeraciones cerradas en el dominio):** `OrderStatus` (NEW, IN_PREPARATION, READY, DELIVERED, CANCELLED), `PaymentStatus` (PENDING, PARTIAL, PAID, REFUNDED), `SalesChannel` (WHATSAPP, FACEBOOK, INSTAGRAM, STORE, FAIR, OTHER), `PaymentMethod` (CASH, QR, BANK_TRANSFER, CARD, OTHER). Los códigos son los de `ddd.md`; las etiquetas en español ("Venta directa", "Transferencia") son de UI. `REFUNDED` existe como valor pero **ningún flujo lo produce** en este task.

**Dinero.** `Decimal` en todo el flujo; se rechazan `float` y `bool`; máximo 2 decimales; rango 0 … 9 999 999 999,99 (mismo criterio que `Product.sale_price`). Se crea `backend/shared/domain/money.py` con una función de validación/normalización de importes (no un value object con moneda: la moneda es única e implícita, Bs) porque Sales sería la tercera copia del validador de `catalog/domain/product.py:26-43`. **No se refactoriza `catalog` en este task** (deuda anotada). El monto de un pago es > 0; el descuento es ≥ 0. **Enmienda (plan v2, REV-03, aprobada por el usuario):** el precio de un ítem también es ≥ 0 (un obsequio o muestra puede costar 0, como permite Catalog); un pedido solo de obsequios tiene total 0 y `payment_status` PAID por la regla de total 0 ya prevista.

**Invariantes y reglas (todas en `Order`):**
1. `quantity` entero en 1 … 100 000. Un mismo `product_id` no puede repetirse en el pedido (agregar uno existente se rechaza; se modifica su cantidad).
2. `0 ≤ discount ≤ subtotal`; `total ≥ 0`.
3. **Edición abierta** (datos, ítems, descuento) solo con `status ∈ {NEW, IN_PREPARATION, READY}`.
4. **Nunca `total < paid_total`:** cualquier cambio de cantidad, ítem o descuento que lo provoque se rechaza. Tampoco puede quedar `discount > subtotal` tras quitar o reducir ítems (se rechaza; el usuario ajusta el descuento primero).
5. **Un pedido puede estar vacío solo en NEW.** `prepare` exige ≥ 1 ítem; en IN_PREPARATION y READY no se puede quitar el último ítem (REQ-SAL-004: "un pedido confirmado no puede quedar sin ítems").
6. **Transiciones** (métodos del agregado, no asignación): `start_preparation()` NEW→IN_PREPARATION; `mark_ready()` IN_PREPARATION→READY; `deliver(delivered_date, today)` READY→DELIVERED; `cancel(reason)` desde NEW/IN_PREPARATION/READY→CANCELLED. Cualquier otra combinación falla con regla `invalid_transition`; un cancelado nunca se entrega.
7. **Cancelación:** `reason` obligatorio (recortado, 1 … 500 caracteres); guarda `cancelled_at` y `cancellation_reason`; **conserva ítems y pagos**. "Conserva su historial" se entiende como no perder datos (no hay borrado), no como una bitácora de transiciones.
8. **Fechas:** `expected_delivery_date ≥ order_date`; `delivered_date` por defecto hoy, `≥ order_date` y `≤ hoy`; `payment_date ≤ hoy`; `order_date` sin restricción de pasado. "Hoy" lo inyecta la capa de aplicación (el dominio no lee el reloj).
9. **Pagos:** `register_payment(amount, method, payment_date, reference, today)` exige `amount > 0` (≤ 2 decimales), **`amount ≤ balance`** (sin sobrepago), pedido **no cancelado** (se admite en DELIVERED mientras haya saldo) y `reference` ≤ 100 caracteres. Los pagos no se editan ni se eliminan.
10. **`payment_status` derivado** (REQ-SAL-012/016), independiente de `status`: sin ítems → PENDING; con ítems y `paid_total ≥ total` → PAID (cubre el total 0 por descuento del 100 %); `0 < paid_total < total` → PARTIAL; en otro caso PENDING. Un pedido cancelado **conserva** el estado derivado de sus pagos. `DELIVERED` no implica `PAID` y viceversa.
11. **Acciones disponibles** (consulta del propio agregado, para que el contrato las exponga): `editable`, transiciones permitidas y `can_register_payment`.

**Errores de dominio.** `OrderValidationError({campo: [mensajes]})` para errores atribuibles a un campo enviado (cantidad, descuento mayor al subtotal, monto de pago mayor al saldo, fechas, producto o cliente inexistente/inactivo, motivo vacío) y `OrderRuleViolation(code, message)` para conflictos de estado o regla no atribuibles a un campo (`invalid_transition`, `order_not_editable`, `empty_order`, `duplicate_product`, `total_below_paid`, `order_cancelled`). `OrderNotFound` para pedido o ítem inexistente. Mensajes en español.

**Casos de uso** (uno por clase, `execute`): comandos `CreateOrder`, `UpdateOrder` (datos), `AddOrderItem`, `ChangeOrderItemQuantity`, `RemoveOrderItem`, `ApplyOrderDiscount`, `StartOrderPreparation` (es la "confirmación"), `MarkOrderReady`, `DeliverOrder`, `CancelOrder`, `RegisterPayment`; consultas `GetOrder` y `ListOrders` con filtros. `ListPendingOrders`, `ListPendingDeliveries`, `ListPendingPayments`, `ListOrdersByCustomer`, `ListOrdersByDateRange` de `ddd.md:536-545` **no** son clases aparte: son combinaciones de filtros de `ListOrders`. `ConfirmOrder` y `RefundPayment` no se crean. Sin eventos de dominio (opcionales en el MVP, `ddd.md:549-566`).

## Alternativas consideradas
- **Agregar un estado CONFIRMED / DRAFT.** Modelaría "confirmar" literalmente pero contradice los 5 estados de REQ-SAL-008 y añade una transición que el negocio no pidió. Descartado por decisión del usuario.
- **`Payment` como agregado propio.** Simplifica persistencia, pero obliga a coordinar entre agregados las invariantes "pago ≤ saldo" y "total ≥ pagado" (condiciones de carrera y lógica en la aplicación). `ddd.md:331-335` ya lo ubica dentro de Order. Se mantiene dentro del agregado.
- **`PaymentStatus` como campo asignable.** Contradice REQ-SAL-012 ("derivado de los pagos"). Descartado.
- **Permitir sobrepago o cancelar un pedido entregado:** descartado por el usuario (más fácil de añadir después que de retirar).
- **Auto-ajustar el descuento al quitar ítems:** evita el error pero cambia en silencio un importe que REQ-SAL-006 exige explícito. Se rechaza y se avisa.
- **Value object `Money` con moneda:** sin REQ de multimoneda; la función compartida basta. Se reevalúa si aparece una segunda moneda.
- **Tabla de historial de transiciones (auditoría):** ningún REQ la pide; se acepta como deuda (solo `delivered_date` y `cancelled_at`).

## Estrategia de rollback / mitigación
Cambio aditivo en código: módulo nuevo sin consumidores previos. Rollback = revertir el PR; el modelo de dominio no toca datos existentes. La mitigación de errores de regla está en pruebas de dominio sin base de datos (tabla de transiciones, derivación de `payment_status`, invariantes 1-10). La parte de base de datos se trata en [ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia](ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia.md).

## Consecuencias
- Queda fácil: probar todas las reglas sin Django; la UI recibe del agregado qué acciones están permitidas sin duplicar reglas; `Reporting` podrá agrupar por `sales_channel` y `status`.
- Queda más difícil: un pago registrado por error **no se puede corregir** (sin edición ni anulación ni REFUNDED) hasta que haya un REQ de anulación/reembolso — **riesgo operativo a confirmar con el negocio**; `REFUNDED` queda como valor sin camino de uso.
- Supuestos nuevos a confirmar en el plan (decisiones mías, no del usuario): cantidades **enteras**; un producto no puede repetirse en un pedido; `delivered_date` no futura y `payment_date` no futura; el pedido cancelado conserva el `payment_status` derivado de sus pagos; el cliente solo se valida al asignarlo/cambiarlo (un pedido existente de un cliente luego desactivado sigue siendo editable).
- Deuda aceptada: `catalog` mantiene su propio validador de precio; sin bitácora de transiciones; para `Reporting`, "ventas cobradas" de pedidos cancelados con pagos queda por definir cuando exista ese módulo.
