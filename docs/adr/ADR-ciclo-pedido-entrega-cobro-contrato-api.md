# ADR-ciclo-pedido-entrega-cobro-contrato-api: Contrato REST de `/api/orders/`

**Estado:** Propuesto
**Task relacionado:** TASK-ciclo-pedido-entrega-cobro
**Fecha:** 2026-10-08

## Contexto
Los DDR [menú y lista](../design/DDR-ciclo-pedido-entrega-cobro-menu-y-lista-pedidos.md) y [formulario y detalle](../design/DDR-ciclo-pedido-entrega-cobro-formulario-y-detalle-pedido.md) piden: lista con atajos y filtros (entrega, pago, canal, cliente, fecha de pedido o de entrega prevista, saldo), orden por vista, detalle completo con ítems, importes y pagos que se refresca con la respuesta de cada mutación, y una UI que **solo muestra las acciones que el servidor declare disponibles**. `ddd.md:944-958` sugiere endpoints de pedidos (sin cambio de cantidad, descuento, edición de datos ni `ready`). [ADR-clientes-mvp-historial-compras](ADR-clientes-mvp-historial-compras.md) fija el contrato que Sales debe cumplir: `GET /api/orders/?customer_id=<uuid>` con paginación estándar, orden por fecha descendente y, por pedido, `id`, fecha, total (string decimal) y estado, válido también para clientes inactivos. Patrones previos: vistas `APIView` delgadas, `_run` que traduce errores de dominio, errores 400 por campo, 409 con `code` (`ADR-clientes-mvp-contrato-api`), sin `django-filter`. El modelo de reglas está en [ADR-ciclo-pedido-entrega-cobro-modelo-dominio](ADR-ciclo-pedido-entrega-cobro-modelo-dominio.md).

## Decisión

**Rutas** (montadas como `api/orders/` → `modules.sales.api.urls`; requieren token; sin permisos por rol porque no existen — la autorización sigue siendo `IsAuthenticated`, y el frontend no es la barrera):

| Método y ruta | Efecto | Respuesta |
|---|---|---|
| `GET /api/orders/` | lista paginada con filtros | 200 `{count, next, previous, results[]}` (resumen) |
| `POST /api/orders/` | crea en NEW, sin ítems | 201 pedido |
| `GET /api/orders/{id}/` | detalle | 200 pedido |
| `PATCH /api/orders/{id}/` | edita `customer_id`, `sales_channel`, `order_date`, `expected_delivery_date`, `notes` | 200 pedido |
| `POST /api/orders/{id}/items/` | agrega `{product_id, quantity}` | 201 pedido |
| `PATCH /api/orders/{id}/items/{item_id}/` | cambia `{quantity}` | 200 pedido |
| `DELETE /api/orders/{id}/items/{item_id}/` | quita el ítem | 200 pedido (no 204, para refrescar importes) |
| `POST /api/orders/{id}/discount/` | fija `{discount}` (0 lo quita) | 200 pedido |
| `POST /api/orders/{id}/prepare/` | NEW → IN_PREPARATION | 200 pedido |
| `POST /api/orders/{id}/ready/` | IN_PREPARATION → READY | 200 pedido |
| `POST /api/orders/{id}/deliver/` | READY → DELIVERED; body opcional `{delivered_date}` (defecto hoy) | 200 pedido |
| `POST /api/orders/{id}/cancel/` | `{reason}` obligatorio | 200 pedido |
| `POST /api/orders/{id}/payments/` | `{amount, payment_method, payment_date?, reference?}` (fecha por defecto hoy) | 201 pedido |

No hay `DELETE` ni `PUT` del pedido (405) ni edición/anulación de pagos. Los campos de estado, importes derivados y fechas de entrega real **no** se aceptan en `POST`/`PATCH` del pedido (solo cambian por las acciones). Todas las mutaciones devuelven el **pedido completo**, así la UI refresca ejes, importes y acciones con una sola respuesta.

**Recurso detalle:** `id`, `code` (solo para mostrar: `"P-"` + primeros 8 caracteres hexadecimales del id en mayúsculas; no se persiste ni es identificador), `customer` (`{id, name}` o `null`), `sales_channel`, `order_date`, `expected_delivery_date`, `delivered_date`, `notes`, `status`, `payment_status`, `items[]` (`id, product_id, product_name, unit_price, quantity, subtotal`), `subtotal`, `discount`, `total`, `paid_total`, `balance`, `payments[]` (`id, amount, payment_method, payment_date, reference, created_at`), `cancellation_reason`, `cancelled_at`, **`editable`**, **`allowed_transitions`** (subconjunto de `["prepare","ready","deliver","cancel"]`), **`can_register_payment`**, `created_at`, `updated_at`. Los importes viajan como **strings decimales** (comportamiento por defecto de DRF `DecimalField`, sin `float`); fechas en ISO `YYYY-MM-DD`.

**Recurso de lista (resumen):** `id`, `code`, `customer`, `sales_channel`, `order_date`, `expected_delivery_date`, `status`, `payment_status`, `total`, `paid_total`, `balance`. Cubre el contrato del historial del cliente (`id`, `order_date`, `total`, `status`, y además `payment_status`).

**Filtros de la lista** (query params; implementados en `ListOrders`, sin `django-filter`; valor inválido → 400 `{param: [mensaje]}`):
- `status` y `payment_status`: uno o varios códigos separados por coma (p. ej. `status=NEW,IN_PREPARATION,READY` = "pendientes de entrega").
- `sales_channel`, `customer_id` (UUID; sin validar contra Customers, funciona para clientes inactivos).
- `date_field` = `order_date` (defecto) | `expected_delivery_date`, con `date_from` y `date_to` (inclusivos).
- `has_balance=true` → `total > paid_total` ("por cobrar"; el frontend añade `status` sin CANCELLED según la Specification).
- `ordering` = `-order_date` (defecto; desempate `-created_at`, `id`) | `expected_delivery_date` (ascendente, **sin fecha al final**). Sin otros campos de orden.
- `page`, `page_size` (máx. 100) con `OrderPagination` propia, igual que catálogo y clientes.

**Errores:** forma/tipos (serializer) → 400 `{campo: [mensajes]}`; reglas atribuibles a un campo enviado (cantidad, descuento mayor al subtotal, monto de pago mayor al saldo, fechas, `product_id`/`customer_id` inexistente o inactivo, motivo vacío) → 400 con ese campo; conflictos de estado o regla no atribuibles a un campo (`invalid_transition`, `order_not_editable`, `empty_order`, `duplicate_product`, `total_below_paid`, `order_cancelled`) → **409** `{"code": "...", "detail": "mensaje en español"}`; pedido o ítem inexistente (o id mal formado) → 404 `{detail}`; sin token → 401. `_run` en la capa API traduce `OrderValidationError`→400, `OrderRuleViolation`→409, `OrderNotFound`→404.

**Transaccionalidad:** cada mutación se ejecuta dentro de `transaction.atomic()` en la capa API (ver [ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia](ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia.md)).

**Nombre del cliente:** `customer.name` se resuelve al serializar mediante la fachada de Customers (ver [ADR-ciclo-pedido-entrega-cobro-integracion-modulos](ADR-ciclo-pedido-entrega-cobro-integracion-modulos.md)), en una sola consulta por página.

**Documentación:** al implementar se actualiza `ddd.md:944-958` (rutas reales) y la sección 10 (fachadas).

## Alternativas consideradas
- **`ModelViewSet`/router, `django-filter`, `PATCH {status}`:** descartados por las mismas razones que en catálogo y clientes (estados por métodos del agregado; filtros manuales explícitos).
- **Un único `PATCH` para datos y descuento:** menos rutas, pero mezcla campos editables con reglas distintas (descuento depende del subtotal) y oculta `ApplyOrderDiscount`. Ruta propia `discount/`.
- **204 en `DELETE` de ítem:** la UI tendría que volver a pedir el pedido; se devuelve el pedido completo.
- **Que el frontend derive las acciones del `status`:** duplica la tabla de transiciones y se desincroniza si cambia la regla. El servidor expone `editable`, `allowed_transitions`, `can_register_payment`.
- **Estado como filtro de un solo valor:** obligaría a varias llamadas para "pendientes de entrega". Lista separada por comas.
- **Código secuencial legible (`PED-0001`):** requiere secuencia de BD y concurrencia de asignación; `code` derivado del UUID basta como etiqueta. Una columna secuencial es migración aditiva posterior.
- **Endpoint `GET /api/customers/{id}/orders/` en Customers:** invertiría la dependencia (ADR de historial). Descartado; se usa `?customer_id=`.

## Estrategia de rollback / mitigación
Aditivo: rutas nuevas sin consumidores previos; el único consumidor futuro es el frontend nuevo. Rollback = revertir el PR (quitar el `include` en `config/urls.py`). No cambia autenticación ni autorización; sin feature flag. Si se cambia el contrato de la lista después de que Customers lo consuma, se enmienda también el ADR del historial.

## Consecuencias
- Queda fácil: un solo recurso consistente para todas las mutaciones; el frontend no replica reglas; el historial del cliente y la lista operativa usan el mismo endpoint.
- Queda más difícil: respuestas de detalle más pesadas (ítems y pagos en cada mutación); cualquier acción nueva debe actualizar `allowed_transitions`/`editable`.
- Deuda aceptada: sin búsqueda de texto en la lista (no pedida), sin orden por otros campos, sin código secuencial, sin `DELETE`/anulación de pagos.
