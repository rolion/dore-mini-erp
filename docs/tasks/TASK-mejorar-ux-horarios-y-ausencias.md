# TASK-mejorar-ux-horarios-y-ausencias: Registrar un mismo horario en varios días y editar ausencias

**Etapa actual:** PUBLISH
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
| 2026-11-04 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-04 | REVIEW → ENGINEERING → REVIEW | REV-01..06 corregidos (ciclo 2) | delivery-publish / delivery-build |
| 2026-11-04 | REVIEW → PUBLISH | Quality Gate ciclo 2: PASS | delivery-publish |

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

**Backend** (`backend/modules/agenda/`):
- `api.py`: `ShiftView.post` acepta `days` (AC-01..03, INV-04, EDGE-02); alta atómica con comprobación de solape por día; error indica el día. Nueva `AbsenceDetailView` con `put` y `delete` filtradas por empresa y profesional (AC-04..06). `urls.py`: ruta `absences/<int:absence_id>/`.
- `tests/test_api.py`: pruebas de AC-01..AC-06 y EDGE-02/03/05.

**Frontend** (`features/agenda/`):
- `agenda.component.{ts,html}`: chips de días con atajos, repetición (semana / fin de mes / fecha) con resumen, «Copiar a otros días», ausencia con «Todo el día», edición, eliminación con confirmación en el mismo diálogo, acciones en la cabecera y aviso de éxito descartable (AC-07..AC-11, UI del DDR).
- `models/agenda-dates.ts` (+ spec): funciones puras de fechas (AC-08, AC-10). `services/agenda-api.service.ts`: `createShifts`, `saveAbsence` con PUT, `deleteAbsence`.
- i18n es/en/pt: 29 claves nuevas (AC-12). Pantalla de referencia: la propia pantalla (DDR vigente); botones según sección 3 del sistema de diseño.

**Desviaciones respecto al plan:**
- Los `<dialog>` pasaron fuera del bloque `@if (week)` porque los botones de la cabecera los referencian.
- El aviso de éxito se cierra con un botón «Cerrar»; no desaparece solo.
- El DDR pedía «Eliminar» desde la tarjeta: abre el diálogo de ausencia directamente en la confirmación.

**Verificación propia (no es el Quality Gate):** `npm run lint`, `npm run i18n:check` y `npm run build` pasan; 35 pruebas de `features/agenda` pasan. `npm test` completo: 1264 pruebas pasan (la falla ajena de `screens-i18n.spec.ts` observada antes no se reprodujo). Las pruebas de backend **no se ejecutaron** (el worktree no tiene `DATABASE_URL`); solo se comprobó la sintaxis.

**Deuda técnica:** sin eliminación de turnos; sin aviso de citas existentes al crear/editar turnos o ausencias (ambos fuera de alcance).

## Review
Quality Gate (subagente aislado, ciclo 1): sin Critical/High; 2 Medium y 4 Low. Backend y revisión visual **no ejecutados**. Hallazgos: docs/reviews/REV-2026-11-04-mejorar-ux-horarios-y-ausencias-01..06. Corregidos en el ciclo 2 de build (REV-04 se resolvió como IMPLEMENTATION: AC-08 solo fija `valid_until`, por lo que al editar se conserva `valid_from`). Verificaciones posteriores (ciclo 2): backend `python manage.py test` completo 1391 OK (40 de agenda; un test propio corregido: el error llega como texto, no lista); revisión visual en navegador (escritorio claro/oscuro y móvil 390 px) sin hallazgos funcionales; detalles menores en REV-07 (dos ya corregidos). Quality Gate ciclo 2 (subagente aislado): **PASS**; REV-01..06 resueltos; REV-07 abierto (Low).

## Publicación
PR #58 listo para aprobación humana (no se mergea automáticamente). Sin cambios de arquitectura, autenticación, base de datos ni infraestructura. Limitaciones conocidas en la descripción del PR.
