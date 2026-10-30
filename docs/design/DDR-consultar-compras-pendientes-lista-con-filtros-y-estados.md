# DDR-consultar-compras-pendientes-lista-con-filtros-y-estados: Lista de compras con seguimiento y filtros

**Estado:** Propuesto
**Task relacionado:** TASK-consultar-compras-pendientes
**Fecha:** 2026-10-30

## Contexto
La lista de compras (`features/purchases/pages/purchase-list`) solo muestra fecha, proveedor, referencia externa, total y estado documental. PB-COM-006 pide seguimiento de recepción, pago y saldo, y filtros. El detalle ya tiene las pestañas Resumen/Recepciones/Pagos.

## Pantallas/flujos afectados
- **Lista de compras** (modificada): columnas, barra de filtros, búsqueda, estado vacío.
- **Detalle de compra** (ajuste menor): en «Resumen» se añaden las filas **Total pagado** y **Saldo** (hoy solo están en la pestaña Pagos), para ver totales y los tres estados juntos. Sin otros cambios.

## Componentes/patrones elegidos
Plantilla «Lista de solo lectura con filtros» (`design-system.md` sección 5; referencias `inventory/pages/movement-list` y `sales/pages/order-list`), conservando el botón «+» Nueva compra que la lista ya tiene.
- Cabecera: título, buscador `search-field` (con `label` y `aria-label`, placeholder «Referencia interna o externa»), botón «+» Nueva compra.
- Formulario de filtros en fila (Reactive Forms, `label` + control, apilado en móvil): Proveedor (`ng-select`, como el filtro de cliente en Ventas), Desde / Hasta (`input type=date`), Estado (`form-select`: Todos, Borrador, Confirmada, Cancelada), Recepción (Todas, Sin recibir, Recibida parcialmente, Recibida), Pago (Todos, **Pago pendiente**, Sin pagar, Pago parcial, Pagada) y «Limpiar filtros» (`btn-light`, deshabilitado sin filtros).
- Columnas: **Referencia** (interna `COM-…`, enlace en negrita al detalle; la externa en texto pequeño debajo), Fecha, Proveedor, Total, **Recepción** (badge), **Estado** (badge documental existente), **Pago** (badge), **Saldo** (derecha, `MoneyPipe`), Acciones (ver; editar solo en borrador).
- Badges (`badge-outline col-<color>`, siempre con texto): documental como hoy (naranja/verde/rojo); recepción: Sin recibir `col-orange`, Recibida parcialmente `col-cyan`, Recibida `col-green`; pago: Sin pagar `col-orange`, Pago parcial `col-cyan`, Pagada `col-green`. Borrador y cancelada: «—» en recepción, pago y saldo.
- «Recibido/pendiente»: una sola columna con el estado de recepción; el detalle por línea se consulta en el detalle (no se suman unidades distintas).
- Los filtros se reflejan en la URL (query params) y se restauran al volver del detalle.

## Alternativas consideradas
1. Filtros en un panel desplegable: descartada, sin precedente; la fila de filtros ya es el patrón.
2. Atajos tipo «Por cobrar» como en Ventas: descartados; la tarjeta pide combinar filtros finos y «Pago pendiente» ya cubre el caso.
3. Mostrar cantidades recibidas/pendientes en la lista: descartada por la tarjeta (unidades distintas).

## Comportamiento por privilegio/estado
- Cargando: `loadingIndicator` de la tabla. Error de servidor: `alert alert-danger` con «Reintentar». Error 400 de filtros: mensaje visible junto a los filtros.
- **Vacío sin filtros:** «Aún no hay compras. Crea la primera con «Nueva compra».» **Vacío con filtros:** bloque con los filtros aplicados como badges (p. ej. «Proveedor: X», «Recepción: Recibida», «Pago: Pago pendiente»), botón «Limpiar filtros» y acceso «Nueva compra». Nunca una tabla en blanco.
- Rango Desde > Hasta: se marca en el formulario y no se consulta.
- El frontend no es la barrera: el backend filtra por empresa, valida los parámetros (400) y exige el módulo Compras habilitado (`required_modules`).

## Consecuencias
Los badges de pago/recepción de Compras son locales (no reutilizan `app-payment-status-badge` de Ventas para no acoplar módulos); si se necesitan en un tercer lugar se mueven a `shared/`. El patrón «vacío con filtros aplicados» se documenta en `design-system.md` (sección 5) en este mismo PR.
