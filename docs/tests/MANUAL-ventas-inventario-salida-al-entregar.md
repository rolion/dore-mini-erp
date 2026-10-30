# Prueba manual: salida de inventario al entregar un pedido (PB-INT-002)

Task: `TASK-ventas-inventario-salida-al-entregar` · Plan: `docs/plans/PLAN-2026-10-29-ventas-inventario-salida-al-entregar.md`

Sirve de evidencia de UI y API para la historia. Adjunta capturas o respuestas a la tarea o al PR.

## Preparación

1. Backend (desde `backend/`, con `.env` y PostgreSQL): `python manage.py migrate` y `python manage.py runserver`.
2. Frontend (desde `frontend/panel_admin/`): `npm start`.
3. Regístrate en `http://localhost:4200/pocketbiz/signup` e inicia sesión. En Configuración → Módulos habilita **Inventario**.
4. Inventario: almacén «Central» (y, para B4, otro «Zona»). Productos: «Bolsas» (control de stock, unidad `u`, sin fracciones) y «Servicio» (sin control de stock).
5. Inventario → Existencias iniciales: **5 u** de Bolsas en «Central».

## A. Entrega con stock suficiente (AC-01, AC-09, AC-12)

| # | Paso | Resultado esperado |
|---|---|---|
| A1 | Crea un pedido con **4** Bolsas, confírmalo («Iniciar preparación») y márcalo listo; registra un cobro total | Inventario → Existencias sigue en **5** (crear, preparar, listo y cobrar no descuentan) |
| A2 | En el detalle pulsa «Marcar como entregado» | Se abre el diálogo: referencia `P-…`, fecha de hoy, «Central» (único almacén), tabla Bolsas · 4 · u · existencia 5 · saldo proyectado 1; sin avisos |
| A3 | «Cancelar» | El diálogo se cierra; el pedido sigue en «Listo»; Existencias en 5 |
| A4 | Vuelve a abrirlo y pulsa «Confirmar entrega» (haz doble clic rápido) | El botón pasa a «Confirmando…» y se deshabilita; el pedido queda «Entregado» y se ve la tarjeta **Salida de inventario** (referencia, Central, fecha, Bolsas 4 u). Estado de entrega y de cobro siguen en paneles separados |
| A5 | Pulsa «Ver movimientos» | Inventario → Movimientos filtrado por el pedido (chip «Pedido P-…»): una fila **Salida por venta**, Central, 4 u, tu usuario; el enlace del movimiento abre el pedido |
| A6 | Inventario → Existencias | Bolsas en Central = **1** (solo hubo una salida) |

## B. Política de stock insuficiente (AC-02, AC-03)

| # | Paso | Resultado esperado |
|---|---|---|
| B1 | Crea otro pedido de **4** Bolsas hasta «Listo» (el saldo es 1) y abre «Marcar como entregado» | Tabla: existencia 1, saldo proyectado **−3** (rojo, con icono y texto «negativo»); alerta roja «Existencia insuficiente en Central» con producto, solicitado 4 y existencia 1; **«Confirmar entrega» deshabilitado**; no hay «Continuar de todos modos» ni enlace para cambiar la política |
| B2 | Cierra y comprueba el pedido | Sigue «Listo»; sin movimientos nuevos |
| B3 | Inventario → Ajustes: activa «Permitir stock negativo» (confirmando el diálogo). Reabre la entrega | Alerta **amarilla** «dejará saldo negativo… política configurada»; el botón se habilita. Confirma: el pedido queda «Entregado» y el saldo final es **−3** |
| B4 | Con un segundo almacén «Zona» (predeterminado) crea y deja listo un pedido de Bolsas | El diálogo ofrece un selector con «Zona (predeterminado)» preseleccionado; al cambiar a «Central» la tabla recalcula existencias |
| B5 | Dos pestañas con el mismo pedido «Listo»; entrega en una y luego intenta en la otra | La segunda recibe aviso («el pedido cambió»), se recarga y no se duplica la salida |
| B6 | Desactiva todos los almacenes y abre la entrega de un pedido con Bolsas | Alerta amarilla que explica «No hay un almacén activo… Inventario → Configuración → Almacenes»; confirmación deshabilitada |

## C. Casos sin salida (AC-06, AC-08)

| # | Paso | Resultado esperado |
|---|---|---|
| C1 | Pedido solo con «Servicio» | «Marcar como entregado» muestra la confirmación habitual (solo fecha, sin almacén); no hay tarjeta de salida ni movimientos |
| C2 | Pedido con Bolsas y Servicio | Solo Bolsas aparece en el diálogo y en los movimientos |
| C3 | Deshabilita Inventario, entrega un pedido con Bolsas | Confirmación habitual sin almacén; al volver a habilitar Inventario no hay movimiento retroactivo ni tarjeta |
| C4 | Pedido entregado | No permite editar ítems ni cancelar (409) |

## D. API (AC-07, AC-11, AC-15) — sustituye `TOKEN`, ids y `HOST`

```bash
curl -s -H "Authorization: Token TOKEN" "http://HOST:8000/api/orders/<id>/delivery-preview/"
```

```bash
curl -s -X POST -H "Authorization: Token TOKEN" -H "Content-Type: application/json" -d '{"warehouse_id":"<almacen>"}' "http://HOST:8000/api/orders/<id>/deliver/"
```

- Sin `warehouse_id` con productos controlados → 400 `{"warehouse_id": [...]}`.
- Con un `warehouse_id` de **otra empresa** o inactivo → 400; el pedido sigue «Listo».
- Con saldo insuficiente y bloqueo → 409 `insufficient_stock` con `warehouse` y `lines[]` (producto, unidad, `requested`, `available`).
- Repetir el POST sobre un pedido entregado → 409 `invalid_transition`; sin movimientos nuevos.
- `GET /api/stock-movements/?source_type=sales_order&source_id=<id>` lista solo las salidas de ese pedido.

## E. Concurrencia (PostgreSQL)

Con bloqueo de negativos, saldo 5 y dos pedidos de 4: `python manage.py test modules.sales.tests.test_delivery_inventory.ConcurrentDeliveryTests` → una entrega 200, la otra 409; un solo movimiento.
