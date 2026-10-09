# TASK-ciclo-pedido-entrega-cobro: Módulo Ventas (Sales): pedido → preparación → entrega → cobro, con estado logístico y de pago independientes

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** `task/TASK-ciclo-pedido-entrega-cobro`
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/7

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-08 | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |
| 2026-10-08 | DESIGN → ARCHITECTURE | Decisión de diseño registrada en 2 DDR (menú y lista de pedidos; formulario y detalle con ítems, estados, cancelación y pagos) | delivery-design |
| 2026-10-08 | ARCHITECTURE → PLANNING | Decisiones registradas en 5 ADR (modelo de dominio, contrato API, persistencia y concurrencia, integración Catalog/Customers, feature frontend); reglas de negocio confirmadas por el usuario | delivery-architect |
| 2026-10-08 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY; PR #7 abierto | delivery-plan |
| 2026-10-08 | ENGINEERING → REVIEW | Implementación completa según plan v1 (backend `sales`, frontend `features/sales`, historial del cliente, creación rápida, extracción a `shared/`) | delivery-engineer |
| 2026-10-08 | REVIEW → PLANNING | FAIL: 2 hallazgos IMPLEMENTATION (1 High, 1 Medium) y 1 SPECIFICATION (Low, decisión de negocio sobre precio 0); vuelve a la etapa más temprana implicada | delivery-review |
| 2026-10-08 | PLANNING → ENGINEERING | Plan v2 con aprobación del usuario (precio 0 permitido en ítems, REV-03); REV-01 y REV-02 se corrigen en implementación (Fase 10) | delivery-plan |
| 2026-10-08 | ENGINEERING → REVIEW | Plan v2 implementado (REV-01, REV-02 y REV-03 atendidos; humo manual hecho) | delivery-engineer |
| 2026-10-09 | REVIEW → PUBLISH | PASS en re-review sobre `3b55ffc`: REV-01, REV-02 y REV-03 cerrados; suites y humo manual en verde | delivery-review |

## Investigación

### Requerimiento
Objetivo: gestionar el ciclo Pedido → preparación → entrega → cobro. El estado logístico del pedido y el estado del pago son independientes. Alcance: REQ-SAL-001 a REQ-SAL-016.

- **REQ-SAL-001 Crear pedido** (MVP-Alta, dep. REQ-CAT-001): cliente opcional; al menos un producto antes de confirmar; fecha de pedido, canal de venta y notas opcionales; fecha de entrega opcional al crear. Aceptación: se puede iniciar y guardar un pedido válido; un pedido sin productos no se puede confirmar.
- **REQ-SAL-002 Agregar producto** (MVP-Alta, dep. REQ-CAT-003): solo productos activos; cantidad > 0; snapshot de nombre y precio. Aceptación: 2 unidades calculan bien el subtotal; un producto inactivo se rechaza.
- **REQ-SAL-003 Modificar cantidad** (MVP-Alta, dep. 002): en pedido editable; cantidad final > 0; recalcula subtotal de ítem y total.
- **REQ-SAL-004 Eliminar ítem** (MVP-Alta, dep. 002): mientras sea editable; un pedido confirmado no puede quedar sin ítems; recalcula total; si la eliminación deja el pedido inválido, impide confirmarlo.
- **REQ-SAL-005 Calcular subtotal y total** (MVP-Alta, dep. 002): subtotal = Σ subtotales de ítems; total = subtotal − descuento válido; `Decimal`; el usuario no altera el total directamente.
- **REQ-SAL-006 Aplicar descuento** (MVP-Media, dep. 005): total no negativo; descuento explícito en el pedido; descuento > subtotal se rechaza.
- **REQ-SAL-007 Canal de venta** (MVP-Alta, dep. 001): WhatsApp, Facebook, Instagram, venta directa, feria, otro; utilizable en reportes (Reporting agrupa por canal).
- **REQ-SAL-008 Estados del pedido** (MVP-Alta, dep. 001): NEW, IN_PREPARATION, READY, DELIVERED, CANCELLED; sin transiciones inválidas; CANCELLED no puede entregarse.
- **REQ-SAL-009 Fecha de entrega** (MVP-Alta, dep. 001): fecha prevista (modificable mientras el pedido siga abierto) y fecha real (al completar la entrega); consulta por fecha prevista.
- **REQ-SAL-010 Cancelar pedido** (MVP-Alta, dep. 008): motivo obligatorio; no continúa el flujo de entrega; los pagos registrados no desaparecen; conserva su historial.
- **REQ-SAL-011 Registrar pago** (MVP-Alta, dep. 001): uno o más pagos; monto > 0; método y fecha; métodos: efectivo, QR, transferencia, tarjeta, otro; aumenta el total pagado; disponible en el detalle.
- **REQ-SAL-012 Pagos parciales** (MVP-Alta, dep. 011): PaymentStatus PENDING / PARTIAL / PAID / REFUNDED derivado de los pagos; acumulado < total → PARTIAL; cubre el total → PAID.
- **REQ-SAL-013 Saldo pendiente** (MVP-Alta, dep. 012): saldo = total − pagos válidos acumulados; independiente del estado logístico; DELIVERED puede tener saldo; PAID muestra cero.
- **REQ-SAL-014 Listar y filtrar** (MVP-Alta, dep. 001): filtros mínimos estado, estado de pago, fecha, cliente, canal; orden por fecha relevante; localizar pendientes, entregados, cancelados y por cobrar.
- **REQ-SAL-015 Detalle del pedido** (MVP-Alta, dep. 001): cliente, ítems, importes, estados, pagos, canal, fechas, notas; se abre desde la lista.
- **REQ-SAL-016 Separar entrega y pago** (MVP-Alta, dep. 008 y 012): DELIVERED no implica PAID y PAID no implica DELIVERED; se pueden representar "entregado y pendiente de pago" y "pagado y pendiente de entrega".

### Hechos encontrados

**Estado del backend**
- `backend/modules/` contiene `accounts`, `catalog` y `customers`; **no existe `sales`** (`ls backend/modules`). No hay `Order`, `Payment` ni endpoint de pedidos: `backend/config/urls.py:6-11` solo monta `admin`, `health`, `auth`, `products` y `customers`.
- `backend/config/settings/base.py:20-22` registra `modules.accounts`, `modules.catalog`, `modules.customers` en `INSTALLED_APPS`; habría que registrar `modules.sales` y una ruta `api/orders/`.
- `backend/config/settings/base.py:70-86` — DRF con Token + Session, `IsAuthenticated` por defecto, solo `JSONRenderer`, `PageNumberPagination` con `PAGE_SIZE: 50`. No hay modelo de roles/permisos por módulo (todo usuario autenticado accede a todo).
- `backend/config/settings/test.py:1-9` — los tests exigen PostgreSQL vía `DATABASE_URL` (sin SQLite por regla del proyecto).
- `backend/shared/` solo contiene `__init__.py` (`ls backend/shared`): no existen `shared/domain/money.py`, `ids.py`, `date_range.py` ni `exceptions.py` previstos en `docs/architecture/ddd.md:811-826`. `Money` no existe como value object en ningún módulo.
- `backend/requirements/base.txt` — Django 5.2.17, DRF 3.18.1, psycopg 3.3.6, django-environ 0.14.0. Sin librerías de filtros (`django-filter`).
- Últimas migraciones: `backend/modules/catalog/migrations/0001_initial.py`, `backend/modules/customers/migrations/0001_initial.py`, `backend/modules/accounts/migrations/0001_initial.py` (sales tendría su propia `0001`).

**Patrón de referencia ya implementado (`catalog`, `customers`)**
- Dominio puro con dataclass: `backend/modules/catalog/domain/product.py:46-89` (`Product.create`, `rename`, `change_price`, `activate`, `deactivate`; validadores que acumulan errores por campo en `ProductValidationError`, `product.py:56-73`). Dinero validado como `Decimal` rechazando `float`/`bool`, 2 decimales, tope `9999999999.99` (`product.py:26-43`).
- Capa de aplicación con un caso de uso por clase y `execute` (`backend/modules/catalog/application/queries.py:9-25`); repositorio por interfaz de dominio (`domain/repositories.py`) con implementación Django que devuelve una lista perezosa paginable (`backend/modules/catalog/infrastructure/django/repositories.py:11-47`).
- API: vistas `APIView` delgadas que traducen excepciones de dominio a 400/404 (`backend/modules/catalog/api/views.py:22-29`), acciones `activate/` y `deactivate/` como POST (`views.py:69-78`), filtro `active` y `search` por query params (`views.py:40-47`), paginación propia con `page_size` máx. 100 (`api/pagination.py`).
- Modelo Django: UUID como PK, `created_at/updated_at`, `db_table` explícita, `ordering` (`backend/modules/customers/infrastructure/django/models.py:6-20`; análogo en catalog).
- `Customer.id` es UUID y `Customer` tiene `active` y no tiene borrado (`backend/modules/customers/infrastructure/django/models.py:7,13`). `Product` también (`product.py:47-53`).

**Dependencias de Sales hacia otros módulos (aún sin servicio)**
- `docs/adr/ADR-catalogo-productos-mvp-modelo-dominio.md:19` — el snapshot de nombre/precio es responsabilidad de `OrderItem`; el bloqueo de productos inactivos en pedidos "se hará cuando exista Sales, consultando a Catalog por un servicio de aplicación (`ddd.md:793-799`); ese servicio **no se construye ahora**". `docs/adr/ADR-catalogo-productos-mvp-modelo-dominio.md:17` — `Money` se introduce "cuando Sales lo necesite". Verificado: `grep for_sale` en `backend/` no devuelve resultados.
- `docs/adr/ADR-clientes-mvp-historial-compras.md:12` — contrato que Sales debe cumplir: `GET /api/orders/?customer_id=<uuid>` con paginación estándar, orden por fecha descendente, que devuelva por pedido `id`, fecha del pedido, total (string decimal) y estado; debe seguir funcionando para clientes inactivos. `:14` — Sales guarda `customer_id` como UUID sin FK entre apps y valida el cliente con un servicio de aplicación de Customers (`get_customer_for_sale`) "no construido ahora".
- Los productos y clientes no se eliminan nunca (sin `DELETE`; ADR catálogo `:19`, ADR clientes `:15`), así que las referencias `product_id`/`customer_id` de un pedido no quedarán huérfanas.

**Reglas de dominio documentadas (`docs/architecture/ddd.md`)**
- `:327-338` `Order` es el agregado raíz (`OrderItem` y referencias a `Payment`); `:341-359` campos conceptuales (`status`, `payment_status`, `sales_channel`, `order_date`, `delivery_date`, `subtotal`, `discount`, `total`, `notes`); `:363-376` `OrderItem` con snapshot `product_name`, `unit_price`; `:380-390` `Payment` (`order_id`, `amount`, `payment_method`, `payment_date`, `reference`, `status`).
- `:396-442` Value Objects: `OrderStatus` (NEW, IN_PREPARATION, READY, DELIVERED, CANCELLED), `PaymentStatus` (PENDING, PARTIAL, PAID, REFUNDED), `SalesChannel` (WHATSAPP, FACEBOOK, INSTAGRAM, **STORE**, FAIR, OTHER), `PaymentMethod` (CASH, QR, **BANK_TRANSFER**, CARD, OTHER), `Money` compartido con Catalog.
- `:450-465` reglas: al menos un producto, cantidad > 0, cancelado no se entrega, entregado no vuelve a NEW, total calculado en el dominio y no manual, pago sin monto negativo, la suma de pagos determina `PaymentStatus`, entregado y pagado independientes, producto desactivado no entra a nuevos pedidos, cancelar puede requerir razón.
- `:469-511` comportamientos del agregado: `add_item`, `change_quantity`, `apply_discount`, `mark_in_preparation`, `mark_ready`, `deliver`, `cancel(reason)`, `calculate_total`; el estado no se asigna directamente (`order.status = ...` desaconsejado).
- `:517-545` Commands (`CreateOrder`, `AddOrderItem`, `RemoveOrderItem`, `ChangeOrderItemQuantity`, `ApplyOrderDiscount`, `ConfirmOrder`, `StartOrderPreparation`, `MarkOrderReady`, `DeliverOrder`, `CancelOrder`, `RegisterPayment`, `RefundPayment`) y Queries (`GetOrder`, `ListOrders`, `SearchOrders`, `ListPendingOrders`, `ListPendingDeliveries`, `ListPendingPayments`, `ListOrdersByCustomer`, `ListOrdersByDateRange`).
- `:549-566` eventos de dominio: "no son obligatorios en el MVP".
- `:880-912` modelos Django vs entidades: separarlos "especialmente en dominios con lógica relevante como Sales".
- `:944-958` endpoints sugeridos: `GET/POST /api/orders`, `GET /api/orders/{id}`, `POST /api/orders/{id}/items`, `DELETE /api/orders/{id}/items/{item_id}`, `POST …/prepare`, `…/ready`, `…/deliver`, `…/cancel`, `POST …/payments`. No contemplan `PATCH` de pedido (fecha prevista, notas, descuento), cambio de cantidad, ni confirmar.
- `:1127-1161` flujo de pago: `payment.amount <= saldo permitido`, transición PENDING → PARTIAL → PAID.
- `:741-751` Reporting solo lee Sales.
- `:1011-1034` estructura Angular sugerida para sales: `pages/order-list|order-detail|order-create`, `components/order-form|order-items|order-status|payment-form`, `services/sales-api.service.ts`, `models/order.ts|payment.ts`, `sales.routes.ts`.

**Frontend**
- `frontend/panel_admin/src/app/features/` contiene `products/` y `customers/` (pages `*-list`, `*-form`, `*-detail`, servicios `*-api.service.ts`, `models`, `testing/*-fixtures.ts`, `*.routes.ts`); no existe `features/sales`.
- `frontend/panel_admin/src/app/app.routes.ts:20-29` registra `catalog/products` y `customers` con `loadChildren`; no hay ruta de pedidos.
- Menú: `frontend/panel_admin/src/assets/data/routes.json` tiene "Dashboard", "Catálogo ▸ Producto" (grupo `menu-toggle`) y "Cliente" (entrada directa, ícono `users`); títulos por claves `MENUITEMS.*` en `src/assets/i18n/{en,es,de}.json`. No hay entrada de ventas/pedidos.
- Dependencias de UI ya instaladas: `@swimlane/ngx-datatable ^22.0.0`, `@ng-select/ng-select ^21.1.4`, `sweetalert2`, `ngx-toastr` (`frontend/panel_admin/package.json:32,39,62,65`); tests con Karma/Jasmine (`package.json:8,88-92`).
- `frontend/panel_admin/src/app/features/customers/components/customer-purchase-history/` existe con estado vacío y **sin ninguna petición a pedidos** (según `docs/tasks/TASK-clientes-mvp.md`, sección Implementación): es el punto donde se conectará el historial real.
- No existe `frontend/panel_admin/src/app/shared/` (`ls`): `Page<T>` y estilos de acciones de tabla están duplicados entre `products` y `customers` y el task de clientes dejó anotado extraer a `shared/` "cuando haya una tercera feature" (`docs/tasks/TASK-clientes-mvp.md`, Deuda técnica) — Sales sería esa tercera feature.

### Hipótesis / supuestos no confirmados
- **Vocabulario "confirmar":** REQ-SAL-001/004 hablan de "confirmar" un pedido (y "pedido confirmado no puede quedar sin ítems") y `ddd.md:527` define el comando `ConfirmOrder`, pero `OrderStatus` (`ddd.md:396-404`) y REQ-SAL-008 no incluyen un estado "CONFIRMED"/"DRAFT". No se verificó qué significa confirmar: ¿la transición NEW → IN_PREPARATION?, ¿un indicador separado?, ¿se puede guardar un pedido NEW sin ítems ("iniciar y guardar un nuevo pedido válido")? Es la ambigüedad central del modelo de estados.
- **"Pedido editable":** REQ-SAL-003/004/009 usan "editable"/"abierto" sin definir en qué estados lo es (¿solo NEW?, ¿NEW e IN_PREPARATION?, ¿hasta READY?). No definido en ningún documento.
- **Transiciones permitidas:** no hay tabla. Se infiere NEW → IN_PREPARATION → READY → DELIVERED y cancelar desde algún estado previo a DELIVERED (REQ-SAL-010 "que todavía permita cancelación"); no se confirmó si se puede saltar pasos (NEW → READY, NEW → DELIVERED para venta directa/feria), ni si un pedido cancelado o entregado es terminal, ni si se puede cancelar un pedido ya entregado.
- **Cancelación y pagos:** REQ-SAL-010 dice que los pagos "no deben desaparecer automáticamente", pero no define el efecto sobre `PaymentStatus` de un pedido cancelado con pagos (¿queda PAID/PARTIAL, pasa a REFUNDED?), si el total pagado sigue contando para Reporting ("ventas cobradas", `ddd.md:706`), ni si existe un flujo de reembolso en este alcance (`RefundPayment` figura en `ddd.md:531`, pero no hay REQ-SAL de reembolso).
- **REFUNDED:** REQ-SAL-012 lo incluye como valor posible pero ningún REQ define cuándo se alcanza ni cómo se registra un reembolso; `Payment.status` (`ddd.md:389`) tampoco tiene valores definidos. "Pagos válidos acumulados" (REQ-SAL-013) sugiere que un pago puede ser inválido/anulado, sin definir cómo.
- **Sobrepago:** `ddd.md:1149` sugiere `payment.amount <= saldo permitido`, pero ningún REQ-SAL lo confirma (¿se rechaza un pago mayor al saldo?). Tampoco se define el PaymentStatus de un pedido de total 0 (descuento = subtotal, que REQ-SAL-006 permite porque solo rechaza descuento "superior" al subtotal) ni de un pedido sin pagos con saldo 0.
- **Descuento:** no se define si es monto fijo o porcentaje, si se puede quitar/modificar después, ni en qué estados; `ddd.md:354` lo lista como `discount` (monto). Se asume monto en `Decimal`.
- **Fecha de pedido / fecha de pago:** no se define si la fecha de pedido la ingresa el usuario o es automática (por defecto hoy), ni si admite fechas pasadas/futuras; lo mismo para `payment_date`. Se asume fecha sin hora. Zona horaria: `TIME_ZONE` por entorno (`base.py:63`).
- **Fecha real de entrega:** REQ-SAL-009 dice que se registra "al completar la entrega"; no se confirmó si es automática (hoy) o editable al marcar DELIVERED (venta atrasada), ni si puede ser anterior a la fecha de pedido.
- **Valores de canal/método:** los textos de los REQ ("venta directa", "transferencia") difieren de los identificadores de `ddd.md` (`STORE`, `BANK_TRANSFER`); se asume que los códigos de `ddd.md` son los internos y los textos de los REQ son etiquetas de UI. Si los valores son fijos (enumeración) o administrables tampoco se confirmó; "valores iniciales" podría implicar catálogo ampliable.
- **Cliente opcional:** "asociado opcionalmente a un cliente" (venta de mostrador sin cliente); no se definió si hay un "cliente genérico" o `customer_id` nulo, ni si al desactivarse un cliente se bloquea su uso en pedidos nuevos (ADR clientes `:14` dice que Sales validará "existe y está activo" pero solo para el caso de uso futuro).
- **Persistencia del descuento/total:** no se confirmó si `subtotal`/`total`/`payment_status`/saldo se persisten como columnas o se calculan al leer (impacta en filtros por estado de pago y en la lista paginada — REQ-SAL-014 — porque `payment_status` derivado de pagos requiere agregación SQL o una columna desnormalizada).
- **Concurrencia:** no se verificó si hay riesgo de pagos simultáneos que excedan el saldo o de ediciones concurrentes del mismo pedido (un solo operario en el MVP, no confirmado).
- **Permisos:** no hay roles; se asume que cualquier usuario autenticado puede ejecutar todas las operaciones (cancelar, registrar pagos).
- **Alcance de frontend:** el task no dice si incluye la UI completa (lista, creación/edición, detalle, pago, cambio de estado) y la entrada de menú. Se asume que sí, siguiendo los task de catálogo y clientes (que incluyeron backend + frontend + menú), pero no se confirmó. Tampoco se pidió explícitamente conectar el historial del cliente ni validación cliente activo; se asume que conectar `customer-purchase-history` entra por la dependencia declarada en el ADR de clientes, no confirmado.
- **Reporting:** REQ-SAL-007 menciona "Reporting puede agrupar ventas por canal"; se asume que basta con que el canal esté persistido y filtrable (el módulo `reporting` no existe y no es parte de este task).
- **Descripción del producto en el ítem:** el snapshot cubre nombre y precio (REQ-SAL-002); no se confirmó si también SKU/descripción (el producto no tiene SKU hoy).
- No se verificó el contenido de la base de datos local ni migraciones aplicadas. No se verificó que la suite completa de Angular compile hoy en `main` (el task de catálogo documentó specs de plantilla fallando y `app.component.spec.ts` sin compilar).

### Módulos y dependencias relacionadas
- **Backend:** nuevo bounded context `sales` (capas `domain/application/infrastructure/api`), con migración inicial (tablas de pedido, ítems y pagos), registro en `INSTALLED_APPS` (`base.py:20-22`) y `config/urls.py:6-11`. Es el **tercer bounded context de negocio** y el primero con un agregado con varias entidades hijas, máquina de estados y valores derivados.
- **Cruza límites de módulo:** sí. Sales referencia `product_id` (Catalog: validar activo y obtener nombre/precio actual para el snapshot) y `customer_id` (Customers: validar existencia/activo). Las dependencias recomendadas son `Sales → Catalog` y `Sales → Customers` (`ddd.md:757-770`) por servicios de aplicación o interfaces, no por modelos (`ddd.md:783-807`); ninguno de esos servicios existe hoy. `Reporting` (inexistente) leerá Sales. `Customers` consumirá `GET /api/orders/?customer_id=` (contrato en ADR clientes).
- **Compartido:** `Money` y posiblemente `DateRange` en `backend/shared/domain/` (hoy vacío).
- **Frontend:** nueva `features/sales/` (pages de lista/detalle/creación, componentes de ítems/estado/pago, servicio, modelos), ruta en `app.routes.ts`, menú en `routes.json` e i18n `en/es/de`; selector de producto (consume `/api/products/?active=true`) y selector/creación de cliente (consume `/api/customers/`); conexión de `customer-purchase-history`. Posible extracción de `Page<T>`/estilos a `shared/`.

### Implementaciones similares existentes
- `catalog` y `customers` (backend) y `features/products` y `features/customers` (frontend) son el patrón a seguir: entidad de dominio pura con validación por campo, comandos/queries por clase con `execute`, repositorio con lista perezosa, vistas delgadas, paginación propia, acciones POST de estado, specs por capa. Decisiones ya tomadas para recursos análogos: `docs/adr/ADR-catalogo-productos-mvp-*.md`, `docs/adr/ADR-clientes-mvp-*.md`, `docs/design/DDR-catalogo-productos-mvp-menu-y-pantallas-producto.md`, `docs/design/DDR-clientes-mvp-menu-y-pantallas-cliente.md`.
- **Sin precedente:** agregado con entidades hijas persistidas (ítems, pagos); máquina de estados con transiciones validadas; valores derivados a partir de colecciones (total, saldo, `PaymentStatus`) y su filtrado en SQL; value object `Money`; servicios de aplicación entre módulos; edición de líneas en un formulario (alta de ítems, cambio de cantidad) y un flujo de pago desde el detalle; chips/etiquetas de estado; filtros múltiples en lista (estado, pago, fecha, cliente, canal).

### Comportamiento actual
- No existe ninguna pantalla, endpoint, modelo ni migración de pedidos o pagos. `GET /api/orders/` devolvería 404 (`backend/config/urls.py:6-11`). El menú no tiene entrada de ventas/pedidos (`routes.json`).
- Catálogo y Clientes operan de extremo a extremo (listar, crear, editar, activar/desactivar) y exponen ids UUID estables y filtros `active`/`search` que Sales consumiría. El perfil del cliente muestra la sección de historial vacía sin llamadas a pedidos.

### Restricciones
- `CLAUDE.md`: cambios acotados a un objetivo y **plan + confirmación antes de tocar varios archivos**; **dinero siempre `Decimal`**, nunca `float`; nunca editar una migración ya aplicada; no leer ni modificar `.env`; **avisar antes de instalar dependencias** (relevante si se quisiera `django-filter`); dominio sin imports de Django; módulos no se importan infraestructura entre sí; Reporting solo lee; **estados cambian por métodos del agregado** (`order.deliver()`), no por asignación; serializers validan forma y tipos; no agregar abstracciones DDD sin necesidad real (sección 29); fuera del MVP: microservicios, event sourcing, CQRS completo, inventario/producción avanzados; frontend por `features/<modulo>/`, servicios inyectables, tipos explícitos sin `any`, Reactive Forms, sin suscripciones colgadas; una rama y un PR por task (`task/TASK-<slug>`), rama base `main`; PostgreSQL, sin SQLite salvo tests explícitos.
- Reglas de negocio de los REQ-SAL-001..016 (ver Requerimiento): invariantes del agregado (≥1 ítem para confirmar, cantidad > 0, total calculado, descuento ≤ subtotal, transiciones válidas, cancelado no se entrega, motivo de cancelación, monto de pago > 0, estado de pago derivado, saldo independiente del estado logístico).

### Riesgos identificados
- **Tamaño del alcance:** 16 requisitos que abarcan dominio, persistencia, API, y todo el frontend (lista, alta, detalle, ítems, pagos, estados, menú). Es el contexto "central" (`ddd.md:323`) y mucho mayor que catálogo/clientes juntos; riesgo de un PR inmanejable y de que el plan deba partirse en tasks/fases (dependencia: la partición no se decide en esta etapa).
- **Modelo de estados ambiguo:** "confirmar" sin estado propio, "editable" sin definición, transiciones y cancelación sin tabla (ver Hipótesis). Un error aquí contamina dominio, API y UI; requiere decisiones del usuario/Specification antes de implementar.
- **Estado de pago derivado + filtros/ordenamiento en lista:** filtrar y paginar por `PaymentStatus`/saldo exige agregación en BD o desnormalización; la decisión de dónde vive el estado derivado afecta consistencia (riesgo de divergencia entre columna y pagos) y rendimiento.
- **Integridad monetaria:** `Money`/redondeo a 2 decimales, subtotales de ítem y descuento deben sostener `Decimal` de extremo a extremo (dominio, DB `DecimalField`, serializers que no usen `float`, JSON como string; en frontend, formateo sin pérdida). El catálogo ya fija la precisión (máx. 2 decimales, `12,2`).
- **Cruce de módulos sin servicios:** para validar producto activo y tomar snapshot, y cliente activo, hay que introducir `get_product_for_sale`/`get_customer_for_sale` (diferidos en dos ADR previos). Riesgo de acoplar a infraestructura de otro módulo (`ddd.md:801-807`) o de duplicar reglas de actividad.
- **Reembolso/cancelación con pagos:** semántica indefinida de `REFUNDED` y de pagos de pedidos cancelados puede inflar o deformar métricas de "ventas cobradas" en Reporting.
- **Concurrencia en pagos y edición:** sin transacciones/locks explícitos pueden aceptarse pagos que excedan el saldo o ediciones sobre un pedido que cambió de estado.
- **Cobertura de pruebas del frontend:** specs de plantilla fallando y `app.component.spec.ts` sin compilar en `main` (documentado en tasks previos) obligan a acotar la verificación a specs de la feature nueva.
- **Datos personales:** el pedido referencia al cliente y las notas pueden contener datos personales; no hay política de anonimización definida (`ddd.md:287-288`).
- **Acoplamiento del historial de clientes:** el ADR de clientes fija un contrato (`GET /api/orders/?customer_id=`) que Sales debe respetar; cambiarlo exige enmendar ese ADR.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Se crea el bounded context central `sales`: agregado `Order` con ítems y pagos, máquina de estados, valores derivados y cambio importante de base de datos (varias tablas y migración inicial). Impacta múltiples módulos (consume Catalog y Customers por servicios de aplicación aún inexistentes, es fuente de Reporting y cierra el historial de Customers) y hay decisiones estructurales abiertas (modelo de estados/"confirmar", dónde vive el estado de pago derivado, `Money` en `shared`, contrato con otros módulos).

### Diseño requerido
**SI** — Pantallas nuevas y un flujo con varios pasos: lista operativa con filtros combinados (estado, pago, fecha, cliente, canal), creación/edición del pedido con ítems editables y selectores de cliente/producto, detalle con estados logísticos y de pago visibles por separado, acciones de cambio de estado y cancelación con motivo, registro de pagos, nueva entrada de menú, y reutilización de `ngx-datatable`/`ng-select` de la plantilla; sin decisión de diseño la pantalla quedaría inconsistente con productos/clientes.

## Diseño
- [DDR-ciclo-pedido-entrega-cobro-menu-y-lista-pedidos](../design/DDR-ciclo-pedido-entrega-cobro-menu-y-lista-pedidos.md) — Propuesto. Menú directo "Pedidos" (`/sales/orders`); lista `ngx-datatable` con atajos (Todos / Pendientes de entrega / Por cobrar / Entregados / Cancelados) + filtros finos (entrega, pago, canal, cliente, fecha de pedido o entrega prevista); columnas con **dos badges separados** (Entrega con `fa-truck`, Pago con `fa-coins`), total y saldo; orden fijo por vista; solo acción "Ver".
- [DDR-ciclo-pedido-entrega-cobro-formulario-y-detalle-pedido](../design/DDR-ciclo-pedido-entrega-cobro-formulario-y-detalle-pedido.md) — Propuesto. Formulario solo con datos del pedido (cliente con `ng-select` y creación rápida en modal, canal, fechas, notas); el **detalle es la pantalla de trabajo**: paneles Entrega y Cobro independientes con alertas "entregado con saldo" / "pagado, pendiente de entrega" / "cancelado", ítems editables en tabla Bootstrap, importes solo lectura (los calcula el servidor), pagos con formulario inline, entrega y cancelación (motivo obligatorio) por `Swal`. La UI muestra solo las acciones que el servidor declare disponibles. Conecta el historial del perfil de cliente.
- Pendiente para arquitectura/Specification: significado de "confirmar", estados editables y transiciones, contrato del pedido (importes, acciones disponibles), pagos en pedido cancelado/sobrepago/REFUNDED, fecha real de entrega, servicios hacia Catalog y Customers, código legible del pedido, estado de pago filtrable.

## Arquitectura
**Decisiones de negocio confirmadas por el usuario (2026-10-08):** "confirmar" = NEW → IN_PREPARATION (sin estado nuevo); editable (datos, ítems, descuento) hasta READY; transiciones lineales estrictas con cancelación desde NEW/IN_PREPARATION/READY; sin sobrepago, sin pagos nuevos en cancelados, REFUNDED sin acción de reembolso; un solo task y un PR.

- [ADR-ciclo-pedido-entrega-cobro-modelo-dominio](../adr/ADR-ciclo-pedido-entrega-cobro-modelo-dominio.md) — módulo `sales`; agregado `Order` con `OrderItem` y `Payment` internos; estados por métodos del agregado; `payment_status`, `total`, `paid_total`, `balance` derivados; 11 invariantes (total ≥ pagado, un producto por pedido, etc.); `shared/domain/money.py` mínimo; `OrderValidationError` (400) vs `OrderRuleViolation` (409).
- [ADR-ciclo-pedido-entrega-cobro-contrato-api](../adr/ADR-ciclo-pedido-entrega-cobro-contrato-api.md) — `/api/orders/` con ítems, descuento, prepare/ready/deliver/cancel y pagos; todas las mutaciones devuelven el pedido completo con `editable`, `allowed_transitions`, `can_register_payment`; filtros `status`/`payment_status` multivalor, `date_field`+rango, `has_balance`, `customer_id`; cumple el contrato del historial de clientes.
- [ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia](../adr/ADR-ciclo-pedido-entrega-cobro-persistencia-consistencia.md) — tablas `sales_order`/`sales_order_item`/`sales_payment` (UUID sin FK entre módulos, CheckConstraints); derivados persistidos y escritos solo por el agregado; `select_for_update` dentro de `transaction.atomic()` en la capa API; migración aditiva reversible.
- [ADR-ciclo-pedido-entrega-cobro-integracion-modulos](../adr/ADR-ciclo-pedido-entrega-cobro-integracion-modulos.md) — fachada `modules/<modulo>/services.py` con DTO inmutables (`get_product_for_sale`, `get_customer_for_sale`, `get_customer_names`); puertos en Sales; Customers no importa Sales.
- [ADR-ciclo-pedido-entrega-cobro-frontend-feature](../adr/ADR-ciclo-pedido-entrega-cobro-frontend-feature.md) — `features/sales`; extracción de `Page<T>` y estilos `btn-tbl-*` a `shared/` (commit aparte); sales → products/customers por API pública, customers → HTTP de pedidos con servicio propio (sin ciclos); creación rápida de cliente como última fase separable; importes como string, sin cálculo en el navegador.
- Sin dependencias nuevas (`pip`/`npm`). Rollback: migración nueva solo con tablas nuevas (`migrate sales zero`) y revert del PR; extracción a `shared/` en commit separado.
- **Supuestos míos a confirmar en el plan:** cantidades enteras; un producto no repetible en un pedido; `delivered_date` y `payment_date` no futuras; el cancelado conserva el `payment_status` derivado; el cliente se valida solo al asignarlo; `code` derivado del UUID (sin número secuencial). **Riesgo operativo:** los pagos no se pueden corregir ni anular en este alcance.

## Plan
- [PLAN-2026-10-08-ciclo-pedido-entrega-cobro](../plans/PLAN-2026-10-08-ciclo-pedido-entrega-cobro.md) — **v2** (antes v1), Modo COMPLETO, Specification readiness: READY. 28 ACs (API de pedidos, ítems, descuento, estados, pagos, lista, detalle, menú, formulario, historial del cliente, creación rápida, extracción a `shared/`), 14 invariantes, 11 casos borde, sin dependencias nuevas, E2E: NO (humo manual obligatorio antes de fusionar). Implementación en 9 fases con commits separados; la creación rápida de cliente (Fase 8) es separable.
- Preguntas abiertas no bloqueantes (decisiones por defecto vetables en el PR): cantidades enteras y producto no repetible; fechas de entrega y de pago no futuras; "por cobrar" sin cancelados; pagos no corregibles ni anulables en este alcance (riesgo operativo); límites de longitud (`notes` 2000, `reason` 500, `reference` 100); código visible derivado del UUID.
- **v2 (2026-10-08), tras el review FAIL:** [Specification] REV-03 resuelto con aprobación del usuario: el precio de un ítem puede ser 0 (INV-01, AC-03, nuevo EDGE-13); ADR `modelo-dominio` enmendado. [Implementation Plan] REV-01 (XSS en `Swal` por nombre de producto, y el mismo patrón en `customer-list`/`customer-detail`) y REV-02 (`null.trim()` en las búsquedas remotas, incluida la de productos) entran como Fase 10 con EDGE-14 y EDGE-15.

## Implementación
Rama `task/TASK-ciclo-pedido-entrega-cobro`, PR #7, siguiendo el plan v1 (COMPLETO) en las 9 fases, con commits separados.

**Backend**
- `backend/shared/domain/money.py` (`parse_money`, `InvalidMoney`) — INV-01.
- Fachadas `modules/catalog/services.py` (`get_product_for_sale`) y `modules/customers/services.py` (`get_customer_for_sale`, `get_customer_names`) con DTO congelados — AC-21.
- `backend/modules/sales/`:
  - `domain/` — `Order`/`OrderItem`/`Payment` (dataclasses sin Django; subtotal, total, pagado, saldo y `payment_status` son propiedades derivadas, nunca asignadas), enums, `OrderValidationError` (400) / `OrderRuleViolation` (409) / `OrderNotFound` / `OrderItemNotFound`, `OrderFilters` y `OrderSummary` (modelo de lectura de la lista): INV-01..INV-11, INV-13, INV-14, AC-02..AC-15.
  - `application/` — puertos (`ProductCatalog`, `CustomerDirectory`, `Clock`), 11 comandos y `GetOrder`/`ListOrders`: AC-03, AC-18.
  - `infrastructure/` — modelos `sales_order`/`sales_order_item`/`sales_payment` con `CheckConstraint`/`UniqueConstraint`, `migrations/0001_initial.py` generada con `makemigrations`, mapper, `DjangoOrderRepository` (upsert, ítems sincronizados, pagos solo agregados, `get_for_update`, lista perezosa con filtros), adaptadores y `SystemClock`: AC-08, AC-16, AC-20.
  - `api/` — serializers, `parse_order_filters`, 10 vistas y `urls`; montado como `api/orders/`; `modules.sales` en `INSTALLED_APPS`: AC-01..AC-19.
- `docs/architecture/ddd.md`: rutas reales de Sales y convención de fachadas `services.py`.

**Frontend** (`frontend/panel_admin/src/app/`)
- `shared/models/page.ts` y `shared/styles/_table-actions.scss`; `products` y `customers` migrados (commit aparte, AC-28).
- `features/sales/` — modelos tipados (importes como texto), `OrdersApiService` (400→errores por campo, 409→`OrderRuleError`), `CustomerOptionsService`, `MoneyPipe`, badges de entrega y pago, componentes `order-summary`/`order-items`/`order-payments`, páginas `order-list` (atajos + filtros en la URL), `order-form` y `order-detail` (paneles Entrega/Cobro, alertas, diálogos `Swal` de entrega y cancelación), `sales.routes.ts`, `index.ts`: AC-23..AC-25.
- Menú "Pedidos" (`routes.json`, i18n en/es/de, `sidebar-menu.spec.ts`) y ruta `sales/orders`: AC-22.
- `features/customers/` — `CustomerOrdersApiService` y `customer-purchase-history` con enlaces, columna Pago y estados de carga/error (AC-26); `CustomerQuickCreateComponent` + `CustomerQuickCreateService` (modal) integrado en el selector del pedido (AC-27); `index.ts` en `products` y `customers`.

**Tests escritos:** backend `shared/tests/test_money.py`, `catalog|customers/tests/test_services.py`, `sales/tests/{test_domain,test_application,test_repository,test_api,test_boundaries}.py`; frontend specs de servicio, pipe, badges, `order-summary`, `order-items`, `order-payments`, `order-list` (+ filtros), `order-form`, `order-detail`, `customer-options`, `customer-orders-api`, `customer-purchase-history`, `customer-detail` (actualizado), `customer-quick-create` (+ servicio).

**Verificación propia (no es el Quality Gate):**
- Backend: `python manage.py test` → 334 tests OK en PostgreSQL (primero en un PostgreSQL desechable propio y luego contra el servidor local del usuario, que solo crea y borra su base `test_doredb`); `makemigrations --check` sin cambios.
- Frontend: `ng lint` OK; `ng build` OK; 258 specs OK (features `sales`, `customers`, `products` y `sidebar-menu`), con un `tsconfig` temporal fuera del repositorio porque la suite completa tiene fallas de plantilla preexistentes.
- No se hizo humo manual con backend + `npm start` (queda para `delivery-review`).

**Desviaciones respecto al plan**
- Un producto con **precio 0** no se puede agregar a un pedido (error en `product_id`): lo exige INV-01 tal cual está escrito, aunque el catálogo permite precio 0. Conviene confirmarlo.
- La lista devuelve un modelo de lectura `OrderSummary` (importes persistidos) en lugar de entidades `Order` sin ítems cargados; el contrato HTTP no cambia.
- Se añadió un límite de dominio no listado: el subtotal del pedido no puede superar 9 999 999 999,99 (evita un error 500 por desbordar la columna `DecimalField(12,2)`); falla en `quantity`.
- Los ids se reciben como `str` y la vista los convierte para responder 404 `{detail}` también con ids mal formados (AC-17).
- Servicios y archivos auxiliares no previstos: `CustomerOptionsService` (búsqueda de clientes compartida por lista y formulario), `order-list-filters.ts` (funciones puras de URL↔filtros).
- `ng build` (plantillas estrictas) detectó errores de tipos que `ng test` no mostraba; corregidos.
- Los tests que afirmaban "el perfil no hace peticiones a pedidos" (clientes AC-13) se reemplazaron por los de AC-26, como pide el ADR de historial.

**Deuda técnica / no verificado**
- `customer-quick-create` importa `duplicateMatchesHtml` desde la página `customer-form` de su misma feature; conviene moverlo a una utilidad.
- Las etiquetas de estado del historial del cliente están duplicadas en `customers` (no puede importar Sales).
- Sin prueba multihilo de concurrencia: solo se comprueba que las mutaciones usan transacción y `select_for_update`.
- Humo manual de UI pendiente (selectores `ng-select` remotos y fechas nativas no se pueden ejercitar bien en Karma).

## Review
**Resultado: PASS** — re-review del 2026-10-09 sobre `task/TASK-ciclo-pedido-entrega-cobro` @ `3b55ffc` (PR #7), plan v2. Revisión hecha en la misma sesión que la revisión anterior: el aislamiento de contexto es procedimental, no real (se releyó el diff y se re-ejecutó todo).

**Historial de revisiones**
- 2026-10-08: FAIL → [REV-01](../reviews/REV-2026-10-08-ciclo-pedido-entrega-cobro-01.md) (High, XSS en `Swal`), [REV-02](../reviews/REV-2026-10-08-ciclo-pedido-entrega-cobro-02.md) (Medium, typeahead con `null`), [REV-03](../reviews/REV-2026-10-08-ciclo-pedido-entrega-cobro-03.md) (Low, precio 0). Los tres **cerrados** con evidencia en cada archivo.
- 2026-10-09: PASS, sin issues abiertos.

**Verificaciones ejecutadas (detalle en el PR)**
- Backend `python manage.py test`: 339 tests OK (PostgreSQL 16 desechable); `makemigrations --check`: sin cambios; `bandit` en `modules/sales` y `shared` (sin tests): sin hallazgos.
- Frontend `ng lint` OK; `ng build` OK; Karma acotado (features, `sidebar-menu`, shared): 272/272 OK; cobertura 97,8 % sentencias, 92,8 % ramas.
- Límites DDD OK (sin Django en `domain/`/`application/`; Catalog y Customers no importan Sales).
- Humo manual completo en backend y `ng serve` propios: crear pedido, ítems, preparar, listo, pago parcial, entrega con saldo, lista "Por cobrar", historial del cliente, cancelación con motivo (vacío rechazado; válido conserva pagos), creación rápida de cliente con aviso de duplicado, ítem de precio 0, XSS y typeahead.
- No ejecutado: `npm audit` (sin lockfile), ruff/flake8/mypy/coverage.py (no configurados en backend; cobertura backend revisada solo por la suite), E2E (el plan lo descarta).
- Preexistentes, no de este PR: `app.component.spec.ts` no compila en `main`; `sidebar.component.spec.ts` falla con "No icon provided" también con el menú de `main`.

## Publicación
_Pendiente_

### Iteración 2 (plan v2, tras el review FAIL)
- **REV-01 / EDGE-15:** `titleText` en los diálogos `Swal` con datos de usuario (`order-detail`, `customer-list`, `customer-detail`); specs que llaman al método real. Mismo patrón sin corregir en `product-list` y `product-detail` (fuera del alcance del plan, anotado como deuda).
- **REV-02 / EDGE-14:** búsquedas de cliente y de producto toleran `null`/`undefined` y errores síncronos; specs que emiten `null` por el typeahead (formulario, lista, ítems, servicio).
- **REV-03 / EDGE-13 (Specification v2):** el precio de un ítem puede ser 0; tests de dominio, aplicación y API.
- **Hallazgo propio del humo:** el detalle no recargaba al cambiar solo el id de la ruta (mostraba el pedido anterior y actuaba sobre él); ahora reacciona a `paramMap`, con specs. `order-form` en modo edición y `customer-detail` conservan la lectura única del id (deuda).
- Verificación propia: backend 339 tests OK (PostgreSQL local, base de pruebas aparte); frontend 272 specs OK, `ng lint` y `ng build` OK. Humo manual en el navegador con backend/`ng serve` propios y base desechable: selector de cliente tras elegir, creación rápida con duplicado, pedido con producto de precio 0, preparar, pago (sobrepago rechazado, pago parcial), cancelación con motivo obligatorio y XSS en el diálogo de quitar ítem: OK.
