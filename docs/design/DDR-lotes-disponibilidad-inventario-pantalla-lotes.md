# DDR-lotes-disponibilidad-inventario-pantalla-lotes: Consulta de lotes y sección de lotes en la existencia

**Estado:** Propuesto
**Task relacionado:** TASK-lotes-disponibilidad-inventario
**Fecha:** 2026-11-26

## Contexto
Inventario debe mostrar por lote: producto, almacén, lote, cantidad física, cantidad disponible para empaque y estado. La tarjeta no pide crear ni liberar desde pantalla (eso llega con Producción). Es una consulta de solo lectura.

## Pantallas/flujos afectados
1. **Inventario › Lotes** (nueva, `/inventory/lots`): lista de solo lectura con filtros.
2. **Detalle de existencia** (`stock-detail`): nueva sección «Lotes» cuando el producto tiene lotes en ese almacén.
3. **Detalle de movimiento** (`movement-detail`): fila «Lote» con el código cuando el movimiento lo tiene.
4. **Menú Inventario**: entrada «Lotes» tras «Existencias».

## Componentes/patrones elegidos
- Lista de Lotes: plantilla **«Lista de solo lectura con filtros»** (`features/inventory/pages/movement-list`, `design-system.md` §5) con su variante compacta < 992 px (`stock-list`). Columnas: Lote (código, enlace al detalle de existencia), Producto, Almacén, Estado, Físico, Disponible para empaque, Fecha. Filtros: búsqueda por código, almacén, estado, «solo con stock». Paginación y estados cargando/vacío/error del sistema.
- Estado del lote con **badge de estado** del sistema (§3): «En refrigeración» (advertencia) y «Liberado» (éxito).
- Cantidades con la unidad base del producto, alineadas a la derecha, formato decimal del listado de existencias.
- Sección en `stock-detail`: tabla compacta dentro de la plantilla «Detalle con historial embebido»; mismas columnas sin Producto/Almacén; sin acciones.
- Todo con `translate` y claves nuevas `INVENTORY.LOTS.*` en es/en/pt. Sin componentes fuera del sistema de diseño ni patrón nuevo reutilizable (no se modifica `design-system.md`).

## Alternativas consideradas
- **Columnas «Disponible» en la lista de Existencias por producto/almacén:** mezclaría dos significados de «disponible» (venta vs. empaque); descartada. Solo se añade el enlace a lotes.
- **Pestaña dentro de Existencias:** esconde la consulta y complica filtros; descartada por coherencia con Movimientos/Ajustes (pantallas hermanas).
- **Pantalla de alta/liberación manual:** fuera de alcance por decisión del usuario.

## Comportamiento por privilegio/estado
- Solo lectura, visible con el módulo Inventario habilitado (mismo guard de ruta `data: { module: 'inventory' }`). Sin botones de acción.
- Estados: cargando, vacío («Aún no hay lotes»; si hay filtros, «Sin resultados»), error con reintento, éxito.
- Un lote en refrigeración muestra Disponible = 0 y una nota accesible («Bloqueado hasta su liberación»).
- **El frontend no es la barrera:** el bloqueo del granel en refrigeración y el saldo por lote los impone el backend (INV-L1..L3).

## Consecuencias
- Sin deuda visual nueva. Los productos sin lotes no cambian de aspecto: la sección y el enlace solo aparecen si existen lotes.
