# DDR-consultar-ordenes-seguimiento-estado-lista-y-detalle: Lista y detalle de órdenes con saldo a granel

**Estado:** Propuesto
**Task relacionado:** TASK-consultar-ordenes-seguimiento-estado
**Fecha:** 2026-11-27

## Contexto
La lista y el detalle de órdenes existen (PROD-003/004/005). Falta ver lo elaborado y el saldo a granel, y filtrar por fecha y receta.

## Pantallas/flujos afectados
- `/pocketbiz/production/orders` (lista) y `/pocketbiz/production/orders/:id` (detalle).

## Componentes/patrones elegidos
- Lista: plantilla «Lista de solo lectura con filtros» + «Variante con seguimiento de estados» (`design-system.md` §5). Filtros: Estado, Receta (`select`), Desde/Hasta (`input type=date`, como `movement-list`). Columnas: Número, Receta, Previstas, Elaboradas, Saldo a granel (alineadas a la derecha con unidad), Estado (badge con texto), Fecha. «—» donde no aplica (elaboradas y saldo antes de refrigerar). Bajo 957 px se mantienen las tarjetas existentes con `dl` ampliado. Rango inválido (Desde > Hasta) muestra error junto al filtro y no consulta.
- Detalle: nueva sección «Existencias del lote» (`dl`: físico, disponible para empaque, estado del lote) dentro del bloque «registrado», visible en refrigeración y listo para empacar. Tiempos de refrigeración y datos de lote ya existen y no cambian.
- Badges: se conserva `badge-outline` actual (el sistema permite migrar al tocar; no se migra aquí para no mezclar alcance).

## Alternativas consideradas
Pestañas por etapa en la lista en lugar del filtro de estado: más cambio visual, sin ganancia; se mantiene el filtro.

## Comportamiento por privilegio/estado
Acciones según estado (editar/iniciar, registrar producción, liberar) ya se muestran por estado; el backend las vuelve a validar y exige el módulo `production`. Estados de pantalla: cargando, vacío (con filtros: badges de filtros activos + «Limpiar filtros»), error con «Reintentar».

## Consecuencias
Lista más ancha (dos columnas nuevas); queda la deuda de migrar badges a `app-status-badge`.
