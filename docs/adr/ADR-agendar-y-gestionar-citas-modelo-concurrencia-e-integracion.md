# ADR-agendar-y-gestionar-citas-modelo-concurrencia-e-integracion: Modelo de cita, concurrencia e integración

**Estado:** Propuesto
**Task relacionado:** TASK-agendar-y-gestionar-citas
**Fecha:** 2026-11-03

## Contexto
PB-AGE-002 añade citas al contexto Agenda. Deben impedir doble reserva del profesional (también con solicitudes simultáneas), respetar turnos, pausas y ausencias de PB-AGE-001, y referenciar cliente, servicio y profesional que pertenecen a otros contextos.

## Decisión
1. **Agregado `Appointment` en Agenda** (dominio puro en `agenda/domain/appointment.py`, sin Django). Estados `scheduled`, `confirmed`, `cancelled`, `attended`, `no_show`; transiciones solo por métodos (`confirm`, `reschedule`, `cancel`, `mark_attended`, `mark_no_show`). Ocupan horario `scheduled` y `confirmed`. Los terminales no cambian. Persistencia: `Appointment` (company_id, professional_id, customer_id, service_id, snapshots `customer_name`, `service_name`, `starts`/`ends` como instantes, `duration_minutes`, `notes`, `status`, `treatment_item_id` UUID nulo sin validar) y `AppointmentEvent` (cita, tipo, autor `BigInteger`, fecha, motivo, horario anterior). Migración aditiva `0002`.
2. **Concurrencia:** reutilizar el bloqueo de fila de `Schedule` por empresa+profesional dentro de `transaction.atomic` (mismo patrón ya probado en turnos). Dentro del bloqueo se verifica que el intervalo completo quepa en un único intervalo de disponibilidad (turno − pausas − ausencias, en `America/La_Paz`) y que no se solape con otra cita que ocupe horario, excluyendo la propia al reprogramar. Intervalos semiabiertos: 09:00–09:30 y 09:30–10:00 no chocan. Una restricción de exclusión de PostgreSQL queda descartada: añade `btree_gist` y una extensión; el bloqueo basta y es coherente con el resto.
3. **Integración por fachadas públicas:** Clientes (`get_customer_for_sale`, nombre y estado activo), Servicios (`get_service_for_new_use`, nombre y duración) y Personal (`professional_exists`). Agenda guarda snapshots de nombres para mostrar el historial aunque el origen cambie; el cliente debe estar activo para crear, no para operar citas ya creadas. Nunca importa infraestructura ajena. Para filtrar por nombre de cliente usa `search_customer_ids`. Las vistas exigen `personnel`, `agenda`, `customers` y `services` habilitados y admin de empresa activa (permiso por defecto).
4. **Contrato** bajo `/api/agenda/appointments/`: lista con filtros (`from`, `to`, `professional`, `status`, `search`) y paginación; alta; detalle con historial y `allowed_actions`; acciones `confirm`, `reschedule`, `cancel`, `attend`, `no-show` por POST; edición de notas por PATCH. Conflicto de horario: 409 con `code` y mensaje; el servidor es la autoridad. Las rutas existentes no cambian.
5. **Vínculo a tratamiento:** no existe módulo proveedor; el campo `treatment_item_id` se acepta nulo y no se valida ni expone en la UI hasta que exista PB de tratamientos.

## Alternativas consideradas
- `ExclusionConstraint` con `btree_gist`: garantía en BD, pero dependencia de extensión y no cubre turnos/ausencias; se prefiere bloqueo + validación de dominio.
- Citas en un módulo nuevo `appointments`: duplicaría contexto de profesional/disponibilidad; la reserva es parte del lenguaje de Agenda.
- Leer tablas de Clientes/Servicios directamente: viola la regla entre módulos.

## Estrategia de rollback / mitigación
Migración solo aditiva (tablas nuevas). Ante incidencia: deshabilitar Agenda por empresa y conservar tablas; revertir el despliegue no pierde datos previos. No se modifican tablas existentes.

## Consecuencias
Garantía de no doble reserva depende de que toda escritura pase por el servicio con bloqueo. Turnos y ausencias modificados después no revisan citas existentes (limitación conocida, seguimiento posterior). Snapshots pueden quedar desactualizados respecto del origen por diseño.
