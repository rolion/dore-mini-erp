# TASK-gestionar-atencion-odontologica-desde-citas: Gestionar atención odontológica desde citas

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-gestionar-atencion-odontologica-desde-citas
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/138
**Fuente:** https://trello.com/c/MI9tzlmQ/24-pb-odo-007-gestionar-atenci%C3%B3n-odontol%C3%B3gica-desde-citas
**Specification readiness:** READY (decisiones de negocio resueltas con el usuario el 2026-11-27, ver Investigación)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-27 | (nuevo) → INVESTIGATION | Task creado desde tarjeta PB-ODO-007 | delivery-start |
| 2026-11-27 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE, diseño requerido; 4 decisiones de negocio respondidas | delivery-start |
| 2026-11-27 | PLANNING → ENGINEERING | Plan v1 READY y PR abierto | delivery-start |
| 2026-11-27 | ENGINEERING → REVIEW | Implementación y pruebas completas | delivery-build |
| 2026-11-27 | REVIEW → PUBLISH | Quality Gate PASS (7 hallazgos Low abiertos) | delivery-publish |
| 2026-11-27 | PUBLISH (sin cambio de etapa) | Rediseño del detalle por crítica de diseño; DDR v2 y PLAN v3 | delivery-build (a pedido del usuario) |
| 2026-11-27 | PUBLISH (re-publicación) | Quality Gate 2.ª pasada PASS (1 hallazgo Low, REV-08) | delivery-publish |
| 2026-11-27 | PUBLISH (re-publicación) | Quality Gate 3.ª pasada PASS (REV-08 confirmado; 1 hallazgo Low, REV-09) | delivery-publish |

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
**Resumen.** Backend: agregado `Encounter` (`dentistry/domain/encounter.py`), tabla `dentistry_encounter` y columna `encounter` en `dentistry_evaluation` (migración `0006_dental_encounters`), comandos/consultas (`application/encounters.py`), vistas y rutas `/api/dentistry/appointments/…`, `encounters/…`, `patients/<id>/encounters/`; fachada `agenda/services.py` y puerto de guardas `agenda/application/guards.py` (las acciones `attend|no_show|cancel|reschedule` de Agenda consultan las guardas; el flujo clínico usa `attend_by_clinic/cancel_by_clinic`). Frontend: listado «Odontología → Citas», detalle «Atención odontológica» (iniciar/finalizar/cancelar con diálogo de motivo, odontograma, observaciones), sección «Atenciones» en la ficha, aviso/enlace en el detalle de cita de Agenda, `?evaluation=&appointment=` en la pantalla de odontograma, subítem de menú e i18n es/en/pt.

**Cobertura.** INV-01/INV-06 constraints de BD (+ prueba de concurrencia); INV-03/05 dominio (`test_encounter_domain.py`); AC-01..AC-12 en `test_encounter_api.py` (23 pruebas, 3 con hilos concurrentes); frontend: specs de servicio, listado, detalle (flujo iniciar → odontograma → finalizar, cancelación con motivo, conflicto de borrador), historial del paciente, y ajustes a specs de menú, odontograma y ficha. Suite completa backend 2625 pruebas (las 2 de fronteras se actualizaron, ver desviaciones), Angular 1956 OK, `ng lint` y `i18n:check` limpios, `ruff`/`flake8` limpios en lo cambiado.

**Desviaciones respecto al plan.**
- API-07: el detalle de cita de Agenda **no** añade el campo `clinical`; el frontend de Agenda consulta `GET /api/dentistry/appointments/<id>/encounter/` solo si el módulo `dentistry` está habilitado y el usuario tiene acceso clínico (ignora 403/404). Evita que Agenda conozca datos clínicos.
- Frontera de módulos: `test_boundaries.py` exige que cada dependencia entre módulos pase por `adapters.py` y `services`; se declaró `dentistry → agenda` en `ALLOWED_DEPENDENCIES` y la guarda y el adaptador de Agenda viven en `dentistry/infrastructure/adapters.py` (no se creó `agenda_guard.py`). Es consecuencia directa del ADR.
- E2E: no se instaló Playwright (requería confirmación); el flujo listado → detalle → iniciar → odontograma → finalizar está cubierto por la prueba de componente `encounter-detail.component.spec.ts` más las pruebas de API de punta a punta. Pendiente de decisión del usuario si exige E2E real.
- AC-12: la prueba de migración se cubre verificando que las evaluaciones creadas sin atención conservan `encounter = NULL` y siguen consultables, y que la migración es aditiva; no hay una prueba con `MigrationExecutor`.
- Pruebas ejecutadas contra un PostgreSQL temporal propio (initdb en carpeta temporal, puerto 5544), no contra la base local del usuario.

**Deuda técnica / notas.**
- El listado compone el filtro por estado de atención con listas de IDs (rango ≤31 días); suficiente para el MVP, a revisar si crece el volumen.
- Un borrador de odontograma de una atención cancelada sigue siendo el borrador único del paciente (regla de PB-ODO-002).
- «Edad» se calcula en el cliente desde `birth_date` si existe.

**UI.** Listado según la plantilla *Lista de solo lectura con filtros* (referencia `inventory/pages/movement-list`, tabla `inventory-table`) y detalle según *Detalle de documento en curso con acciones en la cabecera*; reutiliza badges de Agenda (`STATUS_CLASSES`), el patrón de diálogo `<dialog>` con motivo de Agenda y `fetchAll`/`formatDateTime` de Agenda. Sin componentes nuevos en `shared/`; sin cambios al `design-system.md`.

## Review
**Quality Gate (subagente aislado, 2026-11-27): PASS.** Sin hallazgos Critical/High.
- Backend: suite completa `Ran 2625 tests` OK; `makemigrations --check` sin cambios; `manage.py check` limpio; `ruff`/`flake8` sin avisos propios (solo un E501 preexistente en `test_boundaries.py:34`); `bandit` sin issues.
- Frontend: `ng test` 1956/1956 OK; `ng lint` limpio; `i18n:check` 0 faltantes; `ng build` OK; `npm audit --omit=dev` 0 vulnerabilidades.
- No verificado: revisión visual en navegador (claro/oscuro, 390/1440 px), E2E real con Playwright, prueba de migración con `MigrationExecutor`.
- Hallazgos Low abiertos (no bloquean): REV-01 mensaje/`VAL_*` con paciente archivado al crear odontograma; REV-02 «Finalizar» descarta observaciones sin guardar; REV-03 listado sin acotar conjuntos de IDs; REV-04 carrera `finish` vs enmienda; REV-05 error permanente en «Atenciones» con Agenda/Personal deshabilitados; REV-06 HEX/`select`/spinner en el detalle; REV-07 plan v1 desactualizado (API-01, API-07, E2E, AC-12). Archivos: `docs/reviews/REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-01..07.md`.

**Corrección de hallazgos Low (2026-11-27, delivery-build a pedido del usuario):** REV-01 (`_require_patient` antes de crear odontograma + claves `VAL_*`), REV-02 (diálogo de confirmación; guarda observaciones antes de finalizar), REV-03 (listado parte de las citas del rango; fachada `appointments_in_range`), REV-04 (`amend` bloquea la atención antes que al paciente), REV-05 (tarjeta y submenú condicionados al módulo Agenda), REV-06 (tokens `dark-tokens`, `ng-select`, spinner), REV-07 (PLAN v2). Verificación propia tras los cambios: backend agenda+dentistry 163 OK, boundaries OK, Angular 1959 OK, `ng lint`, `i18n:check` y `ng build` limpios. **El Quality Gate no se repitió sobre estos commits**; los REV quedan marcados Resolved por el autor y deben confirmarse en una nueva pasada de delivery-publish si se desea.

**Rediseño del detalle (2026-11-27, a pedido del usuario tras `/design:design-critique`):** aplicadas las recomendaciones 1-5 (franja de alerta clínica, badges «Cita/Atención» con contraste AA, dos columnas con odontograma protagonista y acciones separadas, accesibilidad de contraste y 44 px, estados vacíos y numeración del odontograma). Documentos: DDR v2 («Revisión v2»), PLAN v3 (Specification UI-02/04/05/10 con aprobación del usuario) y `design-system.md`. Verificación propia: specs del módulo 129 OK, Angular completo 1964 OK, `ng lint`, `i18n:check` y `ng build` limpios. **No verificado visualmente en navegador** ni repetido el Quality Gate.

**Quality Gate, 2.ª pasada (subagente aislado, HEAD 8192417b): PASS.** Backend `Ran 2629 tests` OK; Angular `TOTAL: 1965 SUCCESS`; `ng lint`, `i18n:check` (2719 claves, 0 faltantes; paridad es/en/pt 3299), `ng build`, `makemigrations --check`, `bandit` y `npm audit --omit=dev` limpios; `ruff`/`flake8` solo con el E501 preexistente. REV-01..07 **confirmados Resolved** por el revisor. Hallazgo nuevo **REV-08 (Low, abierto):** `clinical_date()` usa `settings.TIME_ZONE` (UTC en `.env.example`), no America/La_Paz; con UTC, una atención iniciada entre las 20:00 y las 24:00 de La Paz precarga el odontograma con la fecha del día siguiente. Sin pérdida de datos. No verificado: revisión visual en navegador (contraste real, modo oscuro), E2E real, prueba con `MigrationExecutor`.

**REV-08 corregido (2026-11-27):** la fecha clínica del odontograma precargado usa America/La_Paz; prueba nueva (28 de `test_encounter_api` OK, suites agenda+dentistry 165 OK, lint limpio). Resuelto por el autor, sin nueva pasada del Quality Gate.

**Quality Gate, 3.ª pasada (subagente aislado, HEAD 45b2afe8): PASS.** Backend `Ran 2630 tests` OK (la prueba de REV-08 también OK con `TIME_ZONE=UTC` y `America/La_Paz`); Angular `TOTAL: 1965 SUCCESS`; `ng lint`, `i18n:check` (0 faltantes), `ng build`, `makemigrations --check`, `bandit` y `npm audit --omit=dev` limpios; `ruff`/`flake8` solo con el E501 preexistente. REV-08 **confirmado Resolved**. Hallazgo nuevo **REV-09 (Low, abierto):** `test_odontogram_from_encounter_preloads_context_and_is_unique` compara `clinical_date` con `timezone.localdate()` (zona de `TIME_ZONE`) y el código devuelve el día de La Paz; con `TIME_ZONE=UTC` falla entre las 00:00 y las 04:00 UTC (falso rojo intermitente; no es un defecto del código de producción). No verificado: revisión visual en navegador, E2E real, prueba con `MigrationExecutor`.

**REV-09 corregido (2026-11-27):** la prueba compara con la fecha de La Paz; pasa con `TIME_ZONE` UTC, America/La_Paz y Asia/Tokyo. Solo cambia una prueba; sin nueva pasada del Quality Gate. Con esto REV-01..09 están resueltos.

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/138 listo para aprobación humana (no se mergea). Cambio sensible: base de datos (migración 0006 aditiva) y autorización clínica; respaldado por ADR-gestionar-atencion-odontologica-desde-citas-modelo-integracion-agenda-y-odontograma. Pendiente humano: decidir si se exige E2E real (Playwright) y si los REV Low se corrigen ahora o después.
