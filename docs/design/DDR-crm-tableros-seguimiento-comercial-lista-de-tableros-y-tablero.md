# DDR-crm-tableros-seguimiento-comercial-lista-de-tableros-y-tablero: Seguimiento comercial (lista de tableros y tablero con columnas y tarjetas)

**Estado:** Propuesto
**Task relacionado:** TASK-crm-tableros-seguimiento-comercial
**Fecha:** 2026-11-27

## Contexto
La persona quiere llevar el seguimiento de clientes y prospectos en tableros que ella misma arma (columnas y tarjetas). El CRM ya tiene el Kanban de oportunidades y el editor «Tablero»; esta pantalla es el punto de entrada simple para crear tableros y trabajar dentro de ellos.

## Pantallas/flujos afectados
- Menú **CRM → Seguimiento comercial** (`/pocketbiz/crm/tracking`, `moduleGuard` de `customers`).
- **Lista de tableros** (`/pocketbiz/crm/tracking`): una tarjeta por tablero activo con su nombre (enlace al tablero); botón «Crear nuevo tablero» que abre un modal con solo **Nombre**.
- **Tablero** (`/pocketbiz/crm/tracking/:boardId`): título con el nombre, enlace «Volver a tableros», botón «Agregar columna» (modal con **Nombre**). Una columna por etapa activa, en orden, primera a la izquierda; encabezado con nombre y botón de tres puntos (menú «Agregar tarjeta» / «Archivar columna»); debajo, tarjetas (formato de Oportunidades, ver v2); el título y el botón «Ver» abren la ficha de la tarjeta (ver v3). Tareas e historial dentro de la tarjeta: PB-CRM-005.
- **Diálogo «Agregar tarjeta»**: Nombre*, Cliente o prospecto* (selector único con búsqueda sobre clientes y prospectos), Descripción (opcional).
- **Archivar columna**: columna vacía → confirmación simple; con tarjetas activas → aviso bloqueante «Mueve primero las N tarjetas…» sin opción de archivar.

## Componentes/patrones elegidos
Plantilla **Tablero Kanban de tarjetas con acciones accesibles** (`design-system.md` §5, referencia `crm-opportunity-board`): columnas `.card` de ancho fijo con scroll horizontal (apiladas en móvil), tokens de §2, botones de §3. Lista de tableros: rejilla de `.card` clicables (sin plantilla propia; mismos tokens). Menú de tres puntos: `ngbDropdown` (ng-bootstrap, ya usado en la plantilla Oreva) con `aria-label`. Modales: `NgbModal` con Reactive Forms y `board-name-dialog` como base. Selector de contacto: `ng-select` como en `opportunity-dialog`.

## Actualización v2 (2026-11-27, pedido del usuario)
Columnas y tarjetas replican el formato de `crm-opportunity-board` (mismo SCSS por `styleUrls`): encabezado «Nombre · N» con total, tarjeta con asa de arrastre, contacto, importe, siguiente acción y responsable, botón «Agregar» al pie, y arrastrar para mover de columna. Se conserva el menú de tres puntos. Sustituye «tarjetas solo con su nombre». Sin acciones Editar/Cerrar/Actividad en la tarjeta.

## Actualización v3 (2026-11-27, pedido del usuario)
Cada tarjeta lleva un botón «Ver» (`btn-light btn-sm`, con `aria-label` «Ver «título»») y su título es un botón de enlace; ambos abren la **ficha de la tarjeta** (`NgbModal` `lg`, mismo componente que «Nueva tarjeta» en modo edición). La ficha muestra Nombre*, Cliente o prospecto (fijo, con nota: la API no permite cambiarlo) y Descripción; «Guardar» actualiza y recarga el tablero. En el pie, «Agregar actividad» (solo en tarjetas existentes) abre encima el diálogo de actividades de Oportunidades, con su historial. Sin cambios de API. Las tareas dentro de la tarjeta siguen en PB-CRM-005.

## Alternativas consideradas
- Ampliar `crm-opportunity-board` con las acciones nuevas: mezcla filtros/importes/cierre con un flujo mínimo; descartado por el usuario (entrada nueva en el menú).
- Detalle de tarjeta con tareas: PB-CRM-005, fuera de alcance.

## Comportamiento por privilegio/estado
Cargando, error con «Reintentar», lista de tableros vacía («Aún no tienes tableros» + botón crear), tablero sin columnas («Agrega tu primera columna»), columna sin tarjetas («Sin tarjetas»), 400 junto al campo, 409 (`stage_has_cards`, nombre repetido, tablero archivado) en `alert-warning`. Solo admin de empresa; el **backend** valida empresa, tablero, columna y contacto; ocultar botones no es seguridad.

## Consecuencias
Tres pantallas CRM de tableros conviven (Seguimiento, Oportunidades, Tablero); deuda aceptada hasta unificarlas. Se amplía `design-system.md` §5 con una línea sobre esta variante.
