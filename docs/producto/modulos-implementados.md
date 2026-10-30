# PocketBiz (dore-mini-erp): módulos implementados

Documento para Product Management. Describe qué hace hoy el sistema, módulo por módulo, en lenguaje de negocio. Los detalles técnicos están en `docs/architecture/ddd.md`, `docs/adr/` y `docs/tasks/`.

**Estado al 2026-10-27:** los 8 tasks del MVP y el de branding/perfil están publicados y fusionados en `main` (PR #2 a #12).

## 1. Qué es el producto

Mini ERP para pequeños negocios que venden por pedido (WhatsApp, redes, feria, venta directa). Cubre el ciclo completo: **catálogo → clientes → pedido → entrega → cobro → gastos → reportes**.

- Cada persona se registra y crea su **empresa**. Solo ve los datos de su empresa.
- Interfaz web (panel Angular, marca PocketBiz) sobre una API Django/PostgreSQL.

## 2. Resumen de módulos

| Módulo | Qué resuelve | Menú / ruta | Estado |
|---|---|---|---|
| Acceso y empresas | Registro, login, logout, aislamiento por empresa | `/authentication/signin`, `/signup` | Listo |
| Catálogo | Productos y precios | `catalog/products` | Listo |
| Clientes | Agenda de clientes e historial de compras | `customers` | Listo |
| Ventas | Pedidos, entrega y cobros (pagos parciales) | `sales/orders` | Listo |
| Gastos | Registro de gastos y categorías | `expenses` | Listo |
| Reportes | Dashboard y reportes de ventas/gastos | `dashboard`, `reports` | Listo |
| Módulos por empresa | El admin elige qué módulos usa su empresa, con dependencias | `settings/modules` | Listo (PB-MOD-001) |
| Configuración por módulo | Ajustes de cada módulo por empresa con historial de cambios | `sales/settings`, `purchases/settings`, `inventory/settings`, `settings/modules` | Listo (PB-CFG-001) |
| Consulta de existencias | Existencias por producto y almacén con búsqueda, filtros (almacén, activo/inactivo, saldo cero / distinto de cero / negativo) y detalle con historial; sin disponible, reservado ni valoración | `inventory/stock`, `inventory/stock/:productId/:warehouseId` | Listo (PB-INV-005) |
| Política de stock negativo | Ajuste de la empresa «Permitir stock negativo» (bloqueado por defecto) que rige toda salida del libro; el rechazo informa producto, almacén, solicitado y existente. Ventas la consume al entregar (PB-INT-002) | `inventory/settings` | Listo (PB-INV-007) |
| Salida de inventario al entregar | Al pasar un pedido de Listo a Entregado se descuentan, en un solo almacén y de forma atómica e idempotente, los productos que controlan stock; diálogo con almacén, existencia y saldo proyectado, política de stock negativo aplicada por Inventario, salida visible en el pedido y en Movimientos («Salida por venta», filtro por pedido). Sin Inventario habilitado la entrega no cambia | `sales/orders/:id`, `inventory/movements` | Listo (PB-INT-002) |
| Existencias iniciales | Apertura de stock por almacén (movimiento + saldo), consulta de existencias y movimientos | `inventory/stock`, `inventory/stock/opening` | Listo (PB-INV-003) |
| Marca y perfil | Logos PocketBiz, avatar con iniciales, menú de usuario | Transversal | Listo |

## 3. Detalle por módulo

### 3.1 Acceso y empresas
- **Registro público**: formulario de sign-up con nombre de empresa obligatorio. Crea la empresa y deja a la persona como **administrador**.
- **Regla de negocio**: un nombre de empresa ya existente se rechaza. Los usuarios adicionales los agrega el admin (hoy desde Django admin; no hay pantalla propia).
- **Login/logout** con usuario y contraseña. Credenciales inválidas muestran error y no dejan pasar.
- **Aislamiento**: cada dato de negocio pertenece a una empresa y solo es visible para sus usuarios. La empresa sale de la sesión, nunca de lo que envía el navegador.
- **Rol**: hoy solo existe `admin`, con acceso total a los datos de su empresa.
- El registro público se puede apagar con una variable de configuración (`REGISTRATION_ENABLED`).
- Un usuario creado por consola (`createsuperuser`) no tiene empresa: entra a Django admin, pero la API de negocio le responde 403 hasta que se le asigne una.

### 3.2 Catálogo (productos)
- Crear, editar, consultar y listar productos (nombre obligatorio, precio ≥ 0, descripción opcional).
- Activar / desactivar: un producto inactivo no se puede agregar a pedidos nuevos, pero sigue visible en ventas y reportes históricos.
- Lista con filtro activo/inactivo y búsqueda por nombre.
- **Usos del producto (PB-CAT-001)**: cada producto tiene categoría operativa (materia prima, empaque, intermedio, terminado, mercadería) y dos usos independientes, «se puede comprar» y «se puede vender». El precio de venta solo es obligatorio si se vende; el precio de compra se captura en cada compra. Ventas solo acepta productos activos y vendibles (también en la API); la fachada de Catálogo informa los comprables para Compras. La categoría organiza y filtra, no restringe usos. Los productos existentes quedan vendibles, no comprables y «por revisar» (sin categoría) hasta que se clasifiquen; sus pedidos históricos conservan snapshots. La lista filtra por uso, categoría y estado.
- Editar un producto **no altera pedidos anteriores**: estos guardan una copia (snapshot) del nombre y precio.

### 3.3 Clientes
- Crear y editar clientes (nombre obligatorio; teléfono, correo y notas opcionales). También se pueden crear **al vuelo desde un pedido**.
- Búsqueda rápida por nombre y teléfono.
- **Detección de duplicados**: avisa si el teléfono ya existe (se normaliza con código de país, por defecto Bolivia +591) y pide confirmación.
- **Historial de compras** en el perfil (fecha, total, estado de cada pedido).
- Desactivar en lugar de borrar; los pedidos históricos se conservan. La lista muestra solo activos por defecto.

### 3.4 Ventas (pedidos)
Es el núcleo del sistema.

- **Crear pedido**: cliente opcional, ítems de productos activos, canal de venta, fecha de pedido, fecha de entrega prevista, notas.
- **Canales**: WhatsApp, Facebook, Instagram, venta directa, feria, otro.
- **Ítems**: agregar, cambiar cantidad (> 0) y quitar mientras el pedido sea editable. Un pedido necesita al menos un ítem para confirmarse. Se permite precio 0 en ítems (decisión confirmada).
- **Importes**: subtotal y total se calculan solos. Hay descuento explícito que no puede superar el subtotal. Nadie edita el total a mano.
- **Estado de entrega** (logístico): `Nuevo → En preparación → Listo → Entregado`, o `Cancelado`. No se permiten saltos inválidos; un cancelado no se entrega. Cancelar exige motivo.
- **Pagos**: uno o varios por pedido, con monto > 0, método (efectivo, QR, transferencia, tarjeta, otro) y fecha.
- **Estado de pago**: `Pendiente / Parcial / Pagado` (existe `Reembolsado` en el modelo), calculado a partir de los pagos. Se muestra el saldo pendiente.
- **Entrega y pago son independientes**: se puede estar "entregado y por cobrar" o "pagado y por entregar".
- **Lista** con filtros por estado, estado de pago, fecha, cliente y canal. **Detalle** con ítems, importes, estados y pagos.

### 3.5 Gastos
- **Categorías**: crear, editar, activar/desactivar. Una categoría inactiva no se ofrece para gastos nuevos; los gastos históricos la conservan.
- **Gastos**: descripción, monto > 0, categoría, fecha, método de pago (mismos que en ventas), proveedor y notas opcionales. Se pueden editar.
- **Anulación**: lógica, irreversible y sin motivo. Un gasto anulado no suma en reportes. No hay borrado físico.
- Lista filtrable por rango de fechas y categoría.

### 3.6 Reportes y dashboard
Solo lectura: consulta Ventas y Gastos, no modifica nada. El periodo es seleccionable (día, semana, mes o rango).

| Reporte | Contenido |
|---|---|
| Dashboard | Ventas, gastos, **ganancia estimada**, cantidad de pedidos, pendientes de entrega y de cobro |
| Ventas | Total y cantidad de pedidos, ticket promedio |
| Gastos | Total y desglose por categoría (la suma cuadra con el total) |
| Ventas por canal | Agrupado por canal de venta |
| Productos más vendidos | Por unidades e importe |
| Clientes con mayor compra | Por total comprado y número de pedidos |
| Pendientes | Listas de pedidos por entregar y por cobrar |

**Definiciones que el PM debe conocer** (decididas con el usuario el 2026-10-09):
- *Ventas/ingresos* = suma del total de pedidos **no cancelados**, por **fecha de pedido** (base devengada, no caja). Un pedido entregado pero impago cuenta como venta.
- *Ganancia estimada* = ventas − gastos registrados. No incluye costo de producción; la etiqueta lo deja claro.
- Los pagos de pedidos cancelados se ignoran en el MVP.

### 3.7 Marca y perfil (transversal)
- Marca **PocketBiz**: logos en login y menú lateral (logo reducido al contraer), favicon, título de pestaña, color principal, fuente Inter.
- Avatar con **iniciales** (no se guardan fotos), nombre y apellido del usuario y nombre de la empresa en el menú lateral.
- Menú superior simplificado: se quitó búsqueda, mensajes y notificaciones. El menú de usuario muestra nombre, empresa y cerrar sesión.

## 4. Fuera de alcance / limitaciones conocidas

- Sin inventario ni stock, producción ni costeo de productos.
- Sin gestión de usuarios ni roles adicionales desde la interfaz (solo `admin`; alta de usuarios por Django admin).
- Sin reembolsos: el estado "Reembolsado" existe pero no hay flujo que lo use.
- Sin notificaciones ni mensajería (los iconos se quitaron del header).
- Sin exportación de reportes ni facturación fiscal.
- Cancelar un pedido conserva sus pagos pero no genera devolución.
- Las pantallas de plantilla sobrantes (calendario, tablas avanzadas, etc.) siguen en el código pero no forman parte del producto.
- La suite de specs del frontend tuvo 71 fallos preexistentes de la plantilla al publicar el registro (task del 2026-10-12); conviene confirmar su estado actual.

## 5. Dependencias entre módulos

```
Acceso/Empresa ──► (todos los datos llevan empresa)
Catálogo ─┐
Clientes ─┼──► Ventas ──► Reportes ◄── Gastos
```

Ventas lee Catálogo y Clientes para validar producto/cliente activo; Reportes lee Ventas y Gastos; ningún módulo toca la base de datos de otro.

## 6. Referencias

| Módulo | Task (en `docs/tasks/`) | PR |
|---|---|---|
| Backend base | `TASK-inicializar-backend-django` | #2 |
| Login | `TASK-frontend-login-backend` | #4 |
| Catálogo | `TASK-catalogo-productos-mvp` | #5 |
| Clientes | `TASK-clientes-mvp` | #6 |
| Ventas | `TASK-ciclo-pedido-entrega-cobro` | #7 |
| Gastos y Reportes | `TASK-gastos-reporting-mvp` | #8 |
| Marca | `TASK-pocketbiz-branding-logos` | #9 |
| Registro y empresas | `TASK-registro-usuarios-empresa-multitenant` | #10 |
| Perfil y menús | `TASK-perfil-usuario-menus-lateral-superior` | #12 |

### 3.7 Módulos por empresa (PB-MOD-001)
- **Configuración › Módulos** (`/settings/modules`, solo admin): lista los módulos con estado, dependencias obligatorias e integraciones opcionales. Habilitar/Deshabilitar abre un diálogo que resume módulo, empresa y módulos afectados.
- **Base**: Acceso/Empresa y Catálogo, siempre activos y sin interruptor.
- **Dependencias**: Ventas→Catálogo; Reportes→Ventas y Gastos; Compras→Catálogo y Gastos; Inventario→Catálogo. Clientes y Gastos no dependen de otros. Si faltan, se muestran sus nombres y la acción queda bloqueada; tampoco se puede deshabilitar un módulo que otro habilitado requiere.
- Cada empresa conserva su selección. Por defecto: Clientes, Ventas, Gastos y Reportes habilitados; Compras e Inventario apagados. Inventario aún no tiene pantallas propias: al habilitarlo su menú abre «Próximamente». Compras ya tiene Proveedores y Compras en borrador.
- **Pendiente (PB-MOD-002)**: la API de negocio no bloquea módulos deshabilitados.
- **Pendiente (PB-MOD-004)**: la desactivación segura (validar datos existentes) aún no existe.

### 3.8 Configuración por módulo y empresa (PB-CFG-001)
- Cada módulo tiene **Configuración** con pestañas «General» e «Historial de cambios»; solo la ve y guarda el administrador de la empresa y no afecta a otras empresas. Guardar es todo o nada; un valor inválido no se guarda y el error aparece junto al campo. Salir con cambios sin guardar pide confirmación.
- **Ventas** — ajustes y valor inicial:
  - *Canal de venta predeterminado*: ninguno. Precarga el canal al crear un pedido (se puede cambiar).
  - *Método de pago predeterminado*: ninguno. Precarga el método al registrar un pago (se puede cambiar).
  - *Descuento máximo (% del subtotal)*: 100 %. La API rechaza un descuento nuevo que lo supere; los pedidos existentes no cambian.
- **Compras e Inventario**: aún no tienen ajustes (la pantalla lo indica); su historial queda listo.
- **Historial**: fecha y hora, usuario, ajuste, valor anterior y nuevo, con filtro por fecha y ajuste. «Configuración › Módulos» también registra cada habilitación o deshabilitación. No guarda secretos.
- Ajustes futuros (P2 y contables P3) se agregarán con sus historias.

### 3.9 Compras › Proveedores (PB-COM-001)
- **Compras › Proveedores** (`/purchases/suppliers`, solo con el módulo Compras habilitado): lista con nombre, identificación, teléfono, correo y estado; búsqueda por nombre o identificación y filtro Activos (por defecto) / Inactivos / Todos.
- Crear y editar: nombre obligatorio; identificación, teléfono, correo y notas opcionales. El correo se valida si se informa y los errores aparecen junto a cada campo. No se avisa de identificaciones repetidas.
- Activar/desactivar con confirmación; nunca se borra. Desactivar no toca compras históricas.
- «Ver compras» abre `/purchases?supplierId=<id>`, la lista de Compras filtrada a ese proveedor.

### 3.10 Compras › Compras en borrador (PB-COM-002)
- **Compras › Compras** (`/purchases`, solo con Compras habilitado): lista con fecha, proveedor, referencia, total y estado, paginada; con `?supplierId=` muestra solo las de ese proveedor (chip «Proveedor: X» con «Quitar filtro»).
- **Nueva compra / Editar compra** (`/purchases/new`, `/purchases/:id/edit`): formulario único con proveedor activo (obligatorio, búsqueda por nombre), fecha de compra (obligatoria, hoy por defecto), referencia externa y notas opcionales, y líneas: producto activo y habilitado para compra (PB-CAT-001; búsqueda por nombre, sin repetir), unidad base («—» si no tiene), cantidad (> 0, hasta 3 decimales; entera si la unidad no admite fracciones), precio unitario (≥ 0, 2 decimales) y subtotal calculado. El total es de solo lectura, en BOB. Cantidad o precio inválidos se marcan junto a su línea y las entradas se conservan ante cualquier error.
- Sin proveedores activos aparece «Crear proveedor» (y «+ Nuevo proveedor» en el selector): se crea en un diálogo y queda seleccionado sin perder lo escrito.
- Guardar crea o actualiza el **borrador**: no mueve stock ni crea gastos. No existen impuestos, descuentos ni costos adicionales. Un producto aparece una vez por compra; un borrador puede guardarse sin líneas (Confirmar, en otra historia, exigirá al menos una).
- El nombre y la unidad del producto se copian al agregarlo y se conservan al editar el borrador aunque el catálogo cambie; un proveedor desactivado después debe reemplazarse para guardar.
- **Detalle** (`/purchases/:id`): pestaña «Resumen» con referencia interna, proveedor, fechas, estado documental, de recepción y de pago, productos, total y notas. Un borrador ofrece Editar, Confirmar y Cancelar compra.


