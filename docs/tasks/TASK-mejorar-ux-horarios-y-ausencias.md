# TASK-mejorar-ux-horarios-y-ausencias: Registrar un mismo horario en varios días y editar ausencias

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-mejorar-ux-horarios-y-ausencias
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/58

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN → PLANNING | Veredicto NEEDS_PLAN, diseño requerido | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | Specification READY, plan v1 | delivery-start |

## Investigación

### Requerimiento
Crítica de diseño de la pantalla «Horarios y ausencias» (Agenda › Configuración), etapa de refinamiento de UX:
- Registrar **un mismo horario para varios días de la semana o del mes** sin repetir el formulario.
- «Al parecer no se puede editar una ausencia».

### Hechos encontrados
- `backend/modules/agenda/urls.py:21` — `absences/` solo se enruta a `AbsenceView`; no hay ruta con `<absence_id>`.
- `backend/modules/agenda/api.py:119-128` — `AbsenceView` solo implementa `post`. **No existe editar ni eliminar ausencias** (carencia de backend, no solo de UI).
- `frontend/panel_admin/src/app/features/agenda/services/agenda-api.service.ts:24-26` — `saveAbsence` solo hace `POST`.
- `frontend/panel_admin/src/app/features/agenda/agenda.component.html:55-59` — las ausencias se muestran como texto sin acción.
- `backend/modules/agenda/models.py:18-25` — `Shift` es **un día de la semana** (`day`, 0-6) con `valid_from`/`valid_until`: ya es una recurrencia semanal acotada por fechas. Repetir «en el mes» ya está soportado por el modelo; falta la UX.
- `backend/modules/agenda/api.py:95-116` — `ShiftView` crea un turno por llamada (`day` único), valida solapes con `shifts_overlap` bajo bloqueo de `Schedule` y soporta `PUT` por `shift_id`. No hay `DELETE` de turnos.
- `backend/modules/agenda/domain/schedule.py:1-19` — `validate_shift` y `shifts_overlap` (misma lógica de dominio, sin Django).
- `agenda.component.ts:28-32,128-133` — formulario con `day` numérico; por defecto vigencia = semana visible.
- `backend/modules/agenda/application/week.py:7-27` y `appointments.py:52-61` — la disponibilidad (turno − pausas − ausencias) alimenta los huecos libres de citas; editar/borrar ausencias cambia la oferta de citas.
- No existe `agenda.component.spec.ts`; el servicio sí tiene spec (`agenda-api.service.spec.ts`).
- `docs/design/DDR-configurar-horarios-y-disponibilidad-vista-semanal.md` y `docs/adr/ADR-configurar-horarios-y-disponibilidad-limites-y-tiempo.md` — decisiones previas vigentes (zona `America/La_Paz`, bloqueo por profesional, vista de 7 grupos por día).
- `docs/design/design-system.md` sección 3 (botones: una acción principal por pantalla, `btn-light` para cancelar) y sección 5 (diálogos con `NgbModal`; la pantalla actual usa `<dialog>` nativo — se conserva).

### Hipótesis / supuestos no confirmados
- Las ausencias no están referenciadas por otra tabla; eliminarlas es seguro (borrado físico). Verificado: solo `Absence.schedule`.
- Ni crear ni editar turnos/ausencias comprueba hoy citas existentes; se mantiene (fuera de alcance).

### Módulos y dependencias relacionadas
`agenda` (backend y frontend), `personnel` (selector de profesionales). Sin cambios en otros módulos.

### Implementaciones similares existentes
Edición de turnos (`ShiftView.put` + `edit()` en el componente); diálogos de `agenda.component.html`.

### Comportamiento actual
Ver Hechos. Un turno por día por envío; ausencias solo se crean.

### Restricciones
CLAUDE.md: aislamiento por `company_id`, dominio sin Django, textos solo por i18n (es/en/pt con las mismas claves), sin dependencias nuevas, sin editar migraciones aplicadas (no se necesitan migraciones).

### Riesgos identificados
- Alta masiva parcial: debe ser atómica (todo o nada).
- Editar/borrar ausencias libera disponibilidad y puede dejar visible un hueco que antes estaba bloqueado.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a un módulo, contrato API aditivo y sin decisión arquitectónica nueva.

### Diseño requerido
**SI** — cambia el flujo de los dos diálogos y la tarjeta de cada día.

## Diseño
Ver [DDR-mejorar-ux-horarios-y-ausencias-dialogos-y-semana](../design/DDR-mejorar-ux-horarios-y-ausencias-dialogos-y-semana.md).

## Arquitectura
No aplica según veredicto.

## Plan
Ver [PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias](../plans/PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias.md) (v1, COMPLETO).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
