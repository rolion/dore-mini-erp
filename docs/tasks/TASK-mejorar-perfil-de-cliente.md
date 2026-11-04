# TASK-mejorar-perfil-de-cliente: Perfil de cliente accionable con resumen de compras y saldo

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-mejorar-perfil-de-cliente
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Task creado a partir de la crítica de diseño de la pantalla de perfil de cliente | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN → PLANNING | Veredicto NEEDS_PLAN, DDR y PLAN v1 escritos; Specification READY | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | Plan listo para implementar | delivery-start |

## Investigación

### Requerimiento
Sin argumento explícito: el requerimiento es la crítica de diseño previa de la página «Perfil del cliente» (captura adjunta por el usuario, etapa de refinamiento). Objetivo: mejorar usabilidad, jerarquía de información y presentación **conservando la funcionalidad y el sistema de diseño**, de modo que el perfil responda: quién es y cómo contactarlo, su actividad de compra, cuándo compró por última vez, cómo encontrar/inspeccionar un pedido y qué acciones hay. Distinguir total, estado de pago y saldo pendiente; cubrir cliente sin compras, historiales largos, responsive y accesibilidad. Textos de cara al usuario en español (con es/en/pt). Solo se recomiendan métricas respaldadas por datos existentes. Esto es insumo, no una Specification aprobada.

### Hechos encontrados
- `frontend/panel_admin/src/app/features/customers/pages/customer-detail/customer-detail.component.html:22-43` — datos en `dl.row` con 7 filas (Nombre duplicado del `h4`, teléfono y correo como texto plano, Creado/Actualizado con el mismo peso que el contacto).
- `customer-detail.component.html:44-50` — acciones (Editar primario, Desactivar `btn-warning`, Volver) bajo los datos; no hay acción para crear un pedido.
- `frontend/panel_admin/src/app/features/customers/components/customer-purchase-history/customer-purchase-history.component.html:11-31` — tabla con Fecha (enlace al pedido), Total, Estado y Pago como texto plano; sin saldo ni código de pedido.
- `customer-purchase-history.component.html:33-37` y `38-40` — nota «Se muestran los N pedidos más recientes de M» y estado vacío de una frase.
- `frontend/panel_admin/src/app/features/customers/services/customer-orders-api.service.ts:10,38-55` — consulta `GET /api/orders/?customer_id=…&page_size=100`; el DTO local solo mapea `id`, `order_date`, `total`, `status`, `payment_status`.
- `frontend/panel_admin/src/app/features/customers/models/customer.ts:45-55` — `CustomerOrderSummary { id, date, total, status, paymentStatus }`.
- **El backend ya entrega lo que falta:** `backend/modules/sales/api/serializers.py:165-175` (`OrderSummarySerializer`) devuelve `paid_total` y `balance`; `serializers.py:64-68` añade `code` (`order_code(obj.id)`); `frontend/.../sales/services/orders-api.service.ts:161-175` ya los mapea para Sales. **No hace falta cambio de backend** (corrige la estimación de la crítica previa, que lo daba por necesario).
- `backend/modules/sales/api/filters.py:53` y `backend/modules/sales/domain/repositories.py:15` — filtro `customer_id` y orden por defecto más reciente primero.
- `backend/modules/sales/infrastructure/django/read_queries.py:17-20` — regla de negocio existente de «pedido válido» para totales: excluye `CANCELLED` (y pedidos sin ítems).
- `frontend/.../sales/pages/order-list/order-list-filters.ts:87,122-128` — la lista de pedidos ya acepta `customer` y `customer_name` por query string.
- `frontend/.../sales/pages/order-form/order-form.component.ts:75-118` — el formulario de pedido no lee query params; el cliente se elige con `ng-select` (solo clientes activos, líneas 76-85).
- `frontend/.../sales/components/{order,payment}-status-badge/*.ts` — badges con texto + icono; su `input` está tipado con `OrderStatus`/`PaymentStatus` de Sales (los usa `order-list`, `order-detail` y el dashboard).
- `frontend/panel_admin/src/app/shared/pipes/money.pipe.ts` — pipe `money` estándar (`Bs 70.00`, vacío → `—`). No existe ninguna utilidad de suma decimal en el frontend ni librería decimal en `package.json`.
- `docs/design/design-system.md` secciones 3 (badges, `money`), 5 (plantilla de Detalle: `dl.row`, acciones bajo los datos, «Sin …») y 4 (estados).
- `docs/adr/ADR-clientes-mvp-historial-compras.md:11-13,19` — Customers no importa Sales en backend; el historial lo consume el frontend desde `/api/orders/`; la alternativa de agregados en servidor se difirió hasta que el perfil «necesite agregados (total comprado, última compra)».
- No hay teléfono con enlace `tel:`/WhatsApp en ninguna plantilla de la app (Grep sin resultados fuera de plantillas de ejemplo).

### Hipótesis / supuestos no confirmados
- El teléfono se guarda normalizado en formato internacional (`+591…`, ver `CUSTOMER_FORM.SE_GUARDARA_NORMALIZADO…`); se asume que quitar todo lo que no sea dígito da un número válido para `wa.me`.
- Los importes de la API son cadenas decimales de 2 posiciones (`_money()`); la suma en el frontend se hará sobre enteros mínimos (sin `float`).
- Con el módulo Pedidos deshabilitado, `GET /api/orders/` fallaría; el historial ya maneja el error sin ocultar el perfil. Se confirmará en build cómo ocultar «Nuevo pedido» (`ModulesService`).

### Módulos y dependencias relacionadas
Frontend `features/customers` (detalle + historial), `features/sales` (formulario de pedido, lista de pedidos, badges), `shared/pipes/money`. Backend: ninguno.

### Implementaciones similares existentes
Detalle de producto (`features/products/pages/product-detail`), tarjetas de cifras del dashboard (`features/reporting`, `app-report-card`) y tabla apilada en móvil (`features/inventory/components/_inventory-table.scss`).

### Comportamiento actual
Ver «Hechos encontrados»: el perfil muestra datos y una tabla básica; no hay acciones de contacto ni de crear pedido, ni resumen, ni saldo.

### Restricciones
`CLAUDE.md`: sin texto hardcodeado (claves es/en/pt + `npm run i18n:check`), `tr()` solo en funciones, dinero sin `float`, sin `any`, Reactive Forms, sin suscripciones colgadas, avisar antes de instalar dependencias (no se instala ninguna).

### Riesgos identificados
- Agregados calculados sobre los 100 pedidos cargados: si el cliente tiene más, serían parciales (se avisa en pantalla).
- Cruce de límites entre `features/customers` y `features/sales` en el frontend (ya hay precedente con Reporting y la lista de pedidos).

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado al frontend (customers y un prefill en el formulario de pedido), sin decisión arquitectónica nueva, sin cambios de API, datos ni permisos.

### Diseño requerido
**SI** — reorganiza una pantalla existente (jerarquía, tarjetas de cifras, tabla con estados) y debe seguir el sistema de diseño.

## Diseño
Ver `docs/design/DDR-mejorar-perfil-de-cliente-perfil-accionable.md`.

## Arquitectura
No aplica según veredicto.

## Plan
Ver `docs/plans/PLAN-2026-11-04-mejorar-perfil-de-cliente.md` (v1, COMPLETO: cálculo financiero y frontera entre contextos).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
