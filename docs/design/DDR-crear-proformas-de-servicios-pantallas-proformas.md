# DDR-crear-proformas-de-servicios-pantallas-proformas: Pantallas de Cotizaciones → Proformas

**Estado:** Propuesto
**Task relacionado:** TASK-crear-proformas-de-servicios
**Fecha:** 2026-11-03

## Contexto
El operador necesita listar, elaborar y consultar proformas de servicios. Es un módulo nuevo con menú propio «Cotizaciones».

## Pantallas/flujos afectados
- `/pocketbiz/quotations/proformas` — **Lista con filtros** (referencia `purchase-list`, seguimiento de estados): columnas Número/versión, Cliente, Fecha, Total propuesto, Estado; filtros cliente (búsqueda), rango de fechas y estado en la URL; «+ Nueva proforma».
- `/pocketbiz/quotations/proformas/nueva` y `/:id/editar` — **Formulario**: cliente (selector con búsqueda, activo), fecha, vigencia opcional, moneda BOB (solo lectura), condiciones/notas comerciales con aviso «No incluyas diagnósticos». **Tabla editable de líneas** (patrón de líneas de pedido/compra): selector de servicio que muestra nombre y precio, descripción congelada (solo lectura), cantidad, precio unitario (editable solo si `can_edit_price`), subtotal calculado y botón quitar; total con dos decimales como vista previa (el servidor recalcula). Indicador «Cambios sin guardar», errores por línea, «Guardar borrador» y «Presentar» (diálogo de confirmación con resumen y total).
- `/pocketbiz/quotations/proformas/:id` — **Detalle**: `dl` con número, versión, cliente, fechas, vigencia, estado (badge con texto), total propuesto («Total aceptado: —»), tabla de líneas con referencias de tratamiento/pieza si existen, condiciones; sección «Versiones» (tabla con versión, fecha, estado, total, enlace). Acciones según `allowed_actions`: Editar (borrador), Presentar, Nueva versión (presentada).

## Componentes/patrones elegidos
`design-system.md` §5: Lista con filtros, Formulario, Detalle con acciones; diálogo de acción irreversible para «Presentar». Badges: `col-orange` borrador, `col-blue` presentada, `col-grey` reemplazada. Sin componentes compartidos nuevos; la tabla de líneas se implementa en el feature como componente propio (`proforma-lines`). Menú: Cotizaciones → Proformas.

## Alternativas consideradas
- Editar líneas en un diálogo por línea: más clics y peor teclado; descartado.
- Autoguardado: oculta el estado «sin guardar» que pide la tarjeta; descartado.

## Comportamiento por privilegio/estado
Cargando, vacío (mensaje y «Limpiar filtros»), error con «Reintentar» y éxito visibles. Ante error de guardado se conservan los datos del formulario y se marcan los campos/líneas con error. Doble envío bloqueado («Guardando…»). Operable con teclado; confirmación antes de presentar. El campo de precio se deshabilita si el servidor indica `can_edit_price: false`, pero **el backend aplica módulos, empresa, permiso de precio y recálculo**; el frontend no es la barrera.

## Consecuencias
Sin vínculo a tratamiento/pieza en la UI hasta que exista ese módulo. Estados de aceptación ausentes en esta historia.
