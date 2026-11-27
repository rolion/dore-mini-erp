# TASK-gestionar-atencion-odontologica-desde-citas: Gestionar atención odontológica desde citas

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-gestionar-atencion-odontologica-desde-citas
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/MI9tzlmQ/24-pb-odo-007-gestionar-atenci%C3%B3n-odontol%C3%B3gica-desde-citas
**Specification readiness:** READY (decisiones de negocio resueltas con el usuario el 2026-11-27, ver Investigación)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado desde tarjeta PB-ODO-007 | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE, diseño requerido; 4 decisiones de negocio respondidas | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | Plan v1 READY y PR abierto | delivery-start |

## Investigación

### Requerimiento
Fuente: tarjeta Trello PB-ODO-007 «Gestionar atención odontológica desde citas» (insumo, no Specification aprobada). Historia: como odontólogo, iniciar, gestionar y finalizar una **atención odontológica (DentalEncounter)** desde una cita, ver el resumen del paciente y registrar opcionalmente odontograma (y recetas), conservando trazabilidad clínica.

Resumen fiel de la tarjeta:
- Atención: cita obligatoria y única; paciente y odontólogo derivados de la cita; cero o una atención por cita, muchas por paciente; cero o un odontograma lógico (con enmiendas); recetas opcionales (cardinalidad propuesta 0..n). Odontograma y receta no se exigen para finalizar. No genera actos, cobros ni tratamientos.
- Estados: Pendiente (derivado, sin atención), En progreso, Finalizada, Cancelada; la reprogramación es evento de Agenda, no estado clínico. Iniciar (cita elegible, crea/recupera la atención única), Finalizar (atómico e idempotente; sincroniza la cita a Atendida; no finalizar silenciosamente borradores), Cancelar (motivo, autor, fecha; conserva datos), Reprogramar solo antes de iniciar, No asistió impide iniciar. «No marcar cita atendida desde Agenda sin definir coexistencia con el flujo clínico».
- UI: Odontología → Citas (ID, paciente, odontólogo, horario, estado administrativo, estado de atención, «Ver cita»; filtros fecha/odontólogo/paciente/estados; por defecto el día); detalle «Atención odontológica» con resumen del paciente (antecedentes y alergias solo clínicos), acciones Iniciar/Finalizar/Cancelar, sección Odontograma (Agregar/Continuar/Ver), sección Recetas solo si existe módulo (si no, sin botón inoperante), observaciones; ficha del paciente conserva el historial de atenciones.
- Backend: unicidad en BD (atención por cita, odontograma por atención), transacciones y concurrencia, validar empresa/paciente/profesional/módulo/permisos, datos clínicos fuera de recepción, migración de odontogramas existentes sin inventar citas.
- AC 1-9 de la tarjeta (listado/detalle; iniciar-finalizar sin odontograma; odontograma único por atención con concurrencia; inicio idempotente y cierre atómico; reprogramar/cancelar/no asistió; dos citas = dos atenciones; referencias inconsistentes y multiempresa; pruebas unit/integración/migración/regresión/Angular/E2E; recetario si existe o contrato documentado).

Decisiones de negocio respondidas por el usuario (2026-11-27):
1. **Autorización:** cualquier usuario con acceso clínico puede iniciar/finalizar/cancelar (política V1 `has_clinical_access`); el profesional se toma de la cita y el autor queda registrado.
2. **Borrador de odontograma al finalizar:** se bloquea con 409; hay que confirmarlo o descartarlo antes.
3. **Cancelar atención en progreso:** se cancelan **ambas** (atención y cita) con **motivo obligatorio**, en una transacción; los datos clínicos se conservan.
4. **Cita «odontológica»:** la cita cuyo cliente tiene perfil odontológico y la empresa tiene el módulo `dentistry` activo; para ellas «Marcar atendida» de Agenda se rechaza y se finaliza por el flujo clínico. Las demás citas no cambian.

### Hechos encontrados
- `backend/modules/agenda/models.py:34-60` — `Appointment` (UUID, `company_id`, `professional_id`, `customer_id`, `customer_name`, `service_*`, `starts/ends`, `status`); `AppointmentEvent` con historial (`kind`, autor, motivo, horario previo). No existe atención ni tipo de cita.
- `backend/modules/agenda/domain/appointment.py:6-13,61-97` — estados `scheduled|confirmed|cancelled|attended|no_show`; `allowed_actions(now)`: `attend`/`no_show` solo si `now >= starts`; transiciones por métodos del agregado.
- `backend/modules/agenda/application/appointments.py:151-205` — `_locked` (bloqueo por `Schedule` + `select_for_update`), `_transition`, `mark_attended`, `cancel`, `reschedule`; todo `@transaction.atomic`.
- `backend/modules/agenda/appointments_api.py:119-196` — API `/api/agenda/appointments/…` (lista con filtros `from,to,professional,status,search`, acciones `confirm|reschedule|cancel|attend|no-show`); `required_modules = ('personnel','agenda','customers','services')`, permiso por defecto de la API (rol admin).
- `backend/modules/agenda/infrastructure/adapters.py` — Agenda usa fachadas de otros módulos; **Agenda no tiene `services.py` público** (otros módulos sí: `personnel/services.py`, `dentistry/services.py`).
- `backend/modules/dentistry/infrastructure/evaluation_models.py:7-46` — `EvaluationModel` (odontograma) **por paciente** (`customer_id`), secuencia, `status draft|confirmed`, `amends` (enmienda), `professional_id`; restricciones `unique(company,customer,sequence)` y **un borrador por paciente**. No tiene vínculo con cita ni atención.
- `backend/modules/dentistry/application/evaluations.py:44-100` — `EvaluationCommands.create/update/discard/confirm/amend` con orden de bloqueos paciente → evaluación.
- `backend/modules/dentistry/api/views.py:46-52,114-121` — `ClinicalView` (`required_modules=('dentistry','customers')`, `CompanyClinicalPermission`), historial del paciente (`PatientHistoryView`).
- `backend/config/permissions.py:36-40` y `backend/modules/accounts/api/permissions.py:6-8` — `has_clinical_access` = rol admin (V1); `backend/modules/accounts/models.py:46-47` — único rol `admin`. No existe rol «recepción» hoy; el aislamiento clínico se prueba con usuarios sin acceso clínico/otra empresa.
- `backend/modules/personnel/domain/profiles.py:54` — `Professional.user_id` opcional (vínculo profesional ↔ usuario, no usado para autorizar en V1).
- `backend/modules/dentistry/api/urls.py:11-30` — rutas `/api/dentistry/…` (pacientes, evaluaciones, proformas, `capabilities/`).
- `frontend/panel_admin/src/app/features/agenda/models/appointment.ts:3-60` — modelo y etiquetas de estado de cita; `appointment-detail.component.html:33` — botón «Marcar atendida» (`can('attend')`).
- `frontend/panel_admin/src/app/features/dentistry/dentistry.routes.ts:25-40` — rutas `/pocketbiz/dentistry/*` con `clinicalGuard`; `pages/odontogram.component.ts:39-45` — pantalla de odontograma por paciente (`patients/:id/odontogram`).
- `frontend/panel_admin/src/app/layout/sidebar/menu-layout.ts:28-34` — orden del menú de odontología; Odontología tiene subítems (Pacientes, Presupuestos anidados).
- Recetas: búsqueda de `receta|prescription` en backend y frontend sin resultados → **no existe recetario** (la tarjeta pide documentar el contrato y no bloquear).
- `docs/tasks/TASK-registrar-diagnostico-odontograma-inicial.md` — PB-ODO-002 ya está mergeado en `main` (PR #136); base de este trabajo.
- Patrón de referencia: `docs/adr/ADR-agendar-y-gestionar-citas-modelo-concurrencia-e-integracion.md` (concurrencia por `Schedule`, fachadas).

### Hipótesis / supuestos no confirmados
- Iniciar exige que la cita permita `attend` (hora de inicio alcanzada), porque finalizar sincroniza con `mark_attended`; si el negocio quisiera iniciar antes de la hora, habría que cambiar la regla de Agenda (fuera de alcance).
- «Antecedentes y alergias autorizados» = campos de `PatientModel` ya visibles solo bajo `CompanyClinicalPermission`.
- La edad no existe en el perfil del paciente → no se muestra si no hay fecha de nacimiento (a verificar en el cliente/ficha en la implementación).

### Módulos y dependencias relacionadas
`dentistry` (nuevo agregado), `agenda` (citas; nueva fachada y puerto de guardas), `customers` (contacto, vía fachada ya usada), `personnel` (nombres de profesional). Dependencias de Trello: PB-AGE-002 y PB-ODO-002 ya en `main`; PB-ODO-003/004 consumirán el contrato de atención.

### Implementaciones similares existentes
Evaluaciones (`EvaluationCommands`, bloqueo y enmiendas), citas (`_transition`), proformas (`dentistry/services.py` como fachada pública), plantilla de detalle con acciones y diálogo con motivo en `design-system.md` (§5).

### Comportamiento actual
Hoy una cita se marca atendida solo desde Agenda y no deja registro clínico; los odontogramas cuelgan del paciente y no de una cita.

### Restricciones
CLAUDE.md: `company_id` en toda consulta; módulos no importan infraestructura entre sí (solo fachadas); estados por métodos del agregado; migraciones nuevas, nunca editar aplicadas; sin texto hardcodeado (i18n es/en/pt); no instalar dependencias sin avisar.

### Riesgos identificados
- Ciclo de dependencia agenda ↔ dentistry (resuelto en ADR con un puerto de guardas en Agenda).
- Cambio de Agenda sobre citas dentales existentes: el bloqueo de «atendida» altera el flujo actual de empresas odontológicas (aceptado por el usuario).
- Un borrador de odontograma de una atención cancelada seguirá siendo el borrador único del paciente (regla de PB-ODO-002) hasta confirmarse o descartarse.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo agregado clínico, migración sobre odontogramas existentes, cambios coordinados en dos módulos (Agenda y Odontología), concurrencia y atomicidad entre estados, permisos clínicos y contrato API nuevo.

### Diseño requerido
**SI** — pantallas nuevas (listado clínico de citas y detalle de atención) con acciones de ciclo de vida y diálogos con motivo.

## Diseño
Ver `docs/design/DDR-gestionar-atencion-odontologica-desde-citas-listado-y-detalle-de-atencion.md`.

## Arquitectura
Ver `docs/adr/ADR-gestionar-atencion-odontologica-desde-citas-modelo-integracion-agenda-y-odontograma.md`.

## Plan
`docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md` (v1, COMPLETO).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
