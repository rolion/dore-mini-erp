# DDR-inventario-existencias-filtros-accesos-operativos-filtros-detalle-y-retorno: Filtros por clasificación/uso, acciones del detalle y retorno

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-existencias-filtros-accesos-operativos
**Fecha:** 2026-10-29

## Contexto
PB-INV-009 amplía Existencias (`/inventory/stock`) con clasificación y usos (datos de Catálogo, PB-CAT-001 ya en `main`), filtros nuevos y accesos a apertura/ajuste desde el detalle. No hay pantallas nuevas: se amplían `stock-list` y `stock-detail` y se ajusta el retorno de `stock-opening` y `adjustment-form`. Parte de `docs/design/DDR-inventario-consultar-existencias-historial-existencias-y-detalle.md`.

## Pantallas/flujos afectados
1. **Lista de Existencias** (`stock-list`): columnas nuevas «Clasificación» y «Usos»; tres filtros nuevos; los filtros se conservan al volver del detalle.
2. **Detalle de existencia** (`stock-detail`): filas «Clasificación» y «Usos»; botones «Registrar apertura» y «Registrar ajuste»; nota cuando la apertura no procede.
3. **Apertura** (`stock-opening`) y **Ajuste** (`adjustment-form`): reciben producto y almacén preseleccionados y, si vienen del detalle, vuelven a él (al guardar y al cancelar).

## Componentes/patrones elegidos
- Plantilla «Lista de solo lectura con filtros» y «Detalle con historial embebido» (`design-system.md` §5); se reutilizan `badge-outline`, `form-select form-control`, `ngb-pagination`, `_inventory-table.scss`. No se crea nada en `shared/`.
- **Clasificación:** texto de `categoryLabel` (`features/products/models/product.ts`); sin categoría → «Sin clasificar» con `badge-outline col-grey`.
- **Usos:** dos badges `badge-outline`: «Comprable» (`col-blue`) y «Vendible» (`col-green`); ninguno → «Sin usos» en gris. Siempre con texto, no solo color.
- **Filtros:** `Clasificación` (Todas · las 5 categorías · «Sin clasificar»), `Comprable` y `Vendible` (Todos · Sí · No), en la misma fila `row g-2` del formulario de filtros; en móvil se apilan (`col-md-*` con ancho completo por defecto). «Limpiar» pasa a llamarse «Limpiar filtros».
- **Detalle:** `dl` existente con filas nuevas; botón primario «Ver movimientos», `btn-outline-primary` «Registrar apertura» y «Registrar ajuste», `btn-light` «Volver».
- **Conservar filtros:** servicio inyectable `StockFiltersState` (en memoria, `providedIn: 'root'`) guarda filtros y página al salir de la lista; la lista los restaura al iniciar. «Volver» del detalle lleva a `/inventory/stock` sin parámetros. `?warehouse_id=` explícito (venido de la apertura) sobrescribe el almacén guardado.
- **Retorno:** parámetro de ruta `return=stock` (valor cerrado, no una URL libre) más `product_id` y `warehouse_id`; el formulario construye el destino `/pocketbiz/inventory/stock/<product_id>/<warehouse_id>` solo si ambos son UUID válidos. Evita redirecciones abiertas.

## Alternativas consideradas
- *Conservar filtros en query params de la URL*: sobrevive a recargas, pero obliga a propagar los parámetros por el detalle y los formularios; descartado por esfuerzo. El estado en memoria cubre el criterio «al volver del detalle».
- *`returnUrl` libre*: más general, pero riesgo de redirección abierta; descartado.
- *Selectores de Comprable/Vendible como casillas*: no distinguen «Todos» de «No»; la historia pide tres opciones.

## Comportamiento por privilegio/estado
- «Registrar apertura»: solo si `can_register_opening` (producto y almacén activos, sin movimientos). Si no, se oculta y la nota explica que la apertura solo procede sin movimientos (o por inactividad).
- «Registrar ajuste»: solo si `can_register_adjustment` (almacén activo). Si no, se oculta y la nota indica «Almacén inactivo».
- Inventario deshabilitado: ya lo cubre `moduleGuard` de la ruta y el gate del backend.
- **El frontend no es la barrera:** el backend revalida permisos (`CompanyAdminPermission`), módulo, almacén activo e historial al confirmar (`RegisterOpening` → 409 `stock_history_exists`; ajuste con sus validaciones). Un error del servicio se muestra en el formulario conservando los datos.
- Estados: cargando, vacío inicial («Aún no hay productos con control de stock…» sin filtros), sin resultados con filtros (mensaje + «Limpiar filtros»), error con «Reintentar».

## Consecuencias
Las existencias muestran datos de Catálogo sin duplicarlos. El estado de filtros vive solo mientras dure la sesión de la SPA (se pierde al recargar): deuda aceptada. Sin patrones nuevos de `design-system.md` salvo una línea en «Lista de solo lectura con filtros» sobre «filtros conservados».
