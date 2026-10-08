# PLAN-2026-10-08-ciclo-pedido-entrega-cobro (v2)

**Task:** TASK-ciclo-pedido-entrega-cobro
**Modo:** COMPLETO
**DDRs relacionados:** [menu-y-lista-pedidos](../design/DDR-ciclo-pedido-entrega-cobro-menu-y-lista-pedidos.md), [formulario-y-detalle-pedido](../design/DDR-ciclo-pedido-entrega-cobro-formulario-y-detalle-pedido.md)
**ADRs relacionados:** [modelo-dominio](../adr/ADR-ciclo-pedido-entrega-cobro-modelo-dominio.md), [contrato-api](../adr/ADR-ciclo-pedido-entrega-cobro-contrato-api.md), [persistencia-consistencia](../adr/ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia.md), [integracion-modulos](../adr/ADR-ciclo-pedido-entrega-cobro-integracion-modulos.md), [frontend-feature](../adr/ADR-ciclo-pedido-entrega-cobro-frontend-feature.md)
**Specification readiness:** READY

> Modo COMPLETO por los tres ejes: (1) reglas de dominio nuevas (agregado con invariantes, máquina de estados, pagos, saldos y descuentos); (2) frontera cruzada (Sales consume Catalog y Customers, y alimenta el historial de Customers); (3) contrato API nuevo, migración inicial de un módulo, cinco ADR y dos DDR con impacto visual.

## Objective
Implementar el módulo Ventas (REQ-SAL-001 a 016): API REST `/api/orders/` en `backend/modules/sales` y las pantallas Angular de lista, formulario y detalle de pedido (ítems, descuento, estados de entrega, cancelación y pagos), con **estado de entrega y estado de pago independientes**; conectar el historial de compras del perfil de cliente; todo en un solo PR.

## Context
Ver `docs/tasks/TASK-ciclo-pedido-entrega-cobro.md`. Verificado hoy sobre `main` (`b43956f`): `backend/modules/` tiene `accounts`, `catalog`, `customers` y **no** `sales`; `backend/config/urls.py:6-11` monta `api/products/` y `api/customers/` y no hay ruta de pedidos; `backend/shared/` solo tiene `__init__.py`; `grep for_sale backend/` no devuelve nada; `frontend/panel_admin/src/app/features/` tiene `products/` y `customers/` (sin `index.ts`) y `src/app/shared/` no existe; `app.routes.ts:20-29` registra `catalog/products` y `customers`; `assets/data/routes.json` tiene "Dashboard", "Catálogo ▸ Producto" y "Cliente". Los hechos de la investigación siguen vigentes. Molde a seguir: `backend/modules/customers/**` (casos de uso con `execute`, `_run` en `api/views.py:22-29` de catalog, repositorio con lista perezosa) y `frontend/panel_admin/src/app/features/customers/**`.

Decisiones de negocio confirmadas por el usuario el 2026-10-08 (constan en el TASK): "confirmar" = NEW→IN_PREPARATION; editable (datos, ítems, descuento) hasta READY; transiciones lineales estrictas y cancelación desde NEW/IN_PREPARATION/READY; sin sobrepago ni pagos nuevos en cancelados; REFUNDED sin acción; un task, un PR.

# Specification

## Domain context
**Bounded Context:** Sales. **Related contexts:** Catalog (producto activo, nombre y precio para el snapshot, vía `modules.catalog.services`); Customers (cliente activo y nombre, vía `modules.customers.services`; Customers consume el contrato HTTP de pedidos, sin importar Sales); Reporting (futuro, solo lee). Referencias entre módulos solo por UUID (`ddd.md:772-779`).

## Ubiquitous language
| Term | Meaning | Source |
|---|---|---|
| Pedido (`Order`) | Agregado raíz de Sales; en la UI y en los REQ también se llama "venta" (REQ-SAL-011 "detalle de la venta") | REQ-SAL, `ddd.md:327` |
| Estado de entrega (`status`) | NEW, IN_PREPARATION, READY, DELIVERED, CANCELLED; avance logístico | REQ-SAL-008, `ddd.md:396` |
| Estado de pago (`payment_status`) | PENDING, PARTIAL, PAID, REFUNDED; **derivado** de los pagos, nunca asignado | REQ-SAL-012 |
| Confirmar | Acción NEW→IN_PREPARATION (`prepare`); no existe estado "confirmado" | TASK, decisión del usuario |
| Editable | Estado en que se pueden cambiar datos, ítems y descuento: NEW, IN_PREPARATION, READY | TASK, decisión del usuario |
| Canal de venta (`sales_channel`) | WHATSAPP, FACEBOOK, INSTAGRAM, STORE, FAIR, OTHER | REQ-SAL-007, `ddd.md:419` |
| Método de pago (`payment_method`) | CASH, QR, BANK_TRANSFER, CARD, OTHER | REQ-SAL-011, `ddd.md:432` |
| Fecha de pedido (`order_date`) | Fecha comercial del pedido | REQ-SAL-001 |
| Entrega prevista / real (`expected_delivery_date` / `delivered_date`) | Fecha planificada (opcional) y fecha en que se marcó entregado | REQ-SAL-009 |
| Subtotal / Descuento / Total | Σ subtotales de ítems / monto restado, explícito / subtotal − descuento | REQ-SAL-005/006 |
| Pagado (`paid_total`) / Saldo (`balance`) | Σ de pagos / total − pagado | REQ-SAL-013 |
| Snapshot | Nombre y precio del producto copiados al ítem al agregarlo | REQ-SAL-002 |
| Pendiente de entrega | `status ∈ {NEW, IN_PREPARATION, READY}` | DDR lista |
| Por cobrar | `balance > 0` y pedido no cancelado | DDR lista (propuesta, ver Open questions) |

Inconsistencias declaradas (no se resuelven en silencio):
- Textos de los REQ vs. códigos de `ddd.md`: "venta directa" = `STORE`, "transferencia" = `BANK_TRANSFER`; los códigos son internos y las etiquetas en español son de UI.
- REQ-SAL-001/004 hablan de "confirmar" y "pedido confirmado" pero no hay estado de ese nombre: se mapea a `prepare` (IN_PREPARATION o posterior).
- `ddd.md:380-390` lista `Payment.status`; en este alcance no existe (sin anulación ni reembolso).
- El menú dice "Pedidos" y el módulo "Sales"/"Ventas"; la ruta es `sales/orders`.
- "Conserva su historial" (REQ-SAL-010) se interpreta como no perder datos (ítems, pagos, motivo, fecha de cancelación), no como bitácora de transiciones.

## Current behavior
No existe ninguna pantalla, endpoint, modelo ni migración de pedidos o pagos: `GET /api/orders/` devolvería 404 (`backend/config/urls.py:6-11`) y el menú no tiene entrada de pedidos (`assets/data/routes.json`). Catálogo y Clientes funcionan de extremo a extremo y exponen UUID estables con filtros `active`/`search` (`backend/modules/catalog/api/views.py:40-47`). La sección de historial del perfil de cliente existe vacía y sin peticiones (`features/customers/components/customer-purchase-history/customer-purchase-history.component.html`).

## Expected behavior
Un usuario autenticado puede crear un pedido en estado NEW (cliente opcional, canal, fecha, entrega prevista opcional, notas), agregarle productos activos con snapshot de nombre y precio, cambiar cantidades, quitar ítems y aplicar un descuento, viendo siempre importes calculados por el servidor; avanzar el pedido NEW→IN_PREPARATION→READY→DELIVERED o cancelarlo con motivo; registrar pagos parciales o totales en cualquier momento mientras el pedido no esté cancelado y haya saldo; y consultar una lista filtrable y un detalle completo. El estado de entrega y el de pago evolucionan por separado: un pedido puede estar entregado con saldo pendiente o pagado y pendiente de entrega. El historial del perfil de cliente muestra sus pedidos reales.

## Domain rules / invariants
Reglas **existentes** que deben seguir siendo verdaderas: dinero en `Decimal` (`CLAUDE.md`); productos y clientes nunca se borran; un producto inactivo no entra a pedidos nuevos (`ddd.md:464`); Reporting solo lee; estados por métodos del agregado.

Reglas **nuevas** (detalle y justificación en [ADR modelo-dominio](../adr/ADR-ciclo-pedido-entrega-cobro-modelo-dominio.md)):
- INV-01: importes `Decimal` con ≤ 2 decimales, 0 ≤ importe ≤ 9 999 999 999,99; `float` y `bool` rechazados; monto de pago > 0; precio de ítem ≥ 0 (un obsequio puede costar 0, como permite Catalog).
- INV-02: `quantity` entero en 1…100 000; un `product_id` no se repite en el pedido.
- INV-03: `0 ≤ discount ≤ subtotal`; `subtotal = Σ (unit_price × quantity)`; `total = subtotal − discount`; `total` no se asigna desde fuera.
- INV-04: datos, ítems y descuento solo se modifican con `status ∈ {NEW, IN_PREPARATION, READY}`.
- INV-05: nunca `total < paid_total`.
- INV-06: el pedido puede tener 0 ítems solo en NEW; `prepare` exige ≥ 1 ítem; en IN_PREPARATION y READY no se puede quitar el último ítem.
- INV-07: transiciones únicas: NEW→IN_PREPARATION (`prepare`), IN_PREPARATION→READY (`ready`), READY→DELIVERED (`deliver`), {NEW, IN_PREPARATION, READY}→CANCELLED (`cancel`). Todo lo demás es inválido; DELIVERED y CANCELLED son terminales.
- INV-08: cancelar exige motivo (recortado, 1…500); guarda `cancellation_reason` y `cancelled_at`; ítems y pagos se conservan; el `payment_status` derivado se conserva.
- INV-09: `expected_delivery_date ≥ order_date`; `delivered_date` (defecto hoy) `≥ order_date` y `≤ hoy`; `payment_date` (defecto hoy) `≤ hoy`.
- INV-10: un pago exige `amount > 0` y `amount ≤ balance`, pedido no cancelado, método válido, `reference` ≤ 100; los pagos solo se agregan (no se editan ni se borran).
- INV-11: `payment_status` = PENDING si no hay ítems; PAID si hay ítems y `paid_total ≥ total`; PARTIAL si `0 < paid_total < total`; PENDING en otro caso. REFUNDED no se produce. No depende de `status` y viceversa.
- INV-12: `subtotal`, `total`, `paid_total`, `payment_status` e ítem `subtotal` los calcula el agregado y se persisten solo mediante `repository.save`.
- INV-13: nombre y precio del snapshot los toma el servidor del catálogo; el cliente HTTP no puede enviarlos.
- INV-14: el cliente (`customer_id`) debe existir y estar activo solo al crear el pedido o al cambiarlo; pedidos existentes de clientes luego desactivados siguen visibles y editables.

## Acceptance criteria
- **AC-01** (REQ-SAL-001, 007) `POST /api/orders/` con `sales_channel` válido crea un pedido NEW, `payment_status` PENDING, sin ítems, `total` `"0.00"`, `order_date` por defecto hoy, cliente opcional y notas opcionales; responde 201 con el recurso detalle. Canal inválido o ausente → 400 `sales_channel`.
- **AC-02** (REQ-SAL-001, 004, 008) `prepare` con 0 ítems → 409 `empty_order` y el estado no cambia; con ≥ 1 ítem → IN_PREPARATION. Quitar el único ítem en IN_PREPARATION o READY → 409 `empty_order`; en NEW queda permitido.
- **AC-03** (REQ-SAL-002) `POST …/items/` con `{product_id, quantity}` de un producto activo guarda `product_name` y `unit_price` del catálogo, calcula `subtotal = unit_price × quantity` (2 unidades de 35,00 → `"70.00"`) y recalcula `subtotal` y `total` del pedido. Producto inexistente o inactivo → 400 `product_id` sin cambios; cantidad no entera o ≤ 0 → 400 `quantity`; producto ya presente → 409 `duplicate_product`; cualquier `unit_price`/`product_name` enviado se ignora. Un producto activo con precio 0 se agrega con subtotal de ítem `"0.00"` (v2, REV-03).
- **AC-04** (REQ-SAL-003) `PATCH …/items/{item_id}/` con `{quantity}` válida actualiza el subtotal del ítem y los totales sin edición manual; cantidad ≤ 0 o no entera → 400 `quantity`.
- **AC-05** (REQ-SAL-004) `DELETE …/items/{item_id}/` quita el ítem y recalcula; responde 200 con el pedido; ítem inexistente → 404.
- **AC-06** (REQ-SAL-005) `subtotal`, `total`, `paid_total`, `balance`, `payment_status` y los estados son de solo lectura: se ignoran si llegan en `POST`/`PATCH`. Los importes son strings decimales.
- **AC-07** (REQ-SAL-006) `POST …/discount/ {discount}`: con `0 ≤ discount ≤ subtotal` fija el descuento y recalcula el total; `discount > subtotal`, negativo o no decimal → 400 `discount`; `0` lo quita; el descuento figura en el recurso. Si el nuevo total quedaría bajo lo pagado → 409 `total_below_paid`. Un cambio de cantidad o quitar un ítem que dejara `discount > subtotal` → 409 `discount_exceeds_subtotal`; que dejara `total < paid_total` → 409 `total_below_paid`; en ambos casos sin cambios.
- **AC-08** (REQ-SAL-007) Los seis canales se aceptan, se persisten en una columna indexada y se pueden filtrar con `sales_channel=`.
- **AC-09** (REQ-SAL-008, 016) Las únicas transiciones válidas son las de INV-07; cualquier otra → 409 `invalid_transition` sin cambios (p. ej. entregar un CANCELLED o un NEW, cancelar un DELIVERED, volver a NEW). `allowed_transitions` es `["prepare","cancel"]` en NEW, `["ready","cancel"]` en IN_PREPARATION, `["deliver","cancel"]` en READY y `[]` en terminales.
- **AC-10** (REQ-SAL-009) `expected_delivery_date` se puede fijar o cambiar con `PATCH` mientras el pedido sea editable (≥ `order_date`, si no → 400); `deliver` registra `delivered_date` (body opcional, defecto hoy; fuera de rango → 400 `delivered_date`); la lista filtra por rango de `expected_delivery_date` con `date_field=expected_delivery_date`, `date_from`, `date_to`.
- **AC-11** (REQ-SAL-010) `cancel` sin motivo o con motivo en blanco → 400 `reason`; con motivo válido deja CANCELLED, guarda `cancellation_reason` y `cancelled_at`, conserva ítems, pagos y `payment_status`, y el pedido queda `editable: false`, `allowed_transitions: []`, `can_register_payment: false`.
- **AC-12** (REQ-SAL-011) `POST …/payments/ {amount, payment_method, payment_date?, reference?}` con monto > 0 y ≤ saldo agrega el pago (201 con el pedido) y aumenta `paid_total`; el pago aparece en `payments`. Monto ≤ 0, no decimal o > saldo → 400 `amount`; método inválido → 400 `payment_method`; fecha futura → 400 `payment_date`; pedido cancelado → 409 `order_cancelled`. Se acepta en NEW, IN_PREPARATION, READY y DELIVERED mientras haya saldo.
- **AC-13** (REQ-SAL-012) `payment_status` sigue INV-11: sin pagos PENDING; pago acumulado menor al total PARTIAL; pago acumulado igual al total PAID; un pedido con ítems y total 0 (descuento total) es PAID; un pedido sin ítems es PENDING.
- **AC-14** (REQ-SAL-013) `balance = total − paid_total`, independiente de `status`: un DELIVERED puede tener saldo > 0 y un PAID tiene `"0.00"`.
- **AC-15** (REQ-SAL-016) Se puede llegar a "DELIVERED + PENDING/PARTIAL" (entregar sin pagar) y a "PAID + NEW/IN_PREPARATION/READY" (pagar todo antes de entregar); ninguna acción de un eje modifica el otro eje.
- **AC-16** (REQ-SAL-014, 007) `GET /api/orders/` pagina (50 por página, máx. 100) con filtros `status`, `payment_status` (listas separadas por coma), `sales_channel`, `customer_id`, `date_field`+`date_from`+`date_to` (inclusivos), `has_balance=true`, y orden `-order_date` (defecto) o `expected_delivery_date` (ascendente, sin fecha al final); valores inválidos → 400 con el parámetro. Devuelve el recurso resumen. Permite localizar pendientes de entrega, entregados, cancelados y por cobrar, y devuelve los pedidos de un cliente inactivo.
- **AC-17** (REQ-SAL-015) `GET /api/orders/{id}/` devuelve el recurso detalle completo (cliente, ítems, importes, estados, pagos, canal, fechas, notas, motivo de cancelación, `editable`, `allowed_transitions`, `can_register_payment`); id inexistente o mal formado → 404 `{detail}`; sin token → 401.
- **AC-18** (REQ-SAL-001, REQ-CUS-001 criterio 2) `customer_id` inexistente o inactivo al crear o cambiar de cliente → 400 `customer_id`; `null` permitido; el recurso incluye `customer: {id, name}` o `null`; un pedido existente de un cliente luego desactivado sigue consultable y editable.
- **AC-19** (INV-04) `PATCH` del pedido, ítems y descuento sobre DELIVERED o CANCELLED → 409 `order_not_editable`.
- **AC-20** (INV-12, ADR persistencia) Lo persistido (`subtotal`, `total`, `paid_total`, `payment_status`, subtotales de ítem) coincide con lo recalculado por el agregado; guardar nunca borra ni modifica pagos existentes; las mutaciones cargan el pedido con bloqueo de fila dentro de una transacción.
- **AC-21** (ADR integración) `modules/catalog/services.py` y `modules/customers/services.py` exponen `get_product_for_sale`, `get_customer_for_sale` y `get_customer_names` con DTO inmutables; Sales solo importa esas fachadas; Customers no importa Sales.
- **AC-22** (DDR lista, REQ menú) Entrada de menú directa "Pedidos" (`/sales/orders`, ícono `shopping-cart`) con título traducido en `en/es/de`.
- **AC-23** (REQ-SAL-014, DDR lista) La lista de pedidos muestra columnas Pedido, Cliente, Canal, Entrega prevista, Total, Saldo, Entrega (badge con `fa-truck`), Pago (badge con `fa-coins`) y "Ver"; los atajos Todos / Pendientes de entrega / Por cobrar / Entregados / Cancelados solo fijan los filtros finos (estado de entrega, estado de pago, canal, cliente, fecha de pedido o entrega prevista con desde/hasta); filtros y página viven en los query params y se conservan al volver; paginación y orden en servidor; estados vacío, carga y error.
- **AC-24** (REQ-SAL-001, 007, 009) El formulario de pedido (`/sales/orders/new`, `:id/edit`) permite elegir cliente activo (o "Sin cliente"), canal, fecha de pedido (hoy por defecto), entrega prevista opcional y notas; muestra los errores del servidor bajo cada campo; al crear navega al detalle; el enlace "Editar datos" no aparece si el pedido no es editable.
- **AC-25** (REQ-SAL-002..006, 008..013, 015, 016) El detalle (`/sales/orders/:id`) muestra paneles Entrega y Cobro separados, las alertas "Entregado con saldo pendiente", "Pagado, pendiente de entrega" y "Pedido cancelado" con motivo, datos, ítems (alta con selector de productos activos y cantidad, cantidad editable en la fila, quitar con confirmación), importes de solo lectura tal como los devuelve el servidor, pagos con formulario inline y saldo de ayuda, y una barra de acciones que muestra solo lo permitido por `allowed_transitions`/`editable`/`can_register_payment`; entregar usa diálogo con fecha real (hoy por defecto) y aviso de saldo sin bloquear; cancelar usa diálogo con motivo obligatorio y aviso de que los pagos se conservan; cada mutación refresca el pedido con la respuesta del servidor y deshabilita su botón mientras se envía.
- **AC-26** (REQ-CUS-004) El historial de compras del perfil de cliente consulta `GET /api/orders/?customer_id=` y muestra fecha, total, estado de entrega y de pago, con enlace al detalle del pedido, del más reciente al más antiguo; vacío "Este cliente aún no tiene pedidos."; un error al cargarlo no impide ver los datos del cliente; funciona para clientes inactivos.
- **AC-27** (REQ-CUS-001 criterio 2) El selector de cliente del formulario permite crear un cliente en un modal (nombre y teléfono), reutilizando el diálogo de duplicado de Clientes, y lo deja seleccionado. *Fase final, separable.*
- **AC-28** (ADR frontend) `Page<T>` y los estilos de acciones de tabla (`btn-tbl-*`) viven en `shared/`; `products` y `customers` los usan y sus specs existentes siguen pasando sin cambios de comportamiento.

## Edge cases
- EDGE-01: dos pagos simultáneos que juntos exceden el saldo: el segundo se rechaza con 400 `amount` (bloqueo de fila).
- EDGE-02: precio del producto cambia después de agregarlo: el ítem conserva el snapshot.
- EDGE-03: producto desactivado después de agregarlo: el ítem se conserva y sigue editable en cantidad; solo se rechaza agregarlo de nuevo.
- EDGE-04: descuento = subtotal (total 0, con ítems): `payment_status` PAID, saldo 0, no se aceptan pagos (`amount > balance`).
- EDGE-05: pedido NEW con pagos y luego se intenta quitar un ítem que baja el total bajo lo pagado → 409 `total_below_paid`.
- EDGE-06: cambiar `order_date` a una fecha posterior a la entrega prevista → 400 `expected_delivery_date`.
- EDGE-07: `deliver` con `delivered_date` anterior a `order_date` o futura → 400.
- EDGE-08: cliente desactivado después de crear el pedido: el pedido sigue listándose y filtrándose por `customer_id`; `customer.name` sigue resolviéndose.
- EDGE-09: `customer_id` con UUID bien formado pero inexistente en el filtro de la lista → lista vacía (no 400).
- EDGE-10: `status=NEW,FOO` → 400 `status`; `date_from > date_to` → 400 `date_to`; `has_balance=maybe` → 400 `has_balance`.
- EDGE-11: un pedido cancelado con pagos conserva `payment_status` PAID/PARTIAL y su saldo calculado; no se pueden registrar más pagos.
- EDGE-12 (UI): pedido inexistente en el detalle o la edición → aviso y retorno a la lista; error de red → `toastr`.
- EDGE-13 (v2, REV-03): un pedido con solo obsequios (precio 0) tiene total `"0.00"`, saldo `"0.00"`, `payment_status` PAID y `can_register_payment: false`; sigue el flujo de estados normal.
- EDGE-14 (v2, REV-02): los selectores de cliente (formulario y lista) y de producto (detalle) siguen buscando después de seleccionar o limpiar una opción: `ng-select` emite `null` por el `typeahead` y no debe romper el flujo ni dejar el spinner fijo.
- EDGE-15 (v2, REV-01): un nombre de producto o de cliente con HTML se muestra como texto en los diálogos de confirmación; nunca se interpreta como HTML.

## Error cases
Forma/tipos del serializer y reglas atribuibles a un campo → 400 `{campo: [mensajes en español]}` (con todos los errores de campo juntos cuando sea posible); conflictos de estado o regla no atribuibles a un campo → 409 `{code, detail}`; pedido o ítem inexistente / id mal formado → 404 `{detail}` ("Pedido no encontrado." / "Ítem no encontrado."); sin token → 401; método no permitido (`DELETE`/`PUT` del pedido, edición de pagos) → 405. Códigos 409 vigentes: `invalid_transition`, `order_not_editable`, `empty_order`, `duplicate_product`, `total_below_paid`, `discount_exceeds_subtotal`, `order_cancelled`. (`discount_exceeds_subtotal` en 409 es un refinamiento de este plan para el caso inducido por un cambio de ítems; el caso del comando de descuento es 400 `discount`.)

## Authorization / permissions
Sin roles en el sistema: cualquier usuario autenticado (token DRF) puede ejecutar todas las acciones (`IsAuthenticated` por defecto, `backend/config/settings/base.py:75-77`). El frontend no es la barrera: oculta acciones según el servidor, y el backend aplica las reglas. No se introducen permisos nuevos.

## API contract
- API-01: contrato completo en [ADR contrato-api](../adr/ADR-ciclo-pedido-entrega-cobro-contrato-api.md): rutas `GET/POST /api/orders/`, `GET/PATCH /api/orders/{id}/`, `POST /items/`, `PATCH/DELETE /items/{item_id}/`, `POST /discount/`, `/prepare/`, `/ready/`, `/deliver/`, `/cancel/`, `/payments/`; recursos detalle y resumen; filtros y orden; errores. Es una API nueva (sin compatibilidad hacia atrás que preservar) que cumple el contrato exigido por [ADR clientes historial-compras](../adr/ADR-clientes-mvp-historial-compras.md).
- Cuerpo de entrada: `POST /api/orders/` y `PATCH`: `customer_id`, `sales_channel`, `order_date`, `expected_delivery_date`, `notes`; ítems: `product_id`, `quantity`; descuento: `discount`; entregar: `delivered_date`; cancelar: `reason`; pago: `amount`, `payment_method`, `payment_date`, `reference`. `PATCH` es parcial; `customer_id` y `expected_delivery_date` aceptan `null`.
- Límites de longitud (supuesto del plan, mismo criterio que Customers): `notes` ≤ 2000, `reason` ≤ 500, `reference` ≤ 100.

## UI behavior
Derivado de los DDR (no se rediseña):
- UI-01: lista con atajos, filtros, tabla, dos badges por fila, estados de carga/vacío/error y filtros en la URL (AC-23).
- UI-02: formulario de pedido solo con datos; selector de cliente con búsqueda remota sobre clientes activos y "Sin cliente"; selector de producto con búsqueda remota sobre productos activos (AC-24, AC-25).
- UI-03: detalle con ejes Entrega/Cobro, alertas, ítems, importes, pagos inline, acciones por estado y diálogos `Swal` de entrega y cancelación (AC-25).
- UI-04: colores de badges según DDR (Entrega: NEW azul, IN_PREPARATION naranja, READY índigo, DELIVERED verde, CANCELLED rojo; Pago: PENDING naranja, PARTIAL cian, PAID verde, REFUNDED morado), siempre con texto e icono.
- UI-05: importes mostrados como `Bs 0.00` a partir del string del servidor; el navegador no suma, multiplica ni redondea.
- UI-06: textos de pantallas en español; solo el menú usa `translate`.

## Non-functional requirements
- Precisión: `Decimal` extremo a extremo (dominio, `DecimalField(12,2)`, JSON como string); sin `float`.
- Concurrencia: bloqueo de fila (`select_for_update`) dentro de `transaction.atomic()` en cada mutación.
- Rendimiento: lista sin N+1 (resumen sin ítems/pagos; nombres de cliente por una consulta por página); detalle con `prefetch_related`.
- Seguridad: sin datos sensibles nuevos; sin SQL concatenado; `reason`/`notes` se escapan en la UI (no `innerHTML`/`Swal html` sin escapar).
- Mantenibilidad: dominio sin imports de Django; módulos solo se comunican por `services.py`.

## Out of scope
Anulación o edición de pagos, reembolsos (REFUNDED sin acción), cancelación de pedidos entregados, bitácora de transiciones, número secuencial de pedido, búsqueda de texto en la lista, orden por columnas, acciones rápidas en filas, impresión/PDF, inventario, reportes (Reporting), roles y permisos, refactor de `catalog` para usar `shared/domain/money.py`, fusión o anonimización de clientes, dashboard.

## Open questions
No bloquean la implementación; son decisiones por defecto que el usuario puede vetar al revisar el PR (un cambio posterior es barato salvo donde se indica):
1. Cantidades **enteras** (sin kg/fracciones) y un producto **no repetible** en un pedido (ADR modelo-dominio).
2. `delivered_date` y `payment_date` **no futuras**.
3. "Por cobrar" = `has_balance=true` sin cancelados; un cancelado con saldo no aparece en ese atajo.
4. Los pagos **no se pueden corregir ni anular** en este alcance: un pago registrado por error requeriría un REQ nuevo (anulación/reembolso) — riesgo operativo.
5. Límites de longitud de `notes` (2000), `reason` (500) y `reference` (100).
6. Código visible del pedido `P-XXXXXXXX` derivado del UUID, sin número secuencial.

# Test Specification

## Unit tests
Backend (sin base de datos, `SimpleTestCase`):
- `backend/shared/tests/test_money.py`: `parse_money` (válidos, `float`/`bool`, >2 decimales, negativos, máximo).
- `backend/modules/sales/tests/test_domain.py`: INV-01…INV-11 sobre `Order` (v2: un ítem de precio 0 se acepta y el pedido solo de obsequios queda PAID con total 0, EDGE-13): tabla de transiciones válidas e inválidas (AC-09), derivación de `payment_status` (AC-13, EDGE-04), subtotales/total/descuento (AC-03, AC-07), `total ≥ paid_total` (EDGE-05), vacío solo en NEW (AC-02), cancelación (AC-11), fechas (AC-10, EDGE-06, EDGE-07), pago y saldo (AC-12, AC-14, AC-15), acciones disponibles.
- `backend/modules/sales/tests/test_application.py`: casos de uso con repositorio en memoria y puertos falsos: producto/cliente inactivos o inexistentes (AC-03, AC-18), snapshot (EDGE-02), `UpdateOrder` solo valida cliente si cambió (INV-14), orquestación de cada comando.
Frontend (Karma, `TestBed`): modelos/mapeo del servicio; componentes de badges. v2: `CustomerOptionsService.search` y las búsquedas de producto toleran `null`/`undefined` (EDGE-14); un test por cada `Swal.fire` con datos de usuario comprueba que un nombre con HTML llega como texto (`titleText`/`text`) y no como `title`/`html` sin escapar (EDGE-15).

## Integration tests
- `test_repository.py` (PostgreSQL real): `save`/`get` ida y vuelta del agregado, sincronización de ítems, pagos solo agregados, coherencia de derivados (AC-20), `get_for_update` requiere transacción, filtros y orden de `list` (AC-16), restricciones `CheckConstraint`/`UniqueConstraint`.
- `test_api.py` (`APITestCase` con token, PostgreSQL): AC-01…AC-19 y EDGE-01…EDGE-11 (EDGE-01 de forma secuencial más una comprobación de que la mutación usa bloqueo).
- `modules/catalog/tests/test_services.py` y `modules/customers/tests/test_services.py`: AC-21 (DTO, inactivos, lote de nombres). Una prueba de límites DDD (grep/AST) asegura que Sales no importa módulos ajenos fuera de `services.py` y que Customers no importa Sales.
- Frontend: `orders-api.service.spec.ts` con `HttpTestingController` (DTO↔modelo, 400/404/409, parámetros de lista); specs de páginas y componentes (AC-22…AC-28).

## E2E
**¿Corresponde E2E?** NO. Playwright no está en `frontend/panel_admin/package.json` y no se instala; el flujo de varias pantallas queda cubierto por specs de componentes con `HttpTestingController` y por pruebas de API sobre PostgreSQL real, igual que en catálogo y clientes. Se exige un **humo manual** antes de fusionar (backend + `npm start`): crear pedido → agregar ítems → descuento → preparar → listo → pago parcial → entregar (con saldo) → pago final; crear otro y cancelarlo con motivo; revisar lista, filtros, atajos e historial del cliente.

## Regression tests
- Specs existentes de `features/products` y `features/customers` (90 en la última revisión) deben seguir pasando tras la extracción a `shared/` (AC-28); `sidebar-menu.spec.ts` se actualiza para 4 entradas.
- Suite completa del backend (130 tests en la última revisión) en PostgreSQL; `makemigrations --check`.
- La suite completa de Angular tiene fallas preexistentes de la plantilla y `app.component.spec.ts` no compila en `main`: la verificación se acota a los specs de `features/sales`, `features/customers`, `features/products` y sidebar (con `tsconfig` temporal si hace falta).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Backend API test; dominio (creación) |
| AC-02 | Dominio unit + API test |
| AC-03 | Dominio unit + aplicación (fakes) + API test |
| AC-04, AC-05 | Dominio unit + API test |
| EDGE-13 | Dominio unit + API test (v2, REV-03) |
| EDGE-14 | Angular specs de `order-form`, `order-list`, `order-items` y `customer-options.service` emitiendo `null` por el typeahead (v2, REV-02) |
| EDGE-15 | Angular specs de `order-detail`, `customer-list` y `customer-detail` espiando `Swal.fire` sin sustituir el método de confirmación (v2, REV-01) |
| AC-06 | API test (campos ignorados, strings decimales) |
| AC-07 | Dominio unit + API test |
| AC-08 | API test + repository test |
| AC-09 | Dominio unit (tabla completa) + API test |
| AC-10 | Dominio unit + API test (filtros de fecha) |
| AC-11 | Dominio unit + API test |
| AC-12 | Dominio unit + API test |
| AC-13, AC-14, AC-15 | Dominio unit + API test |
| AC-16 | Repository test + API test |
| AC-17 | API test |
| AC-18 | Aplicación (fakes) + API test (con Customers real) |
| AC-19 | Dominio unit + API test |
| AC-20 | Repository test (PostgreSQL) |
| AC-21 | Tests de fachadas + prueba de límites de import |
| AC-22 | `sidebar-menu.spec.ts` + verificación de `routes.json` e i18n |
| AC-23 | Angular spec de `order-list` + humo manual |
| AC-24 | Angular spec de `order-form` |
| AC-25 | Angular specs de `order-detail` y componentes (`order-items`, `order-payments`, `order-summary`, badges) + humo manual |
| AC-26 | Angular specs de `customer-purchase-history`, `customer-orders-api.service` y `customer-detail` |
| AC-27 | Angular spec de `customer-quick-create` y de `order-form` (selector) |
| AC-28 | Specs existentes de products/customers + build + lint |

# Implementation Plan

## Architecture considerations
Se respetan los cinco ADR: módulo `sales` con capas `domain/application/infrastructure/api`; agregado `Order` con `OrderItem`/`Payment` internos; derivados persistidos y escritos solo por el agregado; `select_for_update` en `transaction.atomic()` abierta por la capa API (`_run`), la capa `application` no importa Django; fachadas `services.py` entre módulos con DTO inmutables y puertos en Sales; Customers no importa Sales; frontend con `features/sales`, API pública por feature (`index.ts`) y extracción a `shared/` en commit aparte. `docs/architecture/ddd.md`: dominio sin Django, Reporting solo lee, estados por métodos del agregado, sin abstracciones sin necesidad (los puertos y `shared/domain/money.py` están justificados en los ADR). Sin cambios de autenticación, infraestructura ni variables de entorno.

## Proposed solution
Reproducir el molde de `customers` para Sales: `domain/order.py` (dataclasses `Order`, `OrderItem`, `Payment`; enums; excepciones `OrderValidationError`, `OrderRuleViolation`, `OrderNotFound`) → `application/commands.py` y `queries.py` con puertos (`ProductCatalog`, `CustomerDirectory`) → `infrastructure/django` (modelos, mapper, repositorio con lista perezosa) y `infrastructure/adapters.py` → `api` (serializers de entrada y salida, vistas `APIView` delgadas con `_run` que abre `transaction.atomic()` en mutaciones y traduce errores a 400/409/404, paginación). El frontend replica el molde de `features/customers` con un servicio tipado, páginas de lista/formulario/detalle y componentes pequeños; las acciones visibles salen del servidor.

## Files/components affected
- **Backend (nuevos):** `backend/shared/domain/{__init__,money}.py`; `backend/modules/catalog/services.py`; `backend/modules/customers/services.py`; `backend/modules/sales/{__init__,apps,models}.py`, `domain/{__init__,enums,exceptions,order,repositories}.py`, `application/{__init__,ports,commands,queries}.py`, `infrastructure/{__init__,adapters}.py`, `infrastructure/django/{__init__,models,mappers,repositories}.py`, `api/{__init__,serializers,views,urls,pagination}.py`, `migrations/{__init__,0001_initial}.py`.
- **Backend (modificados):** `backend/config/settings/base.py` (`modules.sales` en `INSTALLED_APPS`), `backend/config/urls.py` (`api/orders/`).
- **Frontend (nuevos):** `src/app/shared/models/page.ts`, `src/app/shared/styles/_table-actions.scss`; `src/app/features/sales/**` (models, services, pages `order-list|order-form|order-detail`, components `order-status-badge|payment-status-badge|order-items|order-payments|order-summary`, `testing/order-fixtures.ts`, `sales.routes.ts`, `index.ts`); `features/customers/services/customer-orders-api.service.ts`, `features/customers/components/customer-quick-create/**`, `features/customers/index.ts`; `features/products/index.ts`.
- **Frontend (modificados):** `app.routes.ts` (ruta `sales/orders`); `assets/data/routes.json` y `assets/i18n/{en,es,de}.json` (menú); `features/products` y `features/customers` (usar `shared/Page<T>` y estilos compartidos); `customer-purchase-history` y `customer-detail` (historial real); `layout/sidebar/sidebar-menu.spec.ts`.
- **Tests:** ver Test Specification.
- **Documentación:** `docs/architecture/ddd.md` (rutas reales de Sales en la sección 14 y la convención `services.py` en la sección 10); se actualizan TASK y PR.

## Implementation steps
Un solo PR, por fases con commits separados; cada fase deja los tests de su capa en verde.

**Fase 0 — Extracción a `shared/` (commit aparte, AC-28)**
1. Crear `shared/models/page.ts` (`Page<T>`) y `shared/styles/_table-actions.scss` con los estilos `btn-tbl-*`.
2. Migrar `products` y `customers` (modelos, servicios, specs y SCSS de lista) a usarlos sin cambiar comportamiento; correr sus specs, lint y build.

**Fase 1 — Backend base e integración (AC-21)**
3. `shared/domain/money.py`: `parse_money` e `InvalidMoney`; tests (INV-01).
4. `catalog/services.py` y `customers/services.py` con DTO congelados (`ProductForSale`, `CustomerForSale`) y `get_customer_names`; tests con PostgreSQL.

**Fase 2 — Dominio de Sales (INV-01…INV-14, AC-02…AC-15 a nivel de dominio)**
5. Enums, excepciones y `Order`/`OrderItem`/`Payment` con métodos: `create`, `update_details`, `add_item`, `change_item_quantity`, `remove_item`, `apply_discount`, `start_preparation`, `mark_ready`, `deliver`, `cancel`, `register_payment`, recálculo de derivados y consultas `editable`/`allowed_transitions`/`can_register_payment`; la fecha "hoy" se inyecta. Escribir `test_domain.py` primero para cada invariante.
6. `repositories.py` (Protocol: `get`, `get_for_update`, `save`, `list`).

**Fase 3 — Aplicación (AC-03, AC-18, INV-13, INV-14)**
7. `ports.py`, `commands.py` (un caso de uso por clase, según ADR), `queries.py` (`GetOrder`, `ListOrders` con filtros tipados); `test_application.py` con repositorio en memoria y puertos falsos.

**Fase 4 — Infraestructura y migración (AC-08, AC-16, AC-20)**
8. Modelos Django (`sales_order`, `sales_order_item`, `sales_payment`), restricciones, índices; `models.py` raíz; `apps.py`; registrar `modules.sales` en `INSTALLED_APPS`; generar `0001_initial` con `makemigrations`.
9. Mapper y `DjangoOrderRepository` (upsert + sincronización de ítems, solo agregar pagos, `select_for_update`, lista perezosa con filtros/orden con `nulls_last`); `adapters.py`; `test_repository.py`.

**Fase 5 — API (AC-01…AC-20)**
10. Serializers de entrada (forma/tipos) y de salida (detalle y resumen, `code`, `customer` por lote); paginación; vistas con `_run` (transacción en mutaciones; `OrderValidationError`→400, `OrderRuleViolation`→409, `OrderNotFound`→404); `urls.py`; montar `api/orders/` en `config/urls.py`.
11. `test_api.py` completo (AC-01…AC-19, EDGE-01…EDGE-11), incluidos 401, 404 y 405.
12. Actualizar `ddd.md` (secciones 10 y 14). Verificar suite completa, `makemigrations --check` y límites DDD.

**Fase 6 — Frontend base, menú y lista (AC-22, AC-23)**
13. Modelos (`order.ts`, `payment.ts`), `OrdersApiService` (DTO↔modelo, errores 400/404/409 tipados, parámetros de lista), `order-fixtures.ts`, specs del servicio.
14. `sales.routes.ts`, ruta en `app.routes.ts`, `index.ts`; entrada de menú, i18n `en/es/de` y `sidebar-menu.spec.ts`.
15. Componentes de badges y página `order-list` (atajos → filtros finos → query params, `ngx-datatable` con paginación externa, columnas del DDR) con specs.

**Fase 7 — Formulario y detalle (AC-24, AC-25)**
16. `order-form` (cliente y canal, fechas, notas; navegación al detalle; errores por campo) con spec.
17. `order-detail` con `order-summary`, `order-items` (selector de producto, cantidad en fila, quitar con `Swal`), `order-payments` (formulario inline), alertas, barra de acciones y diálogos de entrega y cancelación; specs de cada componente y de la página (acciones según `allowed_transitions`, alertas por estado).

**Fase 8 — Historial del cliente y creación rápida (AC-26, AC-27)**
18. `customer-orders-api.service.ts`, conectar `customer-detail` y `customer-purchase-history` (filas con enlace, columna Pago, error aislado); `features/customers/index.ts` y `features/products/index.ts`.
19. `customer-quick-create` (modal, reutiliza el diálogo de duplicado) y su integración en el selector de `order-form`. *Separable: si se corta el alcance, esta fase puede quedar para un task posterior sin afectar lo demás.*

**Fase 9 — Verificación**
20. Backend: suite completa en PostgreSQL, `makemigrations --check`. Frontend: `ng lint`, `ng build` y specs de las features tocadas. Humo manual descrito en E2E. Documentar resultados en el TASK.

**Fase 10 — Correcciones del review (v2; REV-01, REV-02, REV-03)**
21. REV-01 (EDGE-15, NFR Seguridad): en `order-detail.component.ts`, `confirmRemove` muestra el nombre del producto como texto plano (`titleText`, no `title`). Auditar todos los `Swal.fire` de `features/sales` y `features/customers`: donde entre un dato de usuario, usar `titleText`/`text` o `escapeHtml`. Incluye el mismo patrón ya existente en `confirmToggle` de `customer-list` y `customer-detail` (nombre del cliente en `title`). Specs que llamen al método real con `Swal.fire` espiado y nombres con HTML (`<img src=x onerror=...>`).
22. REV-02 (EDGE-14, AC-23, AC-24, AC-25): `CustomerOptionsService.search` y la búsqueda de productos de `order-items` aceptan `null`/`undefined` (`(term ?? '').trim()`); proteger los `switchMap` de `customers$` y `products$` de modo que un valor inesperado no termine el stream ni deje `loading` fijo. Specs que emiten `null` por `customerInput$` y `productInput$` y comprueban que la siguiente búsqueda sí se hace y el spinner se apaga (formulario, lista, ítems y servicio).
23. REV-03 (INV-01, AC-03, EDGE-13; cambio de Specification aprobado): quitar de `Order.add_item` la comprobación de precio > 0; mantener el resto. Actualizar `test_domain.py` (el producto de precio 0 ahora se agrega; pedido solo de obsequios: total 0, PAID, sin saldo), `test_application.py` y `test_api.py`. Enmendar el ADR `modelo-dominio` (precio de ítem ≥ 0). Sin cambios de migración (la columna `unit_price` no tiene restricción de positividad) ni de frontend (el selector ya ofrece esos productos).
24. Repetir la Fase 9: backend completo, `makemigrations --check`, `ng lint`, `ng build`, specs de las features tocadas y el humo manual de UI, incluida la cancelación y la creación rápida de cliente que el review no ejercitó.

## Database / migrations
`modules/sales/migrations/0001_initial.py` generada por `makemigrations`; solo crea `sales_order`, `sales_order_item`, `sales_payment` con sus índices y restricciones; no toca tablas existentes ni requiere backfill. Reversible con `python manage.py migrate sales zero`. Nunca se edita una vez aplicada (cambios futuros en migraciones nuevas). Tras el merge: `python manage.py migrate` en cada entorno; este worktree no tiene `backend/.env`, así que las pruebas con PostgreSQL requieren `DATABASE_URL` exportada sin leer `.env`.

## Risks
- **Tamaño del PR:** el alcance es el mayor del proyecto. Mitigación: fases con commits separados, cada una verde; la Fase 8 (creación rápida) es separable; el humo manual cubre el flujo completo.
- **Divergencia de columnas derivadas:** mitigación en el diseño (solo `save` del agregado escribe), `CheckConstraint` y prueba de coherencia (AC-20).
- **Concurrencia:** el bloqueo de fila solo protege si la mutación corre en transacción; `get_for_update` falla fuera de una (prueba incluida). No hay prueba multihilo; queda como riesgo residual bajo (pocos usuarios).
- **Extracción a `shared/` toca `products` y `customers`:** mitigación con commit aparte y specs existentes como red; si falla, se revierte ese commit sin perder Sales.
- **Selectores remotos (`ng-select`) y fechas nativas:** difíciles de probar en Karma; se prueban con valores controlados y el humo manual.
- **Suite de Angular con fallas preexistentes:** verificación acotada a las features tocadas.
- **Pagos no corregibles:** riesgo operativo declarado en Open questions (4).
- **Zona horaria:** "hoy" se calcula con `timezone.localdate()` según `TIME_ZONE`; cerca de medianoche el servidor y el navegador podrían discrepar; el frontend usa la fecha local solo como valor inicial editable.

## New dependencies
Ninguna (`pip`/`npm`): se usan Django/DRF existentes, `@ng-select/ng-select`, `@ng-bootstrap/ng-bootstrap`, `@swimlane/ngx-datatable`, `sweetalert2` y `ngx-toastr`, ya instalados.

## Changelog
- **v2** (2026-10-08): [Specification] INV-01 y AC-03 cambiados tras aprobación explícita del usuario (REV-03, decisión "permitir precio 0 en ítems"): el precio de un ítem puede ser 0 (los pagos siguen siendo > 0); nuevo EDGE-13 (pedido solo de obsequios: total 0, PAID). Solicitado por delivery-review (REV-2026-10-08-ciclo-pedido-entrega-cobro-03).
- **v2** (2026-10-08): [Implementation Plan] Nuevos EDGE-14 y EDGE-15 y Fase 10 con las correcciones de REV-01 (XSS por nombre de producto en `Swal`, incluido el mismo patrón preexistente en `customer-list`/`customer-detail`) y REV-02 (`null.trim()` en las búsquedas remotas, también en `order-items`, que el review no ejercitó). Solicitado por delivery-review (REV-2026-10-08-ciclo-pedido-entrega-cobro-01 y -02). Los dos hallazgos son de implementación: la Specification ya los cubría (NFR Seguridad, AC-24).
