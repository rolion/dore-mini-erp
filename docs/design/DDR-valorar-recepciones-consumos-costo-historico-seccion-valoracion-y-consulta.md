# DDR-valorar-recepciones-consumos-costo-historico-seccion-valoracion-y-consulta: Sección «Valoración» en recepción y movimiento, consulta de movimientos valorados y valor en el ajuste positivo

**Estado:** Propuesto
**Task relacionado:** TASK-valorar-recepciones-consumos-costo-historico
**Fecha:** 2026-10-30

## Contexto
La persona administradora debe ver qué costo se aplicó a cada recepción y consumo, de dónde salió y cómo cambió el promedio; y, con inventario valorado, ingresar un valor al ajustar existencias hacia arriba. Todo es de solo lectura salvo el campo de valor del ajuste. Las pantallas existen; se amplían con componentes ya usados.

## Pantallas/flujos afectados
1. **Detalle de recepción** (`features/purchases`): sección «Valoración».
2. **Detalle de movimiento** (`features/inventory/pages/movement-detail`): sección «Valoración».
3. **Consulta «Movimientos valorados»** (nueva, `inventory/valuation/movements`): lista con filtros producto, origen y fecha.
4. **Formulario de ajuste** (`adjustment-form`): campo «Valor total del ajuste (BOB)» y casilla «Costo cero».
5. **Asistente/consulta de valoración** (`valuation`, existente): enlace «Ver movimientos valorados» tras adoptar.

## Componentes/patrones elegidos
- Sección condicionada por módulo (`design-system.md` §5, «Sección condicionada por módulo», ref. `product-form`): la sección «Valoración» aparece solo con `costing` habilitado y solo si hay adopción; el componente reutilizable `movement-valuation` (tarjeta con tabla de solo lectura) se usa en recepción y movimiento.
- Lista de solo lectura con filtros (§5, ref. `movement-list`) para la consulta; badges de estado de §3: `Valorado` (éxito) y `Cubierto por la adopción` (neutro).
- Formulario (§5, ref. `adjustment-form`): el campo de valor aparece solo si hay inventario valorado y la diferencia es positiva; aviso `alert alert-info` con la regla («El ajuste positivo necesita un valor; el ajuste negativo usa el costo vigente»).
- Contenido de la sección: tabla por línea con producto, cantidad, costo unitario (6 decimales), valor del movimiento (2), promedio anterior → nuevo, origen del costo («Precio de compra», «Valor del ajuste», «Promedio al salir», «Costo del movimiento original») y un enlace a la fuente (recepción/compra/ajuste/pedido). No hay controles de edición del costo (la tarjeta lo prohíbe). Importes con el formato BOB del sistema; texto en español.
- Desvíos del sistema de diseño: ninguno.

## Alternativas consideradas
- **Pestaña «Valoración» en el detalle:** la recepción tiene pocas líneas; una sección basta y evita otra pestaña. Descartada.
- **Columna de costo en la lista de movimientos:** ensancha una lista ya densa; la consulta aparte cubre «por producto, origen y fecha». Descartada.
- **Ingresar costo unitario en el ajuste:** el usuario eligió valor total (coherente con la adopción).

## Comportamiento por privilegio/estado
- Sin `costing` habilitado: no se muestran las secciones ni la consulta (el ajuste igualmente pide valor si hay adopción, por decisión del usuario: se muestra el campo sin depender del módulo; el estado «valorado» llega del API de ajuste).
- Sin adopción: no hay sección; el formulario de ajuste no pide valor.
- Estados: cargando (spinner de §4), vacío («Este movimiento no tiene valoración: es anterior a la adopción» / «Sin movimientos valorados»), error con reintentar, éxito.
- Bloqueos 409/400 de valoración (retroactividad, reversión, valor requerido) se muestran en `alert alert-warning` con el mensaje del backend y el siguiente paso.
- **El backend es la barrera:** permisos por módulo en la API de consulta, validación de valor y bloqueos en el servidor; el frontend solo oculta.

## Consecuencias
Una sección nueva repetida en dos pantallas (componente compartido). Los reportes de valor y la edición/corrección quedan fuera. La deuda visual conocida de listas anchas no cambia.
