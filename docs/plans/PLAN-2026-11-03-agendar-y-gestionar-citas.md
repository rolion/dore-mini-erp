# PLAN-2026-11-03-agendar-y-gestionar-citas (v1)

**Task:** TASK-agendar-y-gestionar-citas · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR](../design/DDR-agendar-y-gestionar-citas-pantallas-citas.md) · [ADR](../adr/ADR-agendar-y-gestionar-citas-modelo-concurrencia-e-integracion.md)

## Objective
Permitir a la recepción crear y gestionar citas (confirmar, reprogramar, cancelar, atendida/no asistió) de un profesional, sin doble reserva y dentro de la disponibilidad de PB-AGE-001.

# Specification

## Domain context
Bounded context Agenda; consume Clientes, Servicios y Personal por fachadas públicas.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Cita | Reserva de un profesional para un cliente y un servicio en un intervalo | Tarjeta |
| Ocupa horario | Estado `scheduled` o `confirmed` | Tarjeta |
| Franja libre | Intervalo de disponibilidad no ocupado por citas | PB-AGE-001 |

## Current behavior
Solo existen turnos, pausas, ausencias y disponibilidad semanal (`agenda/api.py`, `application/week.py`).

## Expected behavior
Existe el agregado Cita con historial; la disponibilidad semanal sigue siendo la de PB-AGE-001 y la lista de franjas libres para agendar se calcula descontando citas que ocupan horario.

## Domain rules / invariants
- INV-01 La cita cabe completa en un intervalo de disponibilidad del profesional (turno − pausas − ausencias), en `America/La_Paz`.
- INV-02 Dos citas que ocupan horario del mismo profesional no se solapan; intervalos semiabiertos (09:00–09:30 y 09:30–10:00 válidas).
- INV-03 Duración entera > 0; fin = inicio + duración. Cliente activo y servicio activo al crear; profesional de la empresa.
- INV-04 Transiciones: `scheduled→confirmed`; `scheduled|confirmed→cancelled` (motivo); `scheduled|confirmed→attended|no_show` solo cuando ya pasó el inicio; reprogramar solo `scheduled|confirmed`, conserva estado y registra horario anterior, autor y motivo. Los estados terminales no cambian.
- INV-05 Reprogramar excluye la propia cita y es todo o nada.
- INV-06 Atender no crea tratamiento ni pago. Las notas son administrativas.

## Acceptance criteria
- AC-01 Crear cita válida (cliente sin perfil odontológico incluido) queda `scheduled`; rechaza cliente/servicio inactivo o ajeno, profesional ajeno, duración ≤ 0, fuera de turno, pausa o ausencia.
- AC-02 Dos solicitudes simultáneas por el mismo horario del mismo profesional: una se crea, la otra recibe 409.
- AC-03 09:00–09:30 y 09:30–10:00 se aceptan; 09:15–09:45 sobre la primera se rechaza.
- AC-04 Confirmar pasa a `confirmed` y sigue ocupando horario.
- AC-05 Reprogramar con motivo mueve la cita, conserva horario anterior/autor/motivo en el historial; si hay conflicto no cambia nada (409); no choca consigo misma.
- AC-06 Cancelar exige motivo, libera el horario (otra cita puede ocupar la franja) y la cita sigue consultable con su historial.
- AC-07 Atendida/No asistió solo si el inicio ya pasó; no crea cobro ni acto clínico.
- AC-08 Lista filtrable por fecha, profesional, estado y búsqueda de cliente, aislada por empresa, con paginación; detalle devuelve historial y `allowed_actions`.
- AC-09 UI: calendario diario/semanal y listado, crear desde franja libre, resúmenes de confirmación, conservar datos y refrescar ante conflicto, estados cargando/vacío/error/éxito, doble envío bloqueado, teclado.

## Edge cases / Error cases
Transición inválida → 409; módulo deshabilitado → 403 `module_disabled`; ajeno → 404; fecha/duración fuera de rango → 400; reprogramar a su mismo horario permitido; cliente inactivo después de creada no impide operarla.

## Authorization / permissions
Admin de empresa activa y módulos `personnel`, `agenda`, `customers`, `services` habilitados (permiso por defecto). Empresa siempre de la sesión.

## API contract
- API-01 `GET/POST /api/agenda/appointments/` (filtros `from`,`to`,`professional`,`status`,`search`, paginado).
- API-02 `GET/PATCH /api/agenda/appointments/{id}/` (PATCH solo notas).
- API-03 `POST …/{id}/confirm|reschedule|cancel|attend|no-show/`.
- API-04 `GET /api/agenda/appointments/free-slots/?professional&date_from&date_to&duration` devuelve franjas libres.
Rutas de PB-AGE-001 sin cambios.

## UI behavior
UI-01 a UI-04: lista, formulario, detalle y diálogos según el DDR y `design-system.md` §5.

## Non-functional requirements
Consultas sin N+1 (snapshots evitan llamadas por fila); mensajes en español.

## Out of scope
Sucursales, sillón/sala/equipo, cobros, tratamiento, vínculo a ítem de tratamiento (campo nulo sin validar), revisión de citas al editar turnos/ausencias, notificaciones, restringir fechas pasadas en la creación, compatibilidad profesional↔especialidad del servicio.

## Open questions
No bloquean (se asumió lo anterior): restricción de fechas pasadas; si reprogramar debe volver a `scheduled`; alerta de citas existentes al crear ausencias.

# Test Specification

## Unit tests
Dominio: INV-01 a INV-05 (solapes, intervalos contiguos, transiciones, inicio pasado).
## Integration tests
API con `TransactionTestCase`, `Barrier` para AC-02, empresas distintas, módulos deshabilitados, snapshots, historial.
## E2E
**NO** — se cubre con integración y recorrido local; sin Playwright.
## Regression tests
Rutas y pruebas de PB-AGE-001 siguen verdes.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Integración + dominio |
| AC-02 | Integración concurrente en PostgreSQL |
| AC-03 | Dominio + integración |
| AC-04 | Integración |
| AC-05 | Integración (éxito, conflicto, todo-o-nada) |
| AC-06 | Integración |
| AC-07 | Dominio + integración |
| AC-08 | Integración |
| AC-09 | `ng build`, specs de servicio/componentes y recorrido local |

# Implementation Plan

## Architecture considerations
Según ADR: dominio puro, bloqueo por `Schedule`, fachadas, snapshots, migración aditiva.

## Proposed solution
Aplicación `agenda/application/appointments.py` orquesta validación y escritura transaccional; vistas delgadas; frontend en `features/agenda/` con servicio de citas y páginas lista/formulario/detalle.

## Files/components affected
- Backend: `agenda/domain/appointment.py`, `models.py`, `migrations/0002_*`, `application/appointments.py`, `infrastructure/adapters.py`, `api.py`/`appointments_api.py`, `urls.py`, tests.
- Frontend: `features/agenda/{models,services,pages,components}`, `app.routes.ts`, `assets/data/routes.json`.
- Docs: `design-system.md` solo si el calendario textual se convierte en patrón reutilizable.

## Implementation steps
1. Dominio de cita y pruebas (INV-01..05).
2. Modelos, migración 0002 y adaptadores de Clientes/Servicios (AC-01).
3. Servicio de aplicación con bloqueo y endpoints de alta, lista, detalle, free-slots (AC-01..03, AC-08).
4. Acciones confirm/reschedule/cancel/attend/no-show e historial (AC-04..07).
5. Frontend: servicio, lista y calendario, formulario, detalle y diálogos, menú y rutas (AC-09).
6. Verificaciones de la Test Specification y registro de resultados.

## Database / migrations
`0002` aditiva con tablas `Appointment` y `AppointmentEvent`, índices por (company_id, professional_id, starts) y estado. No se editan migraciones aplicadas.

## Risks
Concurrencia (mitigada con bloqueo y pruebas); límites de intervalos y zona horaria; consistencia de snapshots.

## New dependencies
Ninguna.
