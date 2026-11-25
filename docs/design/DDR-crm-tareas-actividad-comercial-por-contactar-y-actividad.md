# DDR-crm-tareas-actividad-comercial-por-contactar-y-actividad: Lista «Por contactar» y registro de actividad

**Estado:** Propuesto
**Task relacionado:** TASK-crm-tareas-actividad-comercial
**Fecha:** 2026-11-25

## Contexto
El vendedor necesita ver a quién contactar (tareas por vencimiento) y registrar qué pasó (actividad). La ficha 360° (PB-CRM-002) aún no está integrada; los accesos deben existir ya desde la tarjeta del Kanban y la lista de clientes, y los componentes deben poder embeberse en la ficha.

## Pantallas/flujos afectados
- Menú **CRM → Por contactar** (`/pocketbiz/crm/tasks`, `moduleGuard` de `customers`).
- **Por contactar (lista)**: breadcrumb y encabezado con botón «Nueva tarea». Filtros: **Responsable** (por defecto, la persona actual; opción «Todos»), **Estado** (Pendientes por defecto; Vencidas, Hechas, Canceladas, Todas). Columnas: Vencimiento (insignia «Vencida» si aplica), Tarea, Relacionado (cliente u oportunidad), Responsable, Estado y acciones (Completar, Editar, Cancelar, Reabrir, Archivar según estado). Orden por vencimiento ascendente. Las archivadas no aparecen en ningún filtro.
- **Diálogo Tarea** (alta/edición): título, relacionado (cliente u oportunidad, no editable al editar), vencimiento, responsable.
- **Diálogo Completar tarea**: confirmación con bloque opcional «Registrar actividad» (canal, resultado, notas).
- **Diálogo Actividad** (desde tarjeta del Kanban, fila de Clientes y, luego, la ficha): canal, resultado (opcional), notas, fecha y hora (por defecto ahora). Debajo, historial de actividad de esa entidad (más reciente primero).
- **Tarjeta del Kanban**: se agregan acciones «Registrar actividad», «Nueva tarea» e «Historial de actividad». **Lista de clientes CRM**: las mismas acciones por fila.

## Componentes/patrones elegidos
- Lista: plantilla **Lista** (§5) con variante compacta bajo `lg` y badges de estado (§3): Pendiente = advertencia, Vencida = peligro, Hecha = éxito, Cancelada = secundario.
- Diálogos `NgbModal` con Reactive Forms, `form-label`/`form-control`, errores `small.text-danger`; cancelar tarea usa el patrón de confirmación de §5 sin motivo obligatorio.
- Componentes `task-dialog`, `complete-task-dialog`, `activity-dialog` y `activity-history` autónomos (reciben la entidad por entrada) para reutilizarlos en la ficha 360°. Sin colores ni patrones nuevos; no se modifica `design-system.md`.

## Alternativas consideradas
- **Pestaña «Tareas» dentro del Kanban**: mezcla seguimiento con pipeline; descartada, la tarjeta pide un menú propio «Por contactar».
- **Actividad como página aparte**: innecesaria; el diálogo y el historial embebido cubren el alcance.

## Comportamiento por privilegio/estado
- **Cargando:** «Cargando…». **Vacío:** «No tienes tareas pendientes» con botón «Nueva tarea». **Sin resultados** de filtro: «Limpiar filtros». **Error:** `alert-danger` con «Reintentar». **400:** mensaje junto al campo. **409** (tarea ya completada, oportunidad cerrada, etc.): `alert-warning` y recarga de la lista. **Éxito:** la lista y el historial reflejan el cambio.
- Acciones visibles solo según estado; el **backend** valida empresa, entidad relacionada, responsable y transición (ocultar un botón no es seguridad).

## Consecuencias
Pantalla nueva coherente con las listas existentes. Deuda aceptada: sin vista de calendario ni recordatorios; la ficha 360° embeberá los componentes cuando se integre.
