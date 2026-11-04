# PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias (v1)

**Task:** TASK-mejorar-ux-horarios-y-ausencias · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-mejorar-ux-horarios-y-ausencias-dialogos-y-semana · ADR: Ninguno (el contrato es aditivo; sigue vigente ADR-configurar-horarios-y-disponibilidad-limites-y-tiempo)

## Objective
Permitir registrar el mismo turno en varios días (y repetirlo toda la semana, hasta fin de mes o hasta una fecha) en un solo guardado, y poder editar y eliminar ausencias.

## Context
Ver TASK. El modelo `Shift` ya es recurrente semanal con `valid_from/valid_until`; la mejora es de contrato (alta múltiple) y de UX. Las ausencias no tienen edición ni borrado en backend.

# Specification

## Domain context
Bounded context `agenda`. Sin cambios en otros contextos.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Turno | Horario recurrente de un día de la semana, vigente entre dos fechas | `models.py:18` |
| Ausencia | Intervalo (instantes con zona) que resta disponibilidad | `models.py:28` |
| Alta múltiple | Crear un turno por cada día elegido con el mismo horario | nuevo |

## Current behavior
Ver TASK (Hechos).

## Expected behavior
- Un envío crea un turno por cada día elegido, todo o nada.
- La vigencia se elige con atajos (esta semana, fin de mes, fecha).
- Una ausencia se puede editar y eliminar.

## Domain rules / invariants
- INV-01 (existente): un turno termina el mismo día y las pausas caben dentro, sin solaparse.
- INV-02 (existente): dos turnos del mismo día no se solapan en horas si sus vigencias se cruzan en esa fecha (`shifts_overlap`).
- INV-03 (existente): una ausencia debe terminar después de empezar.
- INV-04 (nueva): un día no puede repetirse en la alta múltiple; los días son 0-6 y hay al menos uno.

## Acceptance criteria
- AC-01: `POST shifts/` con `days: [0,1,2]` crea tres turnos con el mismo horario, pausas y vigencia y responde 201 con la lista.
- AC-02: si alguno solapa con un turno existente, responde 400 indicando el día y no se crea ninguno.
- AC-03: `POST shifts/` con `day` (un solo día) sigue funcionando igual que hoy; enviar `day` y `days` a la vez, o ninguno, responde 400.
- AC-04: `PUT absences/<id>/` actualiza inicio, fin y motivo con la misma validación que el alta (200).
- AC-05: `DELETE absences/<id>/` elimina la ausencia (204); tras ello, la disponibilidad semanal la recupera.
- AC-06: editar o eliminar una ausencia de otro profesional o de otra empresa responde 404.
- AC-07: en el diálogo de turno se pueden marcar varios días, usar los atajos y elegir la repetición; el resumen refleja la selección; guardar con cero días está deshabilitado.
- AC-08: «Hasta fin de mes» fija `valid_until` al último día del mes de la semana visible; «Solo esta semana» al domingo visible.
- AC-09: en cada ausencia de la tarjeta hay «Editar» y «Eliminar»; editar abre el diálogo con los datos y guarda con PUT; eliminar pide confirmación.
- AC-10: «Todo el día» envía `starts` = fecha inicial 00:00 y `ends` = día siguiente a la fecha final 00:00; al editar una ausencia con esa forma, el interruptor aparece activado.
- AC-11: «Copiar a otros días» abre el alta con horario, pausas y vigencia precargados y el día original deshabilitado.
- AC-12: textos nuevos en es/en/pt con las mismas claves.

## Edge cases / Error cases
- EDGE-01: dos días marcados chocan entre sí: no ocurre (días distintos); chocan con un turno existente → AC-02.
- EDGE-02: `days` vacío o con valores fuera de 0-6 → 400.
- EDGE-03: ausencia con fin ≤ inicio → 400 (también en PUT).
- EDGE-04: fin de mes anterior a la semana visible no ocurre (el mes se calcula de la semana visible; si el domingo cruza de mes, se usa el último día del mes del lunes visible y, si es anterior al domingo, el domingo).
- EDGE-05: PUT/DELETE de ausencia inexistente → 404.

## Authorization / permissions
Sin cambios: empresa por sesión, módulos `personnel` y `agenda`, acceso administrativo (`AgendaView`). Todas las consultas filtran por `company_id`.

## API contract
- API-01: `POST /api/agenda/<professional_id>/shifts/` acepta `days: int[]` como alternativa a `day`. Con `days` responde 201 con un arreglo de turnos; con `day` mantiene la respuesta actual (compatible hacia atrás). `PUT shifts/<id>/` sin cambios (solo `day`).
- API-02: `PUT /api/agenda/<professional_id>/absences/<absence_id>/` con `starts`, `ends`, `reason` → 200 con la ausencia.
- API-03: `DELETE /api/agenda/<professional_id>/absences/<absence_id>/` → 204.

## UI behavior
UI-01..: según DDR-mejorar-ux-horarios-y-ausencias-dialogos-y-semana (chips de días, repetición, ausencia «Todo el día», acciones en la tarjeta, confirmación de borrado, cabecera con acciones). Plantilla: configuración de `docs/design/design-system.md` sección 5, botones de sección 3.

## Non-functional requirements
Alta múltiple en una sola transacción con el bloqueo de `Schedule` existente.

## Out of scope
Eliminar turnos; detectar citas existentes al crear/editar turnos o ausencias; vigencia sin fecha final; ausencias recurrentes; cambios de zona horaria.

## Open questions
- Eliminar turnos queda como mejora futura (se corrige editando su vigencia).

# Test Specification

## Unit tests
- Función pura de fechas de repetición (esta semana / fin de mes) y de la ausencia «Todo el día» en el frontend (AC-08, AC-10).

## Integration tests
Backend (`agenda/tests/test_api.py`): AC-01..AC-06, EDGE-02/03/05. Frontend: `agenda-api.service.spec.ts` (PUT/DELETE de ausencia, POST con `days`) y `agenda.component.spec.ts` nuevo (AC-07, AC-09, AC-11, AC-12 vía `provideTestTranslations()`).

## E2E
NO — flujo de configuración cubierto por pruebas de componente e integración de API.

## Regression tests
Alta con `day` y edición de turno por PUT siguen igual (AC-03).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01..AC-03 | test_api (backend) |
| AC-04..AC-06 | test_api (backend) |
| AC-07, AC-11 | spec de componente |
| AC-08, AC-10 | spec unitario de funciones puras |
| AC-09 | spec de componente + servicio |
| AC-12 | prueba de claves i18n existente + `npm run i18n:check` |

# Implementation Plan

## Architecture considerations
Se mantiene la capa actual (vistas DRF + dominio puro). La alta múltiple reutiliza `validate_shift` y `shifts_overlap`.

## Proposed solution
Backend: `ShiftView.post` normaliza a una lista de días y valida cada candidato bajo la misma transacción; nuevo `AbsenceDetailView` con `put` y `delete` filtrados por `schedule` del profesional y la empresa. Frontend: formulario de turno con `days` (array de números) y repetición; formulario de ausencia con interruptor «Todo el día»; helpers puros en `agenda/models/` o `services/`.

## Files/components affected
- backend: `modules/agenda/api.py`, `modules/agenda/urls.py`, `modules/agenda/tests/test_api.py`
- frontend: `features/agenda/agenda.component.{ts,html,scss}`, `models/agenda.ts`, `services/agenda-api.service.{ts,spec.ts}`, nuevo `agenda.component.spec.ts`, `assets/i18n/{es,en,pt}.json`
- docs: TASK, DDR, este PLAN.

## Implementation steps
1. Backend: aceptar `days` en `ShiftView.post` (AC-01..03, INV-04).
2. Backend: `AbsenceDetailView` PUT/DELETE y ruta (AC-04..06).
3. Pruebas de backend.
4. Servicio Angular: `saveShift` con `days`, `updateAbsence`, `deleteAbsence`.
5. Diálogo de turno: chips, atajos, repetición, resumen, «Copiar a otros días» (AC-07, 08, 11).
6. Diálogo de ausencia: «Todo el día», edición, eliminación con confirmación y acciones en la tarjeta (AC-09, 10).
7. Cabecera y mensajes; claves i18n es/en/pt (AC-12).
8. Pruebas de frontend y `npm run lint`, `npm test`, `npm run i18n:check`.

## Database / migrations
Sin migraciones.

## Risks
Editar/borrar ausencias cambia la disponibilidad ofrecida a citas; es el efecto esperado.

## New dependencies
Ninguna.
