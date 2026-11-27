# ADR-gestionar-atencion-odontologica-desde-citas-numeracion-de-citas-por-gestion: Numeración correlativa de citas por gestión fiscal

**Estado:** Propuesto
**Task relacionado:** TASK-gestionar-atencion-odontologica-desde-citas
**Fecha:** 2026-11-27

## Contexto
Las citas se identifican por UUID y la pantalla Odontología → Citas mostraba sus 8 primeros caracteres («ID de cita»). El usuario pide un código correlativo `C-000001`, único en cada gestión fiscal (período fiscal de Contabilidad), y renombrar la columna a «Cita». Es la tercera serie por período del sistema (ventas `PD-`, compras `NC-`): se sigue el mismo patrón (`ADR-numeracion-correlativa-pedidos-venta-contador-por-periodo`, `ADR-numeracion-correlativa-compras-contador-por-periodo`).

Decisiones del usuario (2026-11-27): (1) la gestión es la de la **fecha en que se crea** la cita; (2) sin gestión abierta se **bloquea** la creación con aviso; (3) las citas existentes se **numeran** por orden de creación.

## Decisión
1. **Datos en Agenda:** `Appointment.number` (int, null), `fiscal_period_id` (UUID, null) y `fiscal_period_name` (instantánea del nombre al numerar). `UniqueConstraint(company_id, fiscal_period_id, number)` condicionado a `number IS NOT NULL`. Tabla `AppointmentNumberCounter(company_id, fiscal_period_id, last_number)` con restricción única por empresa y período. El UUID sigue siendo la clave primaria; el código visible es `C-` + 6 dígitos (`appointment_code(number)` en el dominio) y se repite entre gestiones: la identidad es (empresa, gestión, número) y la UI muestra la gestión junto al código.
2. **Asignación al crear** (`create` de Agenda, dentro de su transacción y tras el bloqueo del profesional y la validación del horario): `AppointmentNumbering.next_number(hoy_en_La_Paz)` (adaptador de infraestructura, única vía hacia Contabilidad) llama a `accounting.services.lock_open_period` (bloquea la fila del período con `select_for_update`: serializa altas de la misma gestión entre sí y frente a su cierre) y luego incrementa el contador bajo ese bloqueo. Un fallo posterior revierte también el número: sin huecos. El número **no cambia** al reprogramar ni al cancelar y **nunca se reutiliza**.
3. **Sin gestión o cerrada:** `409` con código estable `fiscal_period_missing` / `fiscal_period_closed` (`AppointmentConflict`); la cita no se crea y el contador no avanza. El cliente traduce el código (`AGENDA.CITAS.VAL_FISCAL_PERIOD_*`).
4. **Dependencia nueva `agenda → accounting`** (solo por `accounting.services`, solo desde `agenda/infrastructure/adapters.py`), declarada en `ALLOWED_DEPENDENCIES` de `test_boundaries`. Sin ciclo: Contabilidad no importa Agenda.
5. **Migraciones:** `agenda/0004_appointment_numbers` (aditiva: columnas nullable, contador y restricciones) y `agenda/0005_backfill_appointment_numbers` (datos): numera por empresa y gestión según la fecha de creación (America/La_Paz) en orden `created_at, id`, continúa desde el contador y es **repetible**; las citas cuya fecha de creación cae fuera de toda gestión quedan sin número (la UI muestra el código corto del UUID). Misma técnica que `sales/0007`.
6. **API:** las citas de Agenda devuelven `code` (`C-000001` o `null`) y `fiscal_period_name`; la fachada `agenda/services.py` los expone en `AppointmentSnapshot` (`code`, `fiscal_period_name`) y Odontología los reenvía en el listado clínico, el detalle y el historial del paciente (`appointment_code`). Cambio compatible hacia atrás (campos nuevos).
7. **UI:** Odontología → Citas: columna «Cita» (antes «ID de cita») con `C-000001` y «Gestión X» debajo; detalle de atención y de cita de Agenda: fila «Cita»; listado de Agenda: columna «Cita»; historial de la ficha: código antes de la fecha. Citas sin número muestran el código corto (Odontología) o «—» / «Sin número» (Agenda).

## Alternativas consideradas
- **Gestión por fecha de la cita (inicio):** como ventas y compras, pero una cita agendada hoy para enero exigiría que exista la gestión siguiente y los números no seguirían el orden de agenda. Descartada por el usuario.
- **Crear sin número si no hay gestión / usar año calendario:** dejan citas sin numerar o mezclan dos criterios. Descartadas por el usuario.
- **Contador compartido entre series:** ya descartado en ventas/compras (series separadas, contador propio por módulo); se mantiene la independencia de módulos.
- **Número solo en Odontología:** la cita es de Agenda; numerarla en Odontología dejaría las citas no odontológicas sin código.

## Estrategia de rollback / mitigación
Migraciones aditivas (`0004`) revertibles con `migrate agenda 0003`; el backfill (`0005`) es solo datos y reversible como `noop` (los números quedan, sin efecto en el resto). Riesgo operativo asumido por el usuario: **si una empresa no tiene gestión fiscal abierta para hoy, no puede agendar citas** hasta crearla o reabrirla en Contabilidad; las empresas nuevas reciben una gestión (año en curso) por defecto. Si hace falta volver al comportamiento anterior, basta quitar la llamada a `AppointmentNumbering` en `create` (las citas ya numeradas conservan su número).

## Consecuencias
- Agenda depende de Contabilidad por fachada. Crear una cita ahora puede responder 409 por gestión ausente o cerrada.
- Un número se repite entre gestiones; la gestión se muestra siempre junto al código.
- Las citas anteriores a la serie sin gestión quedan sin código; es una deuda visible y acotada.
- La búsqueda por código en Agenda queda fuera de alcance.
