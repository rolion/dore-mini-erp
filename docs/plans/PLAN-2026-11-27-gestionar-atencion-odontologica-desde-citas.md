# PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas (v4)

**Task:** TASK-gestionar-atencion-odontologica-desde-citas · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-gestionar-atencion-odontologica-desde-citas-listado-y-detalle-de-atencion · ADR-gestionar-atencion-odontologica-desde-citas-modelo-integracion-agenda-y-odontograma · ADR-gestionar-atencion-odontologica-desde-citas-numeracion-de-citas-por-gestion

## Objective
Permitir iniciar, gestionar, finalizar o cancelar una atención odontológica (DentalEncounter) desde una cita de Agenda, con resumen del paciente y odontograma opcional, manteniendo cita y atención consistentes (atómico, idempotente, concurrente) y trazabilidad clínica.

## Context
Ver TASK. Base: PB-AGE-002 (citas) y PB-ODO-002 (odontograma) ya en `main`.

# Specification

## Domain context
Bounded context **Odontología** (agregado nuevo) con dependencia de **Agenda** (citas), **Clientes** (paciente = cliente) y **Personal** (profesional) siempre por fachadas.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Atención (DentalEncounter) | Encuentro clínico ligado a una cita; una por cita | Tarjeta PB-ODO-007 |
| Estado de cita | Estado administrativo de Agenda (`scheduled…no_show`) | `agenda/domain/appointment.py:6-10` |
| Estado de atención | `pending` (derivado: cita sin atención), `in_progress`, `finished`, `cancelled` | Tarjeta; ADR |
| Cita odontológica | Cita cuyo cliente tiene perfil odontológico, con módulo `dentistry` activo | Decisión del usuario 4 |
| Odontograma lógico | Evaluación raíz (sin `amends`) de una atención; sus enmiendas lo conservan | PB-ODO-002 |

## Current behavior
Citas se marcan atendidas solo desde Agenda sin registro clínico (`agenda/application/appointments.py:177-181`); odontogramas por paciente sin atención (`dentistry/infrastructure/evaluation_models.py:7-46`).

## Expected behavior
Una cita odontológica se atiende desde Odontología → Citas: iniciar crea o recupera la atención única; finalizar la cierra y deja la cita Atendida en la misma transacción; cancelar (con motivo) cancela atención y cita; todo con permisos clínicos y aislamiento por empresa.

## Domain rules / invariants
- **INV-01** (nueva) Una atención por cita (`unique(company_id, appointment_id)`).
- **INV-02** `customer_id` y `professional_id` de la atención son los de la cita al iniciar y no cambian.
- **INV-03** `finish`/`cancel` solo desde `in_progress`; `finished` y `cancelled` terminales; repetir `finish` sobre una finalizada es idempotente (mismo resultado, sin efectos).
- **INV-04** Finalizar con odontograma en borrador → 409 `draft_pending`; nunca se confirma ni descarta en silencio. No se exige odontograma ni receta.
- **INV-05** Cancelar atención exige motivo (1-500), autor y fecha; cancela también la cita con ese motivo en la misma transacción; los datos clínicos (odontograma, observaciones) se conservan.
- **INV-06** Un odontograma lógico por atención (`unique(encounter)` entre evaluaciones raíz); las enmiendas heredan la atención y conservan el original; se crea solo con la atención `in_progress`.
- **INV-07** Iniciar solo si la cita admite `attend` (estado `scheduled|confirmed` y hora de inicio alcanzada), el paciente tiene perfil activo y cliente activo, y la empresa tiene los módulos requeridos. Cita `cancelled`/`no_show`/`attended` → no se inicia (409).
- **INV-08** Citas con atención: Agenda rechaza `reschedule`, `cancel`, `no_show` (409 `encounter_started`); citas odontológicas: Agenda rechaza `attend` (409 `clinical_flow_required`). Citas no odontológicas: comportamiento actual intacto.
- **INV-09** Reprogramar antes de iniciar conserva la cita y su historial; la atención (no existente) sigue «pendiente».
- **INV-10** Las evaluaciones existentes quedan con `encounter = NULL` (legado consultable); no se crean citas ni atenciones en la migración.

## Acceptance criteria
- **AC-01** Odontología → Citas lista las citas existentes (de pacientes con perfil odontológico) sin duplicar Agenda, con filtros fecha/odontólogo/paciente/estado de cita/estado de atención (por defecto, hoy); el detalle muestra paciente y profesional correctos. (Trello 1)
- **AC-02** Iniciar y finalizar sin odontograma ni recetas es válido; la cita queda Atendida y la atención Finalizada, con inicio y fin reales. (Trello 2)
- **AC-03** Crear odontograma desde la atención precarga paciente, profesional y fecha; un segundo odontograma lógico se rechaza también bajo concurrencia; las enmiendas conservan el original. (Trello 3)
- **AC-04** Reintento o inicio simultáneo no duplica la atención; finalizar es idempotente; si el cierre falla, no cambia ni la atención ni la cita. (Trello 4)
- **AC-05** Reprogramar antes de iniciar conserva historial; cancelada o no asistió impide iniciar; cancelar una atención en progreso exige motivo, cancela atención y cita y conserva los datos clínicos. (Trello 5 + decisión 3)
- **AC-06** Dos citas del mismo paciente generan atenciones independientes, consultables en su historial (ficha del paciente). (Trello 6)
- **AC-07** Se rechazan referencias inconsistentes (cita/atención/evaluación de otra empresa, odontograma de otro paciente), módulos deshabilitados y usuarios sin acceso clínico; los antecedentes/alergias no se exponen sin acceso clínico. (Trello 7)
- **AC-08** Agenda no marca «atendida» una cita odontológica (409) y no permite reprogramar/cancelar/no asistió con atención iniciada; las citas no odontológicas siguen igual (regresión). (Trello «coexistencia» + decisión 4)
- **AC-09** Finalizar con odontograma en borrador responde 409 y no cambia nada. (decisión 2)
- **AC-10** Cualquier usuario con acceso clínico de la empresa puede iniciar/finalizar/cancelar; el autor queda registrado. (decisión 1)
- **AC-11** Recetario: no existe; el DTO expone `prescriptions_enabled: false`, la UI no muestra sección ni botón, y el contrato futuro queda documentado en el ADR. (Trello 9)
- **AC-12** Migración: evaluaciones previas conservan datos con `encounter = NULL` y siguen consultables. (Trello 8)

- **INV-11** (nueva, v4) Cada cita creada recibe un número correlativo `C-000001` único por (empresa, gestión fiscal); la gestión es la de la **fecha de creación** (America/La_Paz); el número no cambia al reprogramar o cancelar y no se reutiliza. Sin gestión abierta para esa fecha la creación se bloquea (409 `fiscal_period_missing` / `fiscal_period_closed`) sin crear la cita ni avanzar el contador. Las citas existentes se numeran por orden de creación (migración repetible); las que caen fuera de toda gestión quedan sin número.

## Edge cases / Error cases
- Doble clic / peticiones simultáneas de iniciar, finalizar o crear odontograma → un solo resultado; sin doble envío en la UI.
- Cita futura (antes de su hora): no se puede iniciar (mensaje claro).
- Paciente archivado o cliente inactivo: no se inicia (409).
- Cancelar con motivo vacío o >500 → 400 con código estable.
- Atención finalizada: odontograma y observaciones de solo lectura salvo enmienda de PB-ODO-002.
- Borrador de una atención cancelada: sigue siendo el borrador del paciente (editable/descartable desde su ficha).

- **AC-13** (nuevo, v4) Las citas se identifican con un código `C-` + 6 dígitos, correlativo y único en cada gestión fiscal; la serie reinicia en cada gestión; Odontología → Citas muestra la columna «Cita» (antes «ID de cita») con el código y la gestión; Agenda lo muestra en su listado y detalle.
- **AC-14** (nuevo, v4) Crear una cita sin gestión fiscal abierta responde 409 con un código estable y un aviso traducido; no se crea la cita ni se consume número; las citas anteriores se numeran por orden de creación sin perder datos (migración repetible).

## Authorization / permissions
`CompanyClinicalPermission` en todos los endpoints nuevos; `required_modules = ('dentistry','agenda','customers','personnel')`; empresa siempre desde el usuario autenticado; el cliente nunca envía `company_id`, paciente ni profesional (derivados de la cita).

## API contract
- **API-01** `GET /api/dentistry/appointments/?from&to&professional&customer&search&status&encounter_status&page&page_size` → `{count, next:null, previous:null, results, from, to}`; cada ítem es plano: `appointment_id, customer_id, customer_name, professional_id, professional_name, service_name, starts, ends, status, encounter_id|null, encounter_status` (`pending|in_progress|finished|cancelled`). Rango ≤ 31 días; el costo depende del rango (se parte de las citas del rango).
- **API-02** `GET /api/dentistry/appointments/<id>/encounter/` → detalle: cita, atención (o `null`), resumen del paciente (nombre, edad opcional, contacto, antecedentes, alergias), odontograma vinculado (resumen), `allowed_actions` (`start|finish|cancel`), `prescriptions_enabled:false`.
- **API-03** `POST …/encounter/start/` (200 si ya en progreso; 201 al crear; 409 no elegible), `POST …/encounter/finish/` (200, idempotente; 409 `draft_pending`), `POST …/encounter/cancel/` `{reason}` (200; 400 motivo; 409 estado).
- **API-04** `PATCH /api/dentistry/encounters/<id>/` `{observations}` (≤2000, solo `in_progress`).
- **API-05** `POST /api/dentistry/encounters/<id>/odontogram/` crea el borrador precargado (201); 409 si ya existe odontograma lógico o la atención no está en progreso.
- **API-06** `GET /api/dentistry/patients/<customer_id>/encounters/` historial paginado.
- **API-08** (nuevo, v4) Agenda y Odontología devuelven `code` (`C-000001` o `null`) y `fiscal_period_name` en listado y detalle de citas (`appointment_code` en el historial del paciente); `POST /api/agenda/appointments/` puede responder 409 `fiscal_period_missing` / `fiscal_period_closed`. Cambio compatible hacia atrás.
- **API-07** Agenda: las acciones existentes pueden responder 409 `clinical_flow_required` / `encounter_started`; el resto del contrato no cambia (compatible hacia atrás). El detalle de cita **no** añade campos clínicos: el frontend de Agenda consulta `GET /api/dentistry/appointments/<id>/encounter/` (UI-08) solo con el módulo `dentistry` habilitado y acceso clínico.
- Los errores usan `{detail, code}` estable para traducir.

## UI behavior
Según DDR: **UI-01** listado clínico (plantilla lista de solo lectura con filtros; compacta < `lg`); **UI-02** detalle «Atención odontológica» en dos columnas (≥ `lg`) con badges «Cita: …» / «Atención: …», franja de alerta clínica (**UI-10**: alergias, antecedentes médicos y medicación en `alert-warning`), «Finalizar» como acción principal junto a las observaciones y «Cancelar» como acción secundaria separada; acciones por `allowed_actions`; **UI-03** diálogo de cancelación con motivo; **UI-04** sección Odontograma («Odontograma de esta atención · versión N», número del paciente como texto secundario; Agregar/Continuar/Ver; reutiliza la pantalla existente); **UI-05** observaciones con un solo envío (texto de solo lectura con «Sin observaciones» al cerrar la atención); **UI-06** sin sección de recetas hoy; **UI-07** ficha del paciente → sección «Atenciones»; **UI-08** Agenda: aviso y enlace en lugar de «Marcar atendida» para citas odontológicas; **UI-09** subítem de menú «Citas» en Odontología. Estados cargando/vacío/error/éxito en todas.

## Non-functional requirements
i18n es/en/pt sin texto hardcodeado (`npm run i18n:check`); sin consultas N+1 en el listado; lint (`ruff`, `flake8`) limpio en lo cambiado.

## Out of scope
Recetas, cobros/actos/tratamientos automáticos, proformas, inventario, cambios de reglas de citas no odontológicas, nuevo rol «recepción», edición de profesional/paciente de una cita, PB-ODO-003/004.

## Open questions
Edad del paciente (si el cliente guarda fecha de nacimiento): se muestra solo si existe; no bloquea.

# Test Specification

## Unit tests
- Dominio `DentalEncounter`: transiciones válidas/ inválidas, idempotencia de `finish`, motivo obligatorio (INV-03, INV-05).
- Guardas de Agenda: citas odontológicas vs no odontológicas, con y sin atención (INV-08).

## Integration tests
- API: iniciar (201/200 idempotente/409), finalizar (cita Atendida, 409 borrador), cancelar (ambas canceladas, motivo), observaciones, historial, listado y filtros, odontograma desde atención (precarga, segundo rechazado, enmienda conserva), aislamiento por empresa/módulo/permiso, atomicidad (forzar fallo en `mark_attended_by_clinic` y verificar que nada cambia), concurrencia con hilos sobre `TransactionTestCase` (inicio y creación de odontograma simultáneos).
- Migración: evaluaciones previas intactas con `encounter = NULL`.

## E2E (¿corresponde? SÍ)
Flujo crítico de punta a punta listado → detalle → iniciar → odontograma opcional → finalizar (exigido por AC 8 de la tarjeta). Si el repositorio no tiene arnés E2E, se cubre con una prueba de componente de flujo completo en Angular y se informa; **instalar Playwright u otra dependencia requiere confirmación previa** (ver New dependencies).

## Regression tests
Suites existentes de `agenda` (citas, API) y `dentistry` (evaluaciones, pacientes, proformas) deben pasar sin cambios; añadir caso: cita no odontológica sigue marcándose atendida desde Agenda.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API listado/filtros/aislamiento; componente lista; E2E |
| AC-02 | API inicio+fin sin odontograma; E2E |
| AC-03 | API odontograma desde atención; concurrencia; enmienda |
| AC-04 | API idempotencia; prueba de atomicidad; concurrencia |
| AC-05 | API cancelar/no asistió/reprogramar; dominio |
| AC-06 | API historial con dos citas; componente ficha |
| AC-07 | API multiempresa, módulo, permiso, referencias cruzadas |
| AC-08 | Pruebas de guardas + regresión de Agenda |
| AC-09 | API finalizar con borrador |
| AC-10 | API con usuario clínico; autor registrado |
| AC-11 | API `prescriptions_enabled`; componente sin sección |
| AC-12 | Prueba de migración |
| AC-13 | `test_appointments.py` (correlativo, reinicio por gestión, reprogramar/cancelar conservan, concurrencia); `test_encounter_api`; specs de listado Odontología, detalle y Agenda |
| AC-14 | `test_appointments.py` (409 sin/ con gestión cerrada, sin rastro), prueba del backfill repetible |

# Implementation Plan

## Architecture considerations
Ver ADR: agregado en `dentistry`, fachada + puerto de guardas en `agenda`, bloqueo cita → atención, restricciones únicas en BD.

## Proposed solution
Dominio puro `domain/encounter.py`; `application/encounters.py` (comandos/consultas); repositorio y modelo; vistas DRF en `api/encounter_views.py`; guardas registradas en `apps.ready()`; fachada `agenda/services.py`; frontend en `features/dentistry` con servicio API, listado, detalle, diálogo de cancelación y sección en la ficha; ajustes mínimos en Agenda (aviso/enlace) y menú.

## Files/components affected
- Backend nuevo: `dentistry/domain/encounter.py`, `application/encounters.py`, `infrastructure/encounter_models.py`, `encounter_repository.py`, `api/encounter_views.py` (+ rutas), `dentistry/apps.py`, `agenda/services.py`, `agenda/application/guards.py`; cambios: `agenda/appointments_api.py` y `application/appointments.py` (guardas), `dentistry/infrastructure/evaluation_models.py` (columna `encounter`), `application/evaluations.py` (vínculo).
- Frontend: `features/dentistry/{models,services,pages,components}` (atención, listado, diálogo, historial en la ficha), `dentistry.routes.ts`, `pages/odontogram.component.ts` (`?encounter=`), `features/agenda/pages/appointment-detail.*` (aviso/enlace), `layout/sidebar` (subítem), i18n `assets/i18n/{es,en,pt}.json`.
- Tests: `backend/modules/dentistry/tests/test_encounter_*.py`, `agenda/tests/` (guardas), specs Angular.
- Docs: TASK/PLAN/DDR/ADR (este PR).

## Implementation steps
1. Dominio `DentalEncounter` + pruebas unitarias (INV-03, INV-05).
2. Modelo, migración (tabla + columna `encounter` nullable + constraints) y prueba de migración (INV-01, INV-06, INV-10 · AC-12).
3. Fachada `agenda/services.py` (lectura, búsqueda, `lock`, `mark_attended_by_clinic`, `cancel_by_clinic`) y puerto de guardas; pruebas (INV-08 · AC-08).
4. Comandos/consultas de atención y vistas: iniciar, finalizar, cancelar, observaciones, detalle, listado, historial (AC-01, 02, 04, 05, 06, 09, 10).
5. Odontograma desde atención y vínculo en `EvaluationCommands` (AC-03).
6. Permisos, módulos y aislamiento + pruebas (AC-07); `prescriptions_enabled` (AC-11).
7. Frontend: servicio API, modelos, listado (UI-01), detalle (UI-02..06), diálogo, ficha (UI-07), Agenda (UI-08), menú (UI-09), i18n en las tres lenguas.
8. Pruebas de componentes y flujo E2E (ver abajo); `npm run lint`, `npm run i18n:check`, `npm test`, `python manage.py test`, `ruff`/`flake8` sobre lo cambiado.

## Database / migrations
Nueva migración `dentistry/0006_dental_encounters` (tabla y columna aditivas); no se edita ninguna migración aplicada; sin migración de datos.

## Risks
Ciclo agenda↔dentistry (mitigado con el puerto); concurrencia (orden de bloqueo fijo + restricciones únicas); regresión de Agenda (suite existente + caso nuevo); listados con filtro por estado de atención (rango acotado a 31 días).

## New dependencies
Ninguna obligatoria. E2E con Playwright **requeriría instalarlo: se pedirá confirmación antes**; hasta entonces el flujo se cubre con prueba de componente de extremo a extremo en Karma.

## Changelog
- **v2** (2026-11-27): [Implementation Plan] Alineado con lo implementado y con los hallazgos REV-01..07 del Quality Gate: API-01 plana, API-07 sin campo `clinical`, listado acotado por rango, `amend` bloquea la atención antes que al paciente, confirmación al finalizar guardando observaciones, tarjeta/submenú condicionados al módulo Agenda. E2E real (Playwright) sigue **pendiente de decisión del usuario** (sin instalar); AC-12 se verifica por estado posterior a la migración (aditiva, nullable), sin `MigrationExecutor`. Solicitado por delivery-publish (REV-07). Sin cambio de Specification.
- **v3** (2026-11-27): [Specification] UI-02, UI-04, UI-05 y nuevo UI-10 (franja de alerta clínica) modificados tras la crítica de diseño, **con aprobación explícita del usuario en el chat** (pidió aplicar las recomendaciones 1-5); DDR revisado (v2). Incluye contraste AA, objetivos táctiles de 44 px, «Sin registrar» y estados vacíos. Sin cambios de AC ni de backend. [Implementation Plan] Los badges de estado usan las clases `*-subtle`/`*-emphasis` de Bootstrap en listado, detalle e historial.
- **v4** (2026-11-27): [Specification] Nuevos INV-11, AC-13, AC-14 y API-08 (numeración correlativa de citas `C-000001` por gestión fiscal y columna «Cita» en Odontología → Citas), **con aprobación explícita del usuario en el chat** (pidió el cambio y respondió las tres decisiones: gestión por fecha de creación, bloqueo sin gestión, numerar las citas existentes). [Implementation Plan] ADR nuevo `…-numeracion-de-citas-por-gestion`; migraciones `agenda/0004` y `0005`; dependencia `agenda → accounting` por fachada (ajuste de `test_boundaries`); contador por empresa y período; sin cambios en el flujo de atención.
