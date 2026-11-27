# DDR-crm-listado-clientes-menu-y-lista-crm: Menú CRM → Clientes y lista de clientes CRM

**Estado:** Propuesto
**Task relacionado:** TASK-crm-listado-clientes
**Fecha:** 2026-11-24

## Contexto
La persona que vende necesita encontrar clientes y priorizar contactos con un vistazo a última compra, pedidos y saldo. Hoy «Cliente» es un ítem directo del menú (`frontend/panel_admin/src/assets/data/routes.json:52-62`) con su lista de mantenimiento (`features/customers/pages/customer-list`); el CRM es una vista comercial distinta, no un reemplazo.

## Pantallas/flujos afectados
- Menú lateral: nuevo submenú **CRM** con el ítem **Clientes** (`/pocketbiz/crm/customers`), visible con el módulo `customers` habilitado.
- Pantalla **CRM → Clientes** (nueva, `features/crm/pages/crm-customer-list`): buscar, filtrar por sucursal, ver columnas y abrir la ficha.
- Abrir ficha: el nombre enlaza a `/pocketbiz/customers/:id` (ficha existente; PB-CRM-002 la reemplazará por la 360°).

## Componentes/patrones elegidos
- Plantilla **Lista de solo lectura con filtros** + **Variante compacta de lista** de `docs/design/design-system.md` §5 (referencias: `inventory/pages/movement-list`, `purchases/pages/purchase-list`): breadcrumb, `.card`, buscador con `label`/`aria-label`, `form-select` de sucursal («Todas las sucursales»), `ngx-datatable` con paginación del servidor; bajo `lg` (992 px) filtros en panel «Filtros» y tarjetas con `dl` y botones de 44 px. Sin botón «+» ni acciones de edición (el alta vive en Clientes).
- Columnas: **Nombre** (enlace en negrita), **Teléfono** («—» si falta), **Última compra** (fecha; «Sin compras» si no hay), **Pedidos** (número, alineado a la derecha), **Saldo** (`money` con la moneda, alineado a la derecha, resaltado si > 0).
- Etiqueta visible «Sucursal» (el dato es el almacén de Inventario); opciones = almacenes activos.
- Sin filtro de segmento ni columna de segmento (queda para PB-CRM-007); la lista debe verse completa sin segmentos configurados.
- Sin desviaciones del sistema de diseño; no hay patrón nuevo.

## Alternativas consideradas
- Reutilizar la lista de Clientes con columnas extra: mezcla mantenimiento y CRM, y obligaría a Clientes a conocer Ventas. Descartada.
- Ítem directo «CRM» sin submenú: no deja lugar a Ficha/Segmentos/Acciones de las historias siguientes. Descartada.

## Comportamiento por privilegio/estado
- **Cargando:** indicador de carga de la tabla/tarjetas. **Vacío sin filtros:** «Aún no hay clientes» con enlace a Clientes → alta. **Vacío con filtros:** badges de filtros activos y «Limpiar filtros». **Error:** `alert alert-danger` con «Reintentar».
- Sin módulo Ventas: se ocultan Última compra, Pedidos y Saldo (la API lo informa en `meta`). Sin Inventario: se oculta el filtro de sucursal.
- Filtros y página viven en la URL.
- El frontend no es la barrera: el servidor filtra por empresa del token, exige el módulo `customers` y valida que el almacén pertenezca a la empresa.

## Consecuencias
Todo el texto va por claves i18n (es/en/pt). Hasta PB-CRM-002 la ficha abierta es la existente. Deuda aceptada: dos listas de clientes con fines distintos.
