# DDR-crm-tareas-actividad-comercial-por-contactar-y-actividad: Lista «Por contactar» y registro de actividad

**Estado:** Propuesto
**Task relacionado:** TASK-crm-tareas-actividad-comercial
**Fecha:** 2026-11-25

## Contexto
El vendedor necesita ver a quién contactar (tareas por vencimiento) y registrar qué pasó (actividad). La ficha 360° (PB-CRM-002) aún no está integrada; los accesos deben existir ya desde la tarjeta del Kanban y la lista de clientes, y los componentes deben poder embeberse en la ficha.

## Pantallas/flujos afectados
- Menú **CRM → Por contactar** (`/pocketbiz/crm/tasks`, `moduleGuard` de `customers`).
- **Por contactar (lista)**: breadcrumb y encabezado con botón «Nueva tarea». Filtros: **Responsable** (por defecto, la persona actual; opción «Todos»), **Estado** (Pendientes por defecto; Vencidas, Hechas, Canceladas, Todas). Columnas: Vencimiento (insignia «Vencida» si aplica), Tarea, Relacionado (cliente u oportunidad), Responsable, Estado y acciones (Completar, Editar, Cancelar, Reabrir, Archivar según estado). Orden por vencimiento ascendente. Las archivadas no aparecen en ningún filtro.
- **Diálogo Tarea** (alta/edición): título, vencimiento, responsable y relacionado. Desde «Por contactar» el relacionado se elige entre **clientes**; desde la tarjeta del Kanban queda fijo en la **oportunidad**; desde la fila de un cliente, fijo en ese cliente. No es editable al editar. *(Ajuste v1.1, REV-07: la lista no busca oportunidades porque exigiría elegir tablero.)*
- **Diálogo Completar tarea**: confirmación con bloque opcional «Registrar actividad» (canal, resultado, notas).
- **Diálogo Actividad** (desde tarjeta del Kanban, fila de Clientes y, luego, la ficha): canal, resultado (opcional), notas, fecha y hora (por defecto ahora). Debajo, historial de actividad de esa entidad (más reciente primero, con «Ver más» para páginas siguientes), embebido en el mismo diálogo.
- **Tarjeta del Kanban**: se agregan acciones «Registrar actividad», «Nueva tarea» e «Historial de actividad». **Lista de clientes CRM**: las mismas acciones por fila.

## Componentes/patrones elegidos
- Lista: plantilla **Lista** (§5) con tabla apilada bajo `md` (768 px) en lugar de tarjetas: son pocas columnas y no hay filtros plegables. Badges de estado `badge-outline` (§3): Pendiente `col-orange`, Vencida `col-red`, Hecha `col-green`, Cancelada `col-grey`. En el historial, el canal va en `col-grey` y el resultado por tono: Contactado/Interesado `col-green`, Sin respuesta `col-orange`, No interesado `col-red`, Seguimiento pendiente `col-cyan`; siempre con texto.
- Diálogos `NgbModal` con Reactive Forms, `form-label`/`form-control`, errores `small.text-danger`; **cancelar y archivar** piden confirmación con un diálogo propio (`confirm-task-action-dialog`, patrón de acción irreversible de §5 sin motivo); completar y reabrir no la piden.
- Componentes `task-dialog`, `complete-task-dialog`, `activity-dialog` (con el historial embebido), `activity-fields` y `confirm-task-action-dialog` autónomos (reciben la entidad por entrada) para reutilizarlos en la ficha 360°. Sin colores ni patrones nuevos; no se modifica `design-system.md`.

## Alternativas consideradas
- **Pestaña «Tareas» dentro del Kanban**: mezcla seguimiento con pipeline; descartada, la tarjeta pide un menú propio «Por contactar».
- **Actividad como página aparte**: innecesaria; el diálogo y el historial embebido cubren el alcance.

## Comportamiento por privilegio/estado
- **Cargando:** «Cargando…». **Vacío:** «No tienes tareas pendientes» con botón «Nueva tarea». **Sin resultados** de filtro: «Limpiar filtros». **Error:** `alert-danger` con «Reintentar». **400:** mensaje junto al campo. **409** (tarea ya completada, oportunidad cerrada, etc.): `alert-warning` y recarga de la lista. **Éxito:** la lista y el historial reflejan el cambio.
- Acciones visibles solo según estado; el **backend** valida empresa, entidad relacionada, responsable y transición (ocultar un botón no es seguridad).

## Consecuencias
Pantalla nueva coherente con las listas existentes. Deuda aceptada: sin vista de calendario ni recordatorios; la ficha 360° embeberá los componentes cuando se integre.
