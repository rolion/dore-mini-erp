# DDR-crear-iniciar-orden-receta-pantallas-ordenes: Pantallas de Órdenes de producción

**Estado:** Propuesto
**Task relacionado:** TASK-crear-iniciar-orden-receta
**Fecha:** 2026-11-26

## Contexto
El operario elige una receta activa, el almacén y cuántas veces la preparará, y ve de inmediato cuánto producirá y qué ingredientes necesita. Se reutilizan las plantillas de `docs/design/design-system.md` §5; el patrón de recetas está en `DDR-gestionar-recetas-produccion-pantallas-recetas`.

## Pantallas/flujos afectados
- Menú **Producción**: nuevo ítem **Órdenes de producción** (`/pocketbiz/production/orders`) bajo Recetas, mismo módulo `production`.
- **Lista** `/production/orders`: columnas N.º (enlace al detalle), Receta, Almacén, Preparaciones, Producción prevista (`120 unidad`), Estado (badge Borrador / En preparación), Fecha. Filtro de estado (Todos por defecto), botón «+ Nueva orden». Bajo 957 px, una tarjeta por orden.
- **Alta** `/production/orders/new`: campos Receta (`ng-select`, solo activas), Almacén (`ng-select`, solo activos; preselecciona el predeterminado) y Preparaciones (entero ≥ 1). Panel **Previsto** en vivo: «Producirás 120 unidad de <producto>» y tabla Ingrediente | Por preparación | Total previsto (cantidad × preparaciones). Pie: **Guardar borrador** (secundario), **Iniciar preparación** (primario; guarda e inicia), Cancelar (`unsavedChangesGuard`).
- **Edición** `/production/orders/:id/edit` (solo Borrador): la receta se muestra fija (solo lectura); se cambian almacén y preparaciones; el panel Previsto se recalcula.
- **Detalle** `/production/orders/:id`: datos (n.º, receta, producto resultante, almacén, preparaciones, estado, creada, **iniciada**), tabla de ingredientes con cantidad por preparación y total previsto. Acciones en cabecera: Borrador → **Iniciar preparación** (primario, con confirmación «No modifica las existencias»), Editar, Volver; En preparación → solo Volver. Bajo 957 px los ingredientes pasan a tarjetas (como en el detalle de recetas).

## Componentes/patrones elegidos
- Lista: plantilla «Lista con seguimiento de estados» (`features/purchases/pages/purchase-list`) con tabla Bootstrap y `ngb-pagination` de servidor, igual que Recetas.
- Alta/edición: «Formulario con líneas» variante de un solo paso con totales calculados (`purchase-form`); las líneas son solo lectura (derivadas de la receta), por lo que no hay añadir/quitar.
- Detalle: «Detalle de documento con acciones en la cabecera» (`purchase-detail`, `order-detail`), badges de §3, fechas `dd/MM/yyyy HH:mm`.
- Cantidades con hasta 4 decimales mostradas sin ceros sobrantes; unidad abreviada del snapshot.
- Sin componentes nuevos de Oreva ni desviaciones del sistema de diseño.

## Alternativas consideradas
- Un único botón «Crear e iniciar»: descartado; la tarjeta distingue borrador e inicio y guardar el borrador debe ser posible.
- Paso de resumen previo a guardar: descartado; el panel Previsto ya muestra el resultado y nada es irreversible.
- Elegir la receta también al editar un borrador: descartado (supuesto 1 del TASK); evita reconstruir la copia.

## Comportamiento por privilegio/estado
- Estados: cargando, vacío («Aún no hay órdenes», CTA «Nueva orden»), error (alerta con reintento), éxito (mensaje y regreso al detalle). Errores de servidor por campo sin borrar lo escrito; foco al primer error.
- Sin recetas activas: el selector muestra aviso con enlace a Recetas; sin almacenes activos: aviso con enlace a configuración de Inventario; ambos bloquean los botones.
- En preparación: sin edición ni nuevo inicio. El frontend solo oculta acciones; **el backend** impone módulo habilitado, aislamiento por `company_id`, receta activa al crear, entero positivo, transición de estado y que solo el borrador se edite o inicie.

## Consecuencias
Deuda visual aceptada: tabla Bootstrap con `ngb-pagination` (como Recetas y Servicios) en vez de `ngx-datatable`. Las acciones futuras (completar, cancelar) se sumarán a la misma cabecera de detalle.
