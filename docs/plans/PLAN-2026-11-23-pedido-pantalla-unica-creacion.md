# PLAN-2026-11-23-pedido-pantalla-unica-creacion (v4)

**Task:** TASK-pedido-pantalla-unica-creacion · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-pedido-pantalla-unica-creacion-formulario-unico · DDR-pedido-pantalla-unica-creacion-detalle-pedido-en-curso · ADR-pedido-pantalla-unica-creacion-creacion-atomica

## Objective
Crear un pedido en una sola pantalla (cabecera, detalle de productos, descuento y totales) cuyo botón «Iniciar preparación» crea el pedido ya en `IN_PREPARATION`, guardando el almacén y validando el stock en ese almacén.

## Context
Hoy el alta son dos pantallas (datos y detalle) y el stock solo se valida al entregar. Ver `docs/tasks/TASK-pedido-pantalla-unica-creacion.md`.

# Specification

## Domain context
Bounded context **Sales** (agregado `Order`). Relacionados: Catalog (precio/estado), Customers (cliente), Inventory (almacén, saldos, stock negativo), Modularity (descuento máximo). Fronteras solo por fachadas/puertos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Iniciar preparación | Confirmar el pedido: pasa a `IN_PREPARATION` (exige ≥ 1 producto) | `domain/order.py:320` |
| Descuento máximo | Tope en % del subtotal de la empresa (`sales.max_discount_percent`) | `modularity/domain/settings.py:51` |
| Almacén del pedido | Almacén desde el que se atenderá y se descontará el stock | decisión de la persona |
| Stock controlado | Producto que controla existencias (Inventario habilitado) | `application/delivery.py:35` |

## Current behavior
Ver TASK → «Comportamiento actual».

## Expected behavior
- `/pocketbiz/sales/orders/new` muestra una única pantalla; al pulsar «Iniciar preparación» se crea un pedido con cabecera, productos y descuento, en estado `IN_PREPARATION`, y se navega a su detalle.
- No se crea nada hasta pulsar el botón (el borrador vive en el navegador).
- El almacén se guarda en el pedido; la entrega lo propone por defecto.

## Domain rules / invariants
- **INV-01 (existente)** Un pedido confirmado tiene ≥ 1 producto sin duplicar producto (`add_item`, `start_preparation`).
- **INV-02 (existente)** Descuento ≤ subtotal y ≤ `max_discount_percent` % del subtotal (`apply_discount`).
- **INV-03 (existente)** El precio y el nombre del producto los fija el servidor al crear; el cliente nunca los envía.
- **INV-04 (nueva)** Con Inventario habilitado y al menos un producto controlado, el almacén es obligatorio y debe estar activo.
- **INV-05 (nueva)** Con esas condiciones, por cada producto controlado `saldo(almacén) ≥ cantidad total` salvo política de stock negativo; si no, se rechaza todo el pedido (409 `insufficient_stock`).
- **INV-06 (nueva)** La creación es atómica: o queda el pedido completo en `IN_PREPARATION` o no queda nada.
- **INV-07 (nueva)** Estados cambian por métodos del agregado (`place`/`start_preparation`), nunca por asignación.

## Acceptance criteria
- **AC-01** Una sola pantalla en `/orders/new` con: Cliente, Canal de venta, Fecha del pedido, Fecha de entrega, Almacén, bloque «Detalle del pedido» (Producto, Cantidad, Agregar), tabla de productos, Subtotal, Descuento, Total e «Iniciar preparación».
- **AC-02** Agregar un producto calcula su subtotal (precio × cantidad); agregar uno ya listado suma la cantidad; se puede editar la cantidad y quitar una fila.
- **AC-03** Subtotal = suma de subtotales; Total = Subtotal − Descuento; ambos de solo lectura.
- **AC-04** El descuento no puede superar el máximo permitido en la configuración de Ventas: la pantalla lo indica y bloquea el envío; el servidor lo rechaza igualmente (400, campo `discount`).
- **AC-05** «Iniciar preparación» está deshabilitado sin productos, con datos inválidos o mientras envía; al crear, el pedido queda en `IN_PREPARATION` con sus productos, descuento y almacén.
- **AC-06** Si falta stock en el almacén elegido, no se crea el pedido, se muestran los productos afectados (disponible vs. pedido) y se conserva lo escrito.
- **AC-07** La entrega de un pedido con almacén guardado lo propone preseleccionado; el diálogo puede cambiarlo y se revalida el stock al entregar.
- **AC-08** Los pedidos NEW existentes siguen abriéndose, editándose y preparándose como hoy; `POST /api/orders/` y demás endpoints no cambian.
- **AC-09** Con Clientes o Inventario deshabilitados, la pantalla oculta el combobox correspondiente y el servidor no exige ni valida esos datos.
- **AC-10** Aislamiento por empresa: no se aceptan cliente, producto ni almacén de otra empresa.
- **AC-11** El detalle de un pedido en `IN_PREPARATION`, `READY` o `DELIVERED` muestra en la cabecera código, badge de estado y badge de cobro, con las acciones a la derecha (DDR detalle en curso).
- **AC-12** «Marcar listo» (en `IN_PREPARATION`) actualiza el estado del pedido; en `READY` el botón primario es «Marcar entregado»; en `DELIVERED` no hay botón primario.
- **AC-13** «Registrar pago» (visible solo si el servidor permite cobrar) abre un modal; al confirmar, el pago queda registrado y el detalle muestra el pedido actualizado; los errores del servidor se ven en el modal sin perder lo escrito.
- **AC-14** El detalle muestra, en solo lectura: Cliente, Canal, Fecha del pedido, Fecha de entrega y Almacén (si existe); tabla Producto/Precio unitario/Cantidad/Subtotal; Subtotal, Descuento, Total, **Pagado y Saldo**; y el detalle de pagos.
- **AC-15** Los pedidos `NEW` y `CANCELLED` conservan el detalle actual.

## Edge cases / Error cases
- Sin productos → 400 `items`. Producto inactivo/no vendible/inexistente, repetido o con cantidad no entera o < 1 → 400 `items`, con un texto por problema que empieza por «Línea N:».
- Producto repetido en el cuerpo → 400 (la UI nunca lo envía; suma cantidades).
- Almacén inexistente/inactivo/de otra empresa → 400 `warehouse_id`. Almacén ausente con producto controlado → 400 `warehouse_id`.
- Productos sin stock controlado (servicios) → no exigen almacén ni stock.
- Cliente inactivo/inexistente → 400 `customer_id`. Fecha de entrega anterior a la del pedido → error existente de `_validate_details`.
- Fallo en cualquier paso → rollback total, sin pedido ni movimientos.
- Error de red → mensaje genérico, lo escrito se conserva, botón se rehabilita.

## Authorization / permissions
Mismos permisos que la creación actual: usuario autenticado con empresa y módulo `sales` habilitado (`required_modules = ('sales',)`); `company_id` sale del usuario, nunca del cuerpo.

## API contract
- **API-01** `POST /api/orders/start/` — cuerpo y respuesta según ADR; `201` con `OrderSerializer` (+ `warehouse: {id, name} | null`); `400` errores por campo (`items` como lista de textos «Línea N: …», uno por problema); `409` `{code, detail}` para reglas (`insufficient_stock` con `lines` y `warehouse`).
- **API-02** `GET /api/orders/{id}/` y respuestas de pedido añaden `warehouse` (nullable). Compatible hacia atrás.
- **API-03** `POST /api/orders/{id}/deliver/` y `GET .../delivery-preview/` usan `order.warehouse_id` como valor por defecto cuando no se envía `warehouse_id`.
- **API-04** `GET /api/settings/sales/` ya expone `sales.max_discount_percent` (sin cambio).

## UI behavior
- **UI-01** Plantilla «Variante de un solo paso con totales calculados» (DDR): cabecera de dos columnas, bloque de detalle, tabla, totales a la derecha, botón primario a la derecha.
- **UI-02** Estados: cargando, vacío («Agregue al menos un producto»), error por campo, 409 de stock con `alert-warning` y filas `table-warning`, éxito con toast y navegación al detalle.
- **UI-03** Almacén preseleccionado (único activo o predeterminado); visible solo con Inventario; Cliente visible solo con Clientes.
- **UI-04** Importes con función pura en centavos; ayuda del descuento: «Máximo permitido: X % del subtotal».
- **UI-05** Salir con cambios usa `unsavedChangesGuard`; accesibilidad: `label` por control, `aria-label` en quitar y en la cantidad de cada fila.
- **UI-06** Textos con claves i18n en es/en/pt.

## Non-functional requirements
Creación en una transacción; respuesta con ≤ 1 consulta de saldos por almacén; sin N+1 al validar líneas; Decimal en backend.

## Out of scope
Reservas de stock; cobros/pagos al crear; eliminar el estado NEW o migrarlo; cambiar el detalle más allá de mostrar el almacén; importación de ventas; idempotencia del endpoint; edición del almacén de un pedido ya creado.

## Open questions
- Ninguna que bloquee. (Notas se conserva como campo opcional; el cliente sigue opcional.)

# Test Specification

## Unit tests
- Dominio: `Order.place` / asignación de almacén; INV-01/02/06/07; estado final `IN_PREPARATION`.
- Frontend: función pura de importes (suma, descuento, total, redondeo a centavos); tope de descuento; fusión de producto repetido.

## Integration tests
- Backend (`DJANGO_SETTINGS_MODULE=config.settings.test`, PostgreSQL): `PlaceOrder` y `POST /api/orders/start/` — creación completa, descuento sobre el tope, sin productos, producto inactivo, cliente inactivo, almacén ausente/inactivo/ajeno, stock insuficiente (con y sin política de stock negativo), Inventario/Clientes deshabilitados, rollback total, aislamiento por empresa, entrega que usa el almacén guardado, NEW antiguo intacto.
- Frontend (Karma, `provideTestTranslations()`): componente `order-create` — estructura, agregar/editar/quitar, totales, deshabilitado del botón, errores 400/409, ocultar combobox por módulo, navegación al éxito; `orders-api.service` — `start`; `sales-settings.service` — `maxDiscountPercent`; `delivery-dialog` — almacén preseleccionado.

## E2E
**NO** — el flujo se cubre con integración de API y de componente; no hay infraestructura E2E en el repositorio y no se instala Playwright para esta tarea.

## Regression tests
Suites existentes de `sales` (`test_api`, `test_delivery_*`, `test_sales_posting`), `order-form`, `order-detail`, `order-items`, i18n (`npm run i18n:check` y prueba de claves).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | spec componente `order-create` (estructura) + revisión visual |
| AC-02 | spec componente + unit función pura |
| AC-03 | unit función pura + spec componente |
| AC-04 | unit frontend (tope) + API test backend 400 `discount` |
| AC-05 | spec componente (botón) + API test (estado y contenido) + dominio |
| AC-06 | API test `insufficient_stock` + spec componente (409) |
| AC-07 | API test de entrega con almacén guardado + spec `delivery-dialog` |
| AC-08 | regresión `sales` + spec `order-form`/`order-detail` |
| AC-09 | API tests con módulos deshabilitados + spec componente |
| AC-10 | API test de aislamiento por empresa |
| AC-11 | spec `order-detail` (cabecera con código y badges) |
| AC-12 | spec `order-detail` («Marcar listo» actualiza el estado; READY y DELIVERED) |
| AC-13 | spec `order-detail` (abre el modal) + spec `payment-dialog` (registro, errores, reintento) |
| AC-14 | spec `order-detail` (datos, productos, importes incl. Pagado y Saldo, y pagos de solo lectura) |
| AC-15 | spec `order-detail` (NEW y CANCELLED conservan el detalle) |

# Implementation Plan

## Architecture considerations
Ver ADR. Endpoint aditivo; lógica en el agregado y un caso de uso nuevo; stock vía puerto `StockOutput` existente; sin importar infraestructura entre módulos.

## Proposed solution
`Order.warehouse_id` + `Order.place(...)` (o método equivalente que asigna almacén y llama `start_preparation`) en dominio; `PlaceOrder` en `application/commands.py` (o `placement.py`) que compone `AddOrderItem`-like validaciones, descuento y verificación de stock compartiendo `controlled_lines`; vista `OrderStartView` y serializers; frontend: `OrderCreateComponent` + función pura de importes + `OrdersApiService.start` + `maxDiscountPercent` en `SalesSettingsService`.

## Files/components affected
- **Backend:** `sales/domain/order.py` (campo y método), `sales/application/commands.py` + `delivery.py` (caso de uso y reutilización), `sales/api/views.py`, `serializers.py`, `urls.py` (endpoint y `warehouse` en la salida), `sales/infrastructure/django/models.py`, `mappers.py`, `repositories.py`, `read_queries.py` si aplica, `adapters.py`, migración `sales/0004`, `DeliverOrder`/`PreviewOrderDelivery` (almacén por defecto), tests en `sales/tests/`.
- **Frontend:** `features/sales/pages/order-create/*` (nuevo), `sales.routes.ts`, `models/order.ts`, `services/orders-api.service.ts`, `services/sales-settings.service.ts`, `components/delivery-dialog` (preselección), `components/order-summary` (fila almacén), `assets/i18n/{es,en,pt}.json`, specs.
- **Docs:** `docs/design/design-system.md` (añadir `order-create` como referencia de la variante) en el PR de publicación.

## Implementation steps
1. **Dominio** (INV-04/06/07): `warehouse_id` en `Order`, método de colocación en preparación; pruebas unitarias.
2. **Migración + mapper/repositorio** (`makemigrations`, columna nullable); pruebas de persistencia.
3. **Caso de uso `PlaceOrder`** (INV-01..06): validaciones de ítems, descuento, cliente, almacén y stock; transacción única; pruebas de aplicación con fakes.
4. **API** `POST /orders/start/` y `warehouse` en la salida (API-01/02); pruebas de API (AC-04..06, 09, 10).
5. **Entrega**: almacén guardado como valor por defecto en `DeliverOrder` y vista previa (API-03, AC-07).
6. **Frontend servicios y modelos**: `start`, `warehouse`, `maxDiscountPercent`; función pura de importes con pruebas.
7. **`OrderCreateComponent`** (UI-01..06, AC-01..05, 09): cabecera, detalle, tabla, totales, errores, guard de salida; ruta `new`.
8. **Detalle y diálogo de entrega**: mostrar y preseleccionar el almacén (AC-07).
9. **i18n** es/en/pt, `npm run i18n:check`, lint (`ruff`/`flake8` en `.py` cambiados; `npm run lint`), `npm test`, `python manage.py test modules.sales`.

## Database / migrations
Nueva `sales/0004_order_warehouse.py`: `warehouse_id` UUID nullable, sin FK entre módulos. No se edita ninguna migración aplicada.

## Risks
- Stock sin reserva (entre iniciar preparación y entregar). Mitigación: la entrega revalida.
- Duplicado por reintento sin idempotencia. Mitigación: botón deshabilitado mientras envía.
- Diferencia entre importes del navegador y del servidor. Mitigación: la función pura replica la regla; manda el servidor tras crear.
- Ruta `new` deja de usar `OrderFormComponent`; `:id/edit` debe seguir funcionando.

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-23): [Specification] Aprobado por el usuario: API-01 y edge cases pasan de errores de `items` indexados por línea a una lista de textos «Línea N: …» (REV-05); UI-05 deja de exigir el foco al producto tras agregar (REV-03). Solicitado por delivery-publish (REV-03, REV-05).
- **v3** (2026-11-23): [Specification] Solicitado por el usuario en el mismo PR: AC-11..AC-15 (nuevo detalle del pedido en preparación, listo y entregado, con modal de pago). Ver DDR-pedido-pantalla-unica-creacion-detalle-pedido-en-curso.
- **v4** (2026-11-23): [Specification] Aprobado por el usuario: AC-14 añade «Pagado» y «Saldo» a los importes del detalle (REV-10). Solicitado por delivery-publish (REV-10).
