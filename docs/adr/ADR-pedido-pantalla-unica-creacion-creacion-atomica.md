# ADR-pedido-pantalla-unica-creacion-creacion-atomica: Creación atómica del pedido en preparación, con almacén

**Estado:** Propuesto
**Task relacionado:** TASK-pedido-pantalla-unica-creacion
**Fecha:** 2026-11-23

## Contexto
La API crea el pedido en NEW sin ítems (`POST /api/orders/`) y los productos, el descuento y `prepare` se hacen con llamadas posteriores. La pantalla única (DDR-pedido-pantalla-unica-creacion-formulario-unico) arma un borrador en el navegador y necesita crear el pedido completo, ya en `IN_PREPARATION`, en una sola operación, guardando el almacén y validando el stock (decisiones de la persona). El stock hoy solo se valida al entregar (`DeliverOrder`).

## Decisión
1. **Endpoint nuevo `POST /api/orders/start/`** (módulo `sales`), aditivo; `POST /api/orders/` y los demás endpoints no cambian. Cuerpo: `customer_id?`, `sales_channel`, `order_date?`, `expected_delivery_date?`, `notes?`, `warehouse_id?`, `discount?` (por defecto 0) e `items: [{product_id, quantity}]` (≥ 1). Respuesta `201` con el pedido en `IN_PREPARATION` (mismo serializer de detalle, que añade `warehouse`).
2. **Caso de uso `PlaceOrder`** (`sales/application`): en una sola transacción reutiliza el agregado: `Order.create` → `add_item` por línea (precio y nombre vigentes del catálogo, validaciones de `AddOrderItem`) → `apply_discount(discount, max_discount_percent)` → asigna el almacén → valida stock → `start_preparation()`. Si cualquier paso falla, no se guarda nada. Errores de campo en 400 (con `items` indexados por línea); reglas de negocio en 409.
3. **Almacén en el agregado:** `Order.warehouse_id: UUID | None` (sin FK a Inventory; solo el id, como `customer_id`), asignado por un método del agregado al colocar el pedido. Migración `sales/0004` **aditiva**: columna nullable. Pedidos existentes quedan en `NULL`.
4. **Validación de stock al iniciar preparación** (solo con Inventario habilitado y productos que controlan stock): `warehouse_id` es obligatorio y debe ser un almacén activo; por cada producto controlado (cantidades sumadas) el saldo del almacén debe cubrir la cantidad, salvo que la empresa permita stock negativo. Reutiliza el puerto `StockOutput` (`controlled_products`, `active_warehouses`, `balances`, `allow_negative_stock`) y responde `409 insufficient_stock` con el mismo cuerpo que la entrega. **No reserva** stock: no escribe movimientos.
5. **Entrega:** `DeliverOrder` usa `order.warehouse_id` cuando el cuerpo no trae `warehouse_id`, y `PreviewOrderDelivery` lo propone como almacén seleccionado; el diálogo puede cambiarlo y la validación de stock al entregar se mantiene.
6. **Estado NEW:** se conserva en dominio, API y detalle para los pedidos existentes; ningún flujo nuevo lo produce. Sin migración de datos.
7. **Contabilidad:** sin cambios; `start_preparation` no genera asiento (el ingreso se reconoce al entregar).

## Alternativas consideradas
- **Extender `POST /api/orders/` con `items`/`warehouse_id`:** cambia el contrato existente (lo usa la importación de ventas y las pruebas) y mezcla dos intenciones; descartada en favor de un endpoint aditivo.
- **Orquestar en el navegador (crear NEW → agregar ítems → descuento → `prepare`):** no es atómico, deja pedidos a medias si falla un paso y N viajes de red; descartada.
- **Reservar stock al iniciar preparación:** fuera del pedido (la persona pidió validar, no reservar) y exige modelo de reservas en Inventory; descartada (sin reservas en el MVP).
- **Almacén solo informativo o guardado sin validar:** descartadas por la persona.
- **Eliminar NEW con migración a IN_PREPARATION:** descartada por la persona (riesgo contable y de datos).

## Estrategia de rollback / mitigación
- Migración aditiva y nullable: revertir el despliegue del código deja la columna sin uso sin pérdida de datos; revertir la migración elimina solo ese campo (no hay datos de negocio previos que dependan de él).
- El endpoint nuevo no altera los existentes: el frontend anterior sigue funcionando contra un backend con el cambio, y el flujo viejo (`/orders/` + detalle) sigue disponible en la API.
- Antes de desplegar, el backup que ya hace `deploy.yml` cubre la migración.

## Consecuencias
- El stock puede faltar entre «iniciar preparación» y «entregar»; la entrega sigue validando.
- `delivery.py` y `PlaceOrder` comparten la lógica de líneas controladas y de faltantes (se extrae lo común sin crear abstracciones nuevas).
- El contrato de detalle de pedido gana `warehouse` (`{id, name}` o `null`); compatible hacia atrás.
- Sin idempotencia en el endpoint: un reintento tras un 201 perdido crearía un segundo pedido (riesgo aceptado, mitigado en la UI).
