# DDR-cargar-ventas-desde-archivo-asistente-de-importacion: Asistente «Importar ventas» e historial

**Estado:** Propuesto
**Task relacionado:** TASK-cargar-ventas-desde-archivo
**Fecha:** 2026-11-19

## Contexto
La persona administradora carga un histórico de ventas desde CSV/Excel. La operación crea datos de varios módulos y no se deshace, por lo que sigue la variante «de operación con previsualización obligatoria» (`docs/design/design-system.md:198`) y el asistente por pasos de `inventory/valuation`.

## Pantallas/flujos afectados
Menú **Ventas → «Importar ventas»** (visible con el módulo `sales`; `adminOnly`):
- `/pocketbiz/sales/import` — asistente de 4 pasos en la misma ruta (indicador de pasos con `aria-current`):
  1. **Subir archivo:** zona de selección (`input type=file`, acepta `.csv,.xlsx`, límite 5 MB / 2 000 filas visible), enlace «Descargar plantilla CSV». Errores del servidor en `alert-danger` bajo la zona.
  2. **Mapear:** arriba, `card` «¿Qué quieres que se cree automáticamente?» con **cuatro casillas** (`form-check`): *Inferir productos* (crea los que no existan), *Inferir clientes*, *Inferir inventario* (crea proveedores, compras recibidas por el faltante de stock y sus entradas) e *Inferir movimientos contables* (asientos de cada módulo). Cada una con explicación en `small.text-muted`; si el módulo necesario no está habilitado (Clientes; Inventario + Compras; Contabilidad) la casilla va deshabilitada con el motivo en texto. Por defecto marcadas las disponibles. Debajo, tabla de mapeo: una fila por campo de destino (Fecha de venta*, Producto*, Cantidad*, Precio unitario*, N.º de venta, Cliente, Método de pago, Canal, Proveedor, Costo unitario, Notas) con `select` de columnas del archivo (sugerido automáticamente) y 3 valores de muestra; los obligatorios llevan `*` y «Revisar» se deshabilita con un campo obligatorio sin mapear. **Valores por defecto** (aparecen cuando la columna no está mapeada): *Método de pago* (por defecto **Caja**/efectivo), *Canal* (Otro) y *Almacén de salida* (solo con Inventario habilitado; el único activo o el predeterminado). Aviso fijo: «Cada venta se registra entregada y cobrada al total en su fecha».
  3. **Vista previa:** `alert-info` «No se ha escrito nada» con titular (ventas y líneas leídas, cuántas se cargarían, cuántas ya fueron importadas, cuántas tienen error), lista de alcance (`small.text-muted`: productos nuevos/existentes, clientes nuevos/existentes, compras a crear y unidades a comprar, ventas sin cobertura contable) y tabla de **filas con problema** (`table-warning`, fila, venta, campo, mensaje; paginada de 10 con `ngb-pagination`, filtro «Solo con error»). «Cargar ventas» (`btn btn-warning`) abre diálogo estático de acción irreversible («No se puede deshacer en bloque…»); se deshabilita si no hay nada que cargar o si cambió el mapeo/opciones desde la previsualización (`alert-warning`: «Vuelve a previsualizar»). «Volver a editar» (`btn-light`).
  4. **Resultado:** `alert-success` (o `alert-warning` si hubo fallos) con contadores (cargadas, ya importadas, sin asiento por fecha, con error), y tabla por venta con `app-status-badge` (Cargada verde, Ya importada gris, Cargada sin asiento amarillo, Con error rojo — siempre con texto), mensaje accionable y enlace al pedido. «Corregir y subir de nuevo» y «Ver historial».
- `/pocketbiz/sales/import/history` — lista de solo lectura (fecha, archivo, usuario, estado, cargadas/errores) con paginación; `/history/:id` detalle con el mismo resultado del paso 4 (filtro por estado). Vacío: «Aún no se ha importado ningún archivo.»

## Componentes/patrones elegidos
- Plantillas de `design-system.md`: «Formulario con líneas y paso de resumen», «Variante de operación con previsualización obligatoria», «Lista de solo lectura con filtros», tabla Bootstrap apilada en móvil, `app-status-badge`, `ngb-pagination`, `NgbModal` estático para la confirmación, `app-posting-issues-alert` para el 409 de configuración contable faltante y `MoneyPipe` para importes.
- Sin componentes nuevos compartidos. El indicador de pasos usa `nav`/`ol` Bootstrap con texto (no solo color).
- Texto visible solo con `translate` (claves nuevas `DATA_IMPORT.*` en `es/en/pt`).

## Alternativas consideradas
- **Cuatro pantallas con rutas separadas:** mejor para «atrás» del navegador, pero se pierde el estado del archivo/mapeo; se prefiere la misma ruta con estado en un servicio (el servidor guarda el archivo, el id va en la URL `?run=<id>` para retomar).
- **Un solo paso (subir y cargar):** descartada: la carga es irreversible y el usuario pidió mapeo y casillas antes.
- **Tabla de vista previa con todas las filas:** descartada por volumen; se muestran contadores y solo filas con problema.

## Comportamiento por privilegio/estado
- Estados: cargando (subida, previsualización, carga con botón «Cargando ventas…» y bloqueo de doble envío con clave de idempotencia), vacío (historial), error de validación (por archivo/campo), error de servidor en `alert-danger` con «Reintentar», 409 `import_running` en `alert-warning`, éxito (paso 4).
- Móvil (< `lg`): tablas pasan a tarjetas; selects de mapeo a ancho completo; botones ≥ 44 px.
- Foco: al cambiar de paso, al encabezado del paso; al terminar, al resumen.
- **El backend aplica todo**: rol admin, empresa del usuario, módulos requeridos (`sales`, `catalog`; 403 `module_disabled`), límites del archivo y todas las reglas de negocio; el frontend solo oculta/deshabilita.

## Consecuencias
Pantalla nueva con patrones existentes; no se modifica `design-system.md` salvo añadir una línea en §6 (menú: «Ventas → Importar ventas»). Sin deuda visual nueva conocida; el asistente no tiene «cancelar importación en curso» (la carga es síncrona).
