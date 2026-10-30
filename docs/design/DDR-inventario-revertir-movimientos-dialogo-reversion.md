# DDR-inventario-revertir-movimientos-dialogo-reversion: Acciones y diálogos de reversión

**Estado:** Propuesto
**Task relacionado:** TASK-inventario-revertir-movimientos
**Fecha:** 2026-10-30

## Contexto
La tarjeta PB-INV-008 pide «Revertir» en el detalle de movimiento y de ajuste, y «Revertir recepción» en el detalle de recepción. Es una acción destructiva de efecto contable (genera un contramovimiento) y no se puede deshacer, por lo que debe mostrar el efecto previsto antes de confirmar, exigir motivo y explicar cuándo no está disponible.

## Pantallas/flujos afectados
1. **Detalle de movimiento** (`inventory/pages/movement-detail`).
2. **Detalle de ajuste** (`inventory/pages/adjustment-detail`): revierte el movimiento vinculado (`movement.id`).
3. **Detalle de recepción** (`purchases/pages/reception-detail`) y su efecto en la pestaña «Recepciones» y el resumen de la compra (badge «Revertida» ya existe).

## Componentes/patrones elegidos
Base: plantilla **Detalle** (sección 5) con acciones bajo los datos y el patrón de **diálogo `NgbModal` con motivo obligatorio** de `purchase-cancel-dialog` (`backdrop: 'static'`, botón `btn-danger` deshabilitado hasta que el motivo recortado no esté vacío, `maxlength` visible, «Volver» `btn-light`). Sin componente compartido nuevo en `shared/`; dos diálogos propios, cada uno en su feature:

- **`MovementReverseDialogComponent`** (`inventory/components/movement-reverse-dialog`), usado por movimiento y ajuste. `dl` de solo lectura con: referencia y tipo del movimiento original (`movementTypeLabel`), producto, almacén, cantidad con unidad, y **efecto inverso previsto** («Se registrará una salida de 5 u en Almacén central; el saldo pasará a …» cuando se conoce; si no, «Se registrará una salida de 5 u»). Campo «Motivo» (`textarea`, obligatorio, máx. 200). Botón «Revertir movimiento» (`btn-danger`) → «Revirtiendo…» mientras envía. Errores del servidor: 400 bajo el campo; 409 `insufficient_stock` con `app-insufficient-stock-alert` (existente) mostrando producto y saldo, sin cerrar el diálogo; otros 409 con `alert alert-warning` y mensaje del servidor.
- **`ReceiptRevertDialogComponent`** (`purchases/components/receipt-revert-dialog`). Resume la recepción (referencia, fecha), una **tabla de todas sus líneas** (producto, cantidad, unidad, si genera salida de stock: «Se registrará una salida» / «Sin control de stock · sin movimiento»), y un `alert alert-info` fijo: «Revertir la recepción restituye las cantidades pendientes de la compra y descuenta el stock recibido. **No devuelve los pagos registrados.** No hay reversión parcial.» Para recepciones documentales: «Recepción documental: no hay movimientos de inventario que corregir.». Mismo campo de motivo y botón «Revertir recepción». 409 `insufficient_stock`: `alert alert-warning` en el diálogo con **todas** las líneas faltantes (producto, solicitado, saldo) y «No se revirtió ninguna línea.». 409 `inventory_unavailable`: mensaje del servidor.

**Botón y reglas de visibilidad**
- Detalle de movimiento/ajuste: `btn btn-warning` «Revertir» (acción de estado, no la principal de la pantalla) solo si `reversal.allowed`. Si el movimiento está `confirmed` pero no es revertible por su origen, se oculta el botón y se muestra `small.text-muted` con `reversal.message` (venta: «Las salidas por venta requieren una devolución, que aún no está disponible.»; compra: «Este movimiento proviene de una recepción: corrígelo desde la recepción en Compras.»). Si ya está revertido o es un contramovimiento: sin botón y sin mensaje de bloqueo (el estado y los enlaces lo explican); nunca se ofrece una segunda reversión.
- Detalle de recepción: `btn btn-warning` «Revertir recepción» solo si `can_revert`; revertida: sin botón.

**Resultado (detalle posterior)**
- Movimiento original: badge «Revertido» (`badge-outline col-grey`, ya existe) y bloque «Reversión» con `dl`: contramovimiento (enlace a su detalle, con su referencia), usuario, fecha `dd/MM/yyyy HH:mm` y motivo. El contramovimiento muestra «Revierte a» el original (ya existe) y su propio motivo.
- Recepción: badge «Revertida» (`col-orange`, ya existe) y bloque «Reversión» con fecha, usuario y motivo; la tabla de movimientos de la recepción añade columna «Estado» (Confirmado/Revertido con texto) y enlace al contramovimiento. El resumen de la compra recarga los estados «Recepción»/«Pendiente».
- Éxito: tras cerrar el diálogo se recarga el detalle y se muestra `alert alert-success` («Movimiento revertido» / «Recepción revertida») con el patrón de confirmación visible.

## Alternativas consideradas
- **Página dedicada «Revertir» con paso de resumen** (plantilla de formulario con líneas): más consistente con la apertura de existencias, pero la acción es de un solo documento y sin edición de líneas; un diálogo reproduce el patrón de «Cancelar compra» con menos pantallas. Descartado.
- **Botón primario `btn-primary`:** la reversión no es la acción principal del detalle y es destructiva; se usa `btn-warning` (acción de estado) y `btn-danger` solo en el diálogo.
- **Componente de diálogo compartido en `shared/`:** los dos diálogos difieren en contenido (líneas vs. un movimiento) y viven en features distintos; compartir exigiría un componente genérico sin segundo uso real. Se evalúa mover el campo «Motivo» a `shared/` solo si un tercer diálogo lo necesita.

## Comportamiento por privilegio/estado
- Estados: cargando («Revirtiendo…»), error de validación (motivo vacío/largo, `small.text-danger`), error de servidor (409/5xx visibles dentro del diálogo, sin perder el motivo escrito), éxito (alert y recarga), vacío no aplica.
- **El frontend no es la barrera:** solo oculta el botón. El backend debe aplicar: rol admin de la empresa (403 si no), módulos requeridos, aislamiento por empresa (404), motivo obligatorio, orígenes permitidos (`requires_return`, `reverse_from_origin`), unicidad de la reversión, política de stock y todo-o-nada de la recepción.
- Si el módulo Inventario está deshabilitado, el detalle de recepción en modo `inventory` no ofrece «Revertir recepción» (`can_revert` falso) y explica el motivo con `small.text-muted`.

## Consecuencias
- Un solo patrón de diálogo con motivo en dos features (copia estructural del de cancelar compra): deuda menor aceptada; se propone documentarlo en `docs/design/design-system.md` como «Diálogo de acción irreversible con motivo» (se incluye en este PR como actualización de la sección 5).
- Desde un movimiento originado en una recepción no hay enlace directo a la recepción (falta el id de compra); solo texto. Queda como mejora futura.
