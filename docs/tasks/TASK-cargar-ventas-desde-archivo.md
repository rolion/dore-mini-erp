# TASK-cargar-ventas-desde-archivo: Cargar ventas desde un archivo CSV/Excel con mapeo e inferencia

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-cargar-ventas-desde-archivo
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/110

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-19 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-19 | INVESTIGATION → DESIGN | Veredicto NEEDS_ARCHITECTURE, diseño requerido | delivery-start |
| 2026-11-19 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-11-19 | ARCHITECTURE → PLANNING | 2 ADR escritos | delivery-start |
| 2026-11-19 | PLANNING → ENGINEERING | Plan v1 COMPLETO, Specification READY | delivery-start |
| 2026-11-19 | ENGINEERING → REVIEW | Implementación completa; pruebas con BD pendientes | delivery-build |

## Investigación

### Requerimiento
Texto recibido: «proceso de cargado de datos mediante archivo csv o excel, el usuario sube un archivo de ventas y se carga al registro las ventas y los movimientos contables. Adicionalmente, se deberá crear el producto si no existe, se deben crear los movimientos de compra a proveedores y se realizan los movimientos contables para cada módulo. El usuario sube el archivo de ventas, se realiza un mapeo de los datos; arriba del mapeo hay checkboxes para elegir si se infieren los productos, clientes, inventario y movimientos contables».

Aclaraciones del usuario (respuestas a la consulta de negocio, 2026-11-19):
1. **Compras inferidas:** el archivo puede traer columnas opcionales de proveedor y costo unitario; con «inferir inventario» se crea una compra recibida **solo por el faltante de stock** de cada producto, al costo del archivo; sin proveedor se usa uno genérico «Importación».
2. **Fechas sin cobertura contable (antes del corte):** cargar la venta igual, sin asiento, y avisar en el reporte final.
3. **Errores:** primero vista previa con resumen; al confirmar, cada venta se carga en su propia transacción (todo o nada por venta) y se informa cuáles fallaron. Reintentar el mismo archivo no duplica.
4. **Cobros:** toda venta importada se registra **cobrada al total el día de la venta**. Si el archivo no trae método de pago, al confirmar el mapeo se agrega la columna «método de pago» y la persona elige un método por defecto; el predeterminado es **Caja** (efectivo).

### Hechos encontrados
- No existe ninguna carga masiva ni parser de archivos: `grep` de `csv|openpyxl|xlsx` solo da usos no relacionados; `backend/requirements/base.txt` tiene Django, DRF, psycopg y django-environ (**sin `openpyxl`**). El frontend no sube archivos (solo plantillas Oreva de ejemplo).
- Ciclo de venta existente: `backend/modules/sales/application/commands.py:50` `CreateOrder`, `:102` `AddOrderItem` (usa el **precio vigente del catálogo**, `:128`), `:176` `StartOrderPreparation` (NEW→IN_PREPARATION), `:188` `MarkOrderReady`, `:198` `DeliverOrder` (salida de stock + `recognize_delivery` + `cost_delivery`), `:267` `RegisterPayment`.
- Dominio de pedido: `Order.add_item(product_id, name, unit_price, quantity)` acepta precio (`sales/domain/order.py:276`); `deliver` exige `order_date ≤ entrega ≤ hoy` (`:335-343`); el pago no puede ser futuro y no excede el saldo (`:360-390`); la cantidad es **entera** (`validate_quantity -> int`, `:93`); canales: WHATSAPP, FACEBOOK, INSTAGRAM, STORE, FAIR, OTHER; métodos: CASH, QR, BANK_TRANSFER, CARD, OTHER (`sales/domain/enums.py`).
- Puertos y adaptadores de Ventas: `sales/application/ports.py` (`ProductCatalog`, `CustomerDirectory`, `StockOutput`, `SalesPosting`, `DeliveryCosting`) y `sales/infrastructure/adapters.py`. Contabilidad: `SalesPostingAdapter.recognize_delivery` (`:256`) reconoce al entregar solo si `coverage_status(...).covered`; sin cobertura y sin anticipos no asienta (`:262-267`). `record_payment` (`:230`) con pedido entregado y **sin** cobertura escribe en el libro anterior y puede rechazar con `payment_method_without_account` (`:289-306`). `DeliveryCostingAdapter.cost_delivery` (`:322`) **rechaza la entrega** con cobertura contable si no hay costo promedio (compra recibida o valoración inicial adoptada).
- Entrega con stock: `DeliverOrder._register_outputs` (`commands.py:223`) exige almacén elegido si hay productos controlados y almacén activo; la política de stock negativo vive en Inventario (`inventory/application/movement_use_cases.py:77`).
- Compras: `purchases/application/purchase_commands.py` (`CreatePurchase` :50, `ConfirmPurchase` :113), `receipt_commands.py` `RegisterReception` (`:56`: recepción, entradas de stock con costo unitario, `recognize_receipt` Debe Inventario / Haber Cuentas por pagar con cobertura); recepción no puede ser futura (`purchases/domain/purchase.py:403`); pagos separados (`payment_commands.py`). Proveedores: `purchases/application/commands.py:12` `CreateSupplier`; fachada `purchases/services.py` solo tiene lectura (`get_supplier_for_purchase`, `list_active_suppliers`).
- Catálogo: `catalog/application/commands.py:58` `CreateProduct` (nombre, precio, categoría, `can_buy`, `can_sell`, `tracks_stock`, `base_unit_id`); un producto que controla stock exige unidad base (`StockControl`, `:19-56`). **Productos y clientes no tienen código/SKU**: solo `name` (`catalog/domain/product.py`, `customers/application/commands.py:21`); clientes con teléfono duplicado exigen confirmación (`DuplicateCustomerPhone`, `:30-36`).
- Fachadas entre módulos: solo lectura salvo casos puntuales; regla de `docs/architecture/ddd.md:793-823` y test `modules/sales/tests/test_boundaries.py`: módulos se hablan **solo por `services.py`** con DTO; mapa de dependencias explícito.
- Aislamiento y permisos: permiso por defecto `CompanyAdminPermission`/`CompanyModulePermission` (`config/settings/base.py:97`, `accounts/api/permissions.py:11`); las vistas declaran `required_modules` (ej. `purchases/api/views.py:48`); catálogo de módulos y dependencias en `modularity/domain/modules.py:15-37`.
- Precedente de operación con previsualización obligatoria y 409 «en curso»: `features/accounting/pages/regularization` (`docs/design/design-system.md:198`); asistente por pasos con resumen: `inventory/stock-opening`, `inventory/valuation` (`DDR-iniciar-valoracion-inventario-costeo-asistente-valoracion`).

### Hipótesis / supuestos no confirmados
- Las compras inferidas **quedan por pagar** (Cuentas por pagar); el archivo de ventas no informa pagos a proveedores. Se declara en el plan como supuesto no bloqueante.
- Los productos nuevos controlan stock (unidad base por defecto) solo si Inventario está habilitado y se marcó «inferir inventario»; el nombre de la unidad por defecto se resuelve en build (ver riesgos).
- Descuentos por venta quedan fuera de este alcance (el archivo informa precio unitario).
- Los eventos de costo y de inventario respetan la fecha histórica de la venta/compra; hay que verificarlo en build (riesgo R-02).
- Límites razonables: 5 MB y 2 000 filas de datos por archivo; ejecución síncrona.

### Módulos y dependencias relacionadas
`sales` (pedidos, entrega, cobro), `catalog` (productos, unidades), `customers`, `purchases` (proveedores, compras, recepciones), `inventory` (saldos, entradas y salidas, almacenes), `costing` (costo promedio), `accounting` (cobertura, asientos automáticos, libro anterior), `modularity`/`module_gate` (módulos habilitados). Frontend: `features/sales`, menú `assets/data/routes.json`, i18n `assets/i18n/{es,en,pt}.json`.

### Implementaciones similares existentes
Regularización de pagos históricos (previsualizar → aplicar, idempotente, 409 en curso): `accounting/application/regularize.py`; existencias iniciales (resumen antes de confirmar, clave de idempotencia); `inventory` registro idempotente por `source_id`.

### Comportamiento actual
Una venta se registra a mano, pedido por pedido: se crea, se agregan productos al precio del catálogo, se confirma/prepara/marca lista/entrega (con almacén) y se cobra. Las compras a proveedor se crean y reciben a mano. No hay forma de cargar un histórico de ventas ni de crear productos, clientes o compras desde un archivo.

### Restricciones
`CLAUDE.md`: `Decimal` para dinero, aislamiento por `company_id` desde el usuario, módulos solo por `services.py`, sin texto hardcodeado (i18n en tres idiomas), avisar antes de instalar dependencias (`openpyxl` para `.xlsx`), nunca editar migraciones aplicadas, dominio sin imports de Django.

### Riesgos identificados
- **R-01 Cobertura/costo:** con cobertura contable, entregar sin costo promedio se rechaza; la importación debe garantizar costo (compra inferida con costo) o reportar el error accionable.
- **R-02 Fechas históricas:** movimientos de inventario y eventos de costo pueden fijar `occurred_at = ahora`, desordenando el promedio ponderado respecto de la fecha de la venta.
- **R-03 Irreversibilidad:** un pedido entregado y cobrado no se cancela; no hay deshacer masivo (fuera de alcance). Mitigación: vista previa obligatoria, confirmación explícita, rastro de qué se creó por fila.
- **R-04 Duplicados:** reintentos y archivos repetidos; hace falta clave de idempotencia por venta.
- **R-05 Volumen/tiempo:** ejecución síncrona dentro de una petición; límite de filas y tiempo de proxy.
- **R-06 Seguridad de archivos:** `.xlsx` es un zip (bombas de descompresión, fórmulas); CSV con inyección de fórmulas al reexportar.
- **R-07 Coincidencia por nombre:** sin códigos, la coincidencia de productos/clientes por nombre normalizado puede unir o separar registros equivocadamente.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo bounded context de orquestación que cruza seis módulos (ventas, catálogo, clientes, compras, inventario, contabilidad/costeo), con tablas nuevas, contrato API nuevo, dependencia nueva (`openpyxl`) y decisiones de consistencia (transacción por venta, idempotencia, fechas históricas, cobertura contable).

### Diseño requerido
**SI** — flujo de varios pasos nuevo (subir, mapear con casillas de inferencia, vista previa, resultado) y pantalla de historial.

## Diseño
Ver `docs/design/DDR-cargar-ventas-desde-archivo-asistente-de-importacion.md` (Propuesto).

## Arquitectura
- `docs/adr/ADR-cargar-ventas-desde-archivo-modulo-e-integracion-por-fachadas.md`
- `docs/adr/ADR-cargar-ventas-desde-archivo-ejecucion-por-venta-e-idempotencia.md`

## Plan
`docs/plans/PLAN-2026-11-19-cargar-ventas-desde-archivo.md` (v1, COMPLETO). Specification readiness: **READY** (los cuatro puntos abiertos de negocio quedaron resueltos por el usuario; los supuestos restantes están declarados como no bloqueantes).

## Implementación

**Backend** (`backend/modules/data_import/`, dominio sin Django): parsers CSV/XLSX con límites (AC-01), mapeo sugerido y validado (AC-02/03), opciones y casillas validadas contra módulos habilitados (AC-04/05), validación por celda y agrupación en ventas con clave de idempotencia (AC-18, INV-05), vista previa sin escritura (AC-06), ejecución por venta en transacción propia con idempotencia, bloqueo de una ejecución por empresa (restricción única parcial) y exigencia de vista previa vigente (AC-07..AC-15, INV-04/09), historial y filas (AC-17), API-01..05 bajo `/api/imports/sales/` con admin + `sales`,`catalog` (AC-16). Migración `data_import/0001_initial` (3 tablas).
Fachadas aditivas: `catalog` (`list_products_for_import`, `create_product_for_import`), `customers`, `purchases` (`import_received_purchase`: crear+confirmar+recibir, sin pago), `sales` (`import_delivered_sale`: precio del archivo, entrega, cobro total), `costing.get_average_costs`; `shared/import_errors.py`; `SalesPostingAdapter.posts_on` y `DeliveryCostingAdapter(post_accounting)`. Test de fronteras actualizado (AC-20). `openpyxl==3.1.5` agregado (autorizado por el usuario).
**Frontend** (`features/data-import/`, hecho por un subagente): asistente de 4 pasos con las cuatro casillas sobre el mapeo, historial y detalle, i18n es/en/pt, ruta `sales/import`, menú `adminOnly`; referencias: `accounting/regularization`, `inventory/stock-opening`; reutiliza `app-status-badge`, `app-posting-issues-alert`, `Page<T>`, `NgbModal`. Se corrigió `sidebar` para respetar `adminOnly` en submenús.

**Desviaciones respecto al plan**
- Los movimientos de inventario y los eventos de costo registran el **momento de la carga**, no la fecha de la venta (las fachadas de Inventario no aceptan `occurred_at` en entradas/salidas de documentos); la fecha de negocio vive en pedido, cobro, recepción y asientos. R-02 queda como deuda técnica.
- Sin integración HTTP de pruebas: **no hay `DATABASE_URL` en este worktree** (no se copia `.env`), así que no se escribieron ni corrieron pruebas de integración con BD (AC-06 «no escribe», AC-07, AC-10..AC-17 contra BD real, 409 concurrente, aislamiento). Cubierto solo con pruebas de dominio/parsers y de casos de uso con fakes (31 pruebas OK) más el test de fronteras (8 OK).
- Frontend: sin `node_modules`, no se ejecutaron `lint`, `npm test` ni `build`; solo `tools/check-i18n-keys.mjs` (0 faltantes). Sin tarjetas móviles (se usa `table-responsive`), sin filtro «solo con error» en la vista previa, retomar `?run=` solo para importaciones terminadas.

**Deuda técnica:** reversa en bloque, ejecución asíncrona, pruebas de integración y Karma pendientes.


## Review
_Pendiente_

## Publicación
_Pendiente_
