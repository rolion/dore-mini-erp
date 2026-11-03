# DDR-agendar-y-gestionar-citas-pantallas-citas: Pantallas de Agenda → Citas

**Estado:** Propuesto
**Task relacionado:** TASK-agendar-y-gestionar-citas
**Fecha:** 2026-11-03

## Contexto
La recepción necesita ver, crear y gestionar citas. Hoy Agenda solo tiene la configuración de horarios ([DDR previo](DDR-configurar-horarios-y-disponibilidad-vista-semanal.md)).

## Pantallas/flujos afectados
- `/pocketbiz/agenda/citas` — **Lista con filtros** (variante con seguimiento de estados, referencia `purchase-list`) con alternancia «Listado / Calendario». Filtros en la URL: fecha, profesional, estado, búsqueda de cliente; «+ Nueva cita».
- Calendario: vista **diaria o semanal** del profesional elegido, apilada por día, sin grilla interactiva (mismo criterio que el DDR de horarios): bloques de texto con hora, cliente, servicio y badge de estado, y «Disponible» como franjas libres con botón «Agendar» (abre el formulario con inicio y profesional precargados).
- `/pocketbiz/agenda/citas/nueva` — **Formulario**: cliente (selector con búsqueda), profesional, servicio activo (precarga duración), fecha/hora de inicio, duración (editable, entero > 0), fin calculado de solo lectura, notas con aviso «No incluyas diagnósticos». Pie Guardar/Cancelar.
- `/pocketbiz/agenda/citas/:id` — **Detalle con acciones de ciclo de vida**: `dl` con cliente, servicio, profesional, inicio/fin, estado (badge con texto), notas; sección «Historial» (tabla apilada con evento, autor, fecha, motivo y horario anterior). Acciones desde `allowed_actions` del servidor.
- Diálogos `NgbModal` (`backdrop: 'static'`): **Confirmar cita**, **Reprogramar** (nuevo inicio/duración, motivo obligatorio, resumen antes→después), **Cancelar** (motivo obligatorio, `btn-danger` deshabilitado hasta tener motivo). Atendida / No asistió con diálogo de resumen, disponibles solo desde el inicio.

## Componentes/patrones elegidos
Plantillas de `design-system.md` §5: Lista (variante purchase-list), Formulario, Detalle con pestañas y acciones, Diálogo de acción irreversible con motivo. Badges con texto (`col-orange` programada, `col-blue` confirmada, `col-red` cancelada, `col-green` atendida, `col-grey` no asistió). Sin componentes nuevos compartidos; calendario propio con el mismo criterio de texto del DDR de horarios. Menú: Agenda → Citas junto a Configuración.

## Alternativas consideradas
- Librería de calendario (FullCalendar): nueva dependencia y accesibilidad por teclado limitada; descartada.
- Grilla interactiva por arrastre: costosa y poco accesible; descartada, se crea desde franja libre con botón.

## Comportamiento por privilegio/estado
Cargando, vacío (mensaje explicativo y «Limpiar filtros»), error con «Reintentar» y éxito visibles. Ante 409 de conflicto: se conservan los datos del formulario, se muestra `alert alert-warning` y se refresca la disponibilidad; el evento permanece en el calendario hasta confirmar el guardado. Doble envío impedido (botón deshabilitado «Guardando…»). Operable con teclado. Visible solo con Agenda, Personal, Clientes y Servicios habilitados y rol admin; **el backend aplica módulos, empresa y permisos**.

## Consecuencias
Calendario textual menos «visual» que una grilla horaria; aceptado por accesibilidad y coste. Sin vínculo a tratamiento en la UI hasta que exista ese módulo.
