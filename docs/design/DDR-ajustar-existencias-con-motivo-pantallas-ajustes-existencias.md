# DDR-ajustar-existencias-con-motivo-pantallas-ajustes-existencias: Lista, formulario y detalle de ajustes de existencias

**Estado:** Propuesto
**Task relacionado:** TASK-ajustar-existencias-con-motivo
**Fecha:** 2026-10-28

## Contexto
La historia pide Inventario → Ajustes con listado, formulario «Nuevo ajuste» y detalle confirmado de solo lectura. El submenú de Inventario ya tiene «Ajustes» (`/inventory/settings`, configuración del módulo). Para no confundirlos, la entrada nueva se llama **«Ajustes de existencias»** (`/inventory/adjustments`) y la existente conserva su nombre.

## Pantallas/flujos afectados
1. **Ajustes de existencias** (`/pocketbiz/inventory/adjustments`): lista.
2. **Nuevo ajuste** (`/pocketbiz/inventory/adjustments/new`): formulario en dos pasos en la misma ruta (Editar → Revisar y confirmar), igual que la apertura.
3. **Detalle de ajuste** (`/pocketbiz/inventory/adjustments/:id`): solo lectura.
4. Submenú Inventario: entrada «Ajustes de existencias». Entrada contextual: botón «Ajustar» en cada fila de Existencias (abre «Nuevo ajuste» con producto y almacén preseleccionados).

## Componentes/patrones elegidos
- **Lista — plantilla Lista** (`movement-list`, tabla apilada de `_inventory-table.scss`). Filtros: Desde/Hasta (`input type=date`), Producto (selector), Almacén (`form-select`); paginación de servidor. Columnas: Referencia (enlace al detalle), Fecha, Producto, Almacén, Sistema, Contado, Diferencia (con signo, `text-success` si es entrada y `text-danger` si es salida, más unidad), Usuario, Estado (badge «Confirmado»/«Revertido»). Botón primario «Nuevo ajuste» en la cabecera. Vacío: «Aún no hay ajustes de existencias.»; sin resultados de filtro: «Sin ajustes para esos filtros.».
- **Formulario — plantilla Formulario** (`stock-opening`, paso Editar):
  - Almacén (`form-select`, solo activos, predeterminado preseleccionado) y Producto (selector con búsqueda, solo productos activos que controlan stock; `appendTo="body"`), ambos obligatorios.
  - Al elegir ambos se consulta el saldo y se muestra «Saldo actual» de solo lectura con la unidad (campo `readonly`), más la unidad base.
  - Cantidad contada (numérica ≥ 0; sin decimales si la unidad no los admite, hasta 3 si los admite) y Motivo (texto obligatorio, máx. 200 caracteres).
  - Cálculo en vivo bajo los campos: «Diferencia: +5 unidades · Entrada de ajuste» / «−3 · Salida de ajuste». Si la diferencia es 0: `alert alert-info` «Sin diferencia: no se registrará ningún movimiento» y «Revisar y confirmar» queda deshabilitado.
  - Pie: «Revisar y confirmar» (primario) y «Cancelar» (`btn-light`, vuelve a la lista sin crear nada; con cambios aplica `unsavedChangesGuard`).
- **Revisar y confirmar (segundo paso):** `card` con `dl.row`: Producto, Almacén, Saldo del sistema, Cantidad contada, Diferencia y sentido, Motivo. Botones «Confirmar ajuste» (primario; deshabilitado con «Registrando…» durante el envío; la clave de idempotencia se genera al abrir el formulario y se reutiliza en cada reintento) y «Volver a editar» (`btn-light`). Aviso: «Un ajuste confirmado no se puede editar; solo podrá revertirse.»
- **Saldo cambiado (409 `balance_changed`):** vuelve al paso de resumen con `alert alert-warning` «El saldo cambió de X a Y desde tu conteo. Revisa la diferencia (ahora ±Z) y confirma de nuevo.»; el resumen se recalcula con el saldo nuevo y «Confirmar ajuste» queda como acción explícita (no se reenvía solo). Si con el saldo nuevo la diferencia es 0, se muestra «Sin diferencia» y no se puede confirmar.
- **Éxito:** navega al detalle con `ToastrService` «Ajuste registrado»; una réplica (200) muestra lo mismo sin error.
- **Detalle — plantilla Detalle** (`movement-detail`): `dl.row` con Referencia, Estado, Fecha, Producto, Almacén, Saldo del sistema al confirmar, Cantidad contada, Diferencia y sentido, Unidad, Motivo, Usuario, y enlace «Ver movimiento» al detalle del movimiento de ajuste. Sin acciones de editar/eliminar. «Revertir» **no se muestra** hasta PB-INV-008 (el estado «Revertido» sí, derivado del movimiento).
- Estados de toda pantalla: cargando, vacío, error de servidor (alerta; el borrador se conserva), error de validación (`small.text-danger` por campo).
- Patrón nuevo: ninguno; se reutiliza «Formulario con revisión y confirmación de envío único» ya documentado en `design-system.md` (se añade la variante «reconfirmación por cambio de saldo»).

## Alternativas consideradas
- **Renombrar la entrada de configuración a «Configuración»:** toca una pantalla ajena a la historia; descartado (se anota como deuda de nombres).
- **Modal para el ajuste:** inadecuado en móvil y sin espacio para la revisión; descartado.
- **Ajuste de varios productos por conteo:** fuera de la historia (un producto y almacén por ajuste).
- **Reenviar automáticamente con el saldo nuevo:** contradice «exigir revisar y reconfirmar».

## Comportamiento por privilegio/estado
- Con el módulo Inventario deshabilitado, las rutas redirigen por `moduleGuard` y el submenú no aparece.
- El frontend **no es la barrera**: el backend aplica módulo habilitado, rol administrador, empresa del usuario, producto que controla stock, almacén activo, motivo obligatorio, cantidad válida, comparación del saldo esperado y la idempotencia.

## Consecuencias
- Deuda aceptada: dos entradas parecidas en el menú («Ajustes» y «Ajustes de existencias») hasta unificar nombres; sin ajuste masivo ni adjuntos de conteo; sin «Revertir» hasta PB-INV-008.
