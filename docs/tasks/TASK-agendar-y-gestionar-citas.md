# TASK-agendar-y-gestionar-citas: PB-AGE-002 · Agendar y gestionar citas de pacientes

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-agendar-y-gestionar-citas
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/50
**Fuente:** https://trello.com/c/wXPEdZkA/4-pb-age-002-agendar-y-gestionar-citas-de-pacientes

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-03 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello | delivery-start |
| 2026-11-03 | INVESTIGATION → DESIGN | Nuevas pantallas de citas | delivery-start |
| 2026-11-03 | DESIGN → ARCHITECTURE | Agenda consume Clientes, Servicios y Personal; concurrencia; migración | delivery-start |
| 2026-11-03 | ARCHITECTURE → PLANNING | Decisiones registradas en ADR/DDR | delivery-start |
| 2026-11-03 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-11-03 | ENGINEERING → REVIEW | Implementación publicada; pruebas de API pendientes de PostgreSQL | delivery-build |
| 2026-11-03 | REVIEW (sin cambio) | Quality Gate sin PASS: AC-02 no verificable sin PostgreSQL; REV-01 (Medium) y REV-02..07 (Low) abiertos | delivery-publish |
| 2026-11-03 | REVIEW (sin cambio) | REV-01 corregido por indicación de la persona; AC-02 sigue pendiente de PostgreSQL | delivery-build |
| 2026-11-03 | REVIEW (sin cambio) | REV-02..07 corregidos; AC-02 verificado en PostgreSQL (.env local copiado a petición de la persona) | delivery-build |
| 2026-11-03 | REVIEW → PUBLISH | Segundo Quality Gate: PASS con REV-08 (Medium), REV-09 y REV-10 (Low) como limitaciones conocidas | delivery-publish |
| 2026-11-03 | PUBLISH → REVIEW | REV-08, REV-09 y REV-10 corregidos por indicación de la persona; pendiente reverificar REV-08 en navegador | delivery-build |
| 2026-11-04 | REVIEW → PUBLISH | Tercer Quality Gate: PASS con REV-11 y REV-12 (Low) como limitaciones conocidas | delivery-publish |
| 2026-11-04 | PUBLISH (sin cambio) | Merge de main (idiomas es/en/pt): conflictos en los catálogos y pantallas de Citas pasadas a claves de traducción | delivery-build |
| 2026-11-04 | PUBLISH (sin cambio) | Cuarto Quality Gate tras el merge con main: PASS con REV-11, REV-12 y REV-13 (Low) como limitaciones conocidas | delivery-publish |
| 2026-11-04 | PUBLISH → REVIEW | REV-11 y REV-13 corregidos por indicación de la persona; REV-12 se deja abierto por decisión de la persona | delivery-build |
| 2026-11-04 | REVIEW → PUBLISH | Quinto Quality Gate: PASS con REV-12 (abierto por decisión de la persona) y REV-14 (Low) como limitaciones conocidas | delivery-publish |

## Investigación

### Requerimiento
Fuente: tarjeta de Trello PB-AGE-002 (insumo, no Specification aprobada). Los dos documentos de Google enlazados en la tarjeta no son accesibles (401); el análisis se basa solo en la tarjeta.

Historia: como recepcionista, crear y gestionar citas de clientes y pacientes. Menú Agenda → Citas: calendario diario/semanal y listado; crear desde franja libre, formulario, detalle e historial; filtros por fecha, profesional y estado; búsqueda de cliente.
Campos: cliente obligatorio (perfil odontológico no exigido); profesional; servicio activo; inicio; duración positiva editable; fin calculado; notas administrativas opcionales (sin diagnósticos); estado; vínculo opcional a ítem de tratamiento.
Acciones: crear programada; confirmar; reprogramar conservando horario anterior, autor y motivo; cancelar con motivo; marcar atendida / no asistió después del inicio. Programada y confirmada ocupan horario; cancelar libera. Verificar turno, ausencia y conflictos de profesional, también con solicitudes simultáneas. Reprogramar excluye la propia cita y es todo o nada. Atender no registra tratamiento ni pago.
Interfaz: mostrar cliente, servicio, profesional, inicio/fin, estado; confirmar cancelación/reprogramación con resumen; ante conflicto conservar datos y refrescar disponibilidad; la agenda mantiene el evento hasta confirmar el guardado.
Aceptación: dos reservas simultáneas del mismo profesional permiten solo una; 09:00–09:30 y 09:30–10:00 son válidas; cancelada libera el horario y sigue consultable; atendida no genera cobro ni acto clínico.
Límites: un consultorio por empresa; sin sucursales ni reserva de sillón/sala/equipo. Dependencias PB-AGE-001 y PB-SRV-001 (ambas ya en `main`).

### Hechos encontrados
- `backend/modules/agenda/models.py:4-30` — `Schedule` (único por empresa+profesional), `Shift`, `Absence`; sin modelo de citas.
- `backend/modules/agenda/api.py:73-136` — vistas con `required_modules = ('personnel','agenda')`; escrituras serializadas con `get_or_create` de `Schedule` + `update(company_id=F('company_id'))` dentro de `transaction.atomic` (bloqueo de fila por profesional). Patrón reutilizable para las reservas.
- `backend/modules/agenda/api.py:18` — `ZONE = America/La_Paz`; `application/week.py:6-27` calcula disponibilidad (turnos − pausas − ausencias) por semana; `domain/schedule.py:30-35` `subtract`.
- `docs/adr/ADR-configurar-horarios-y-disponibilidad-limites-y-tiempo.md` — zona única en Agenda, hora civil en turnos, ausencias como instantes; PB-AGE-002 integra reservas.
- `backend/modules/agenda/infrastructure/adapters.py:1-3` — Agenda consume Personal solo por `modules.personnel.services.professional_exists` (`personnel/services.py:25`); no hay lectura de nombre ni estado activo del profesional.
- `backend/modules/customers/services.py:18-31,45-56,70` — fachada con `get_customer_for_sale` (incluye `active`), `get_customers_administrative`, `search_customer_ids`; sin datos clínicos.
- `backend/modules/service_catalog/services.py:12-33` — `get_service` y `get_service_for_new_use` (excluye inactivos, respeta el módulo `services`); DTO con `duration_minutes`, `name`.
- `backend/modules/modularity/domain/modules.py:18-24` — módulos `services`, `agenda` (requiere `personnel`), `customers` (habilitado por defecto).
- `backend/config/permissions.py:21-37` y `modules/accounts/api/permissions.py:8,21` — permiso por defecto: admin de empresa activa + `required_modules`; el único rol es `admin`.
- `backend/modules/dentistry/` — solo `PatientModel`/historial; no existe plan ni ítem de tratamiento (`grep` sin coincidencias).
- `backend/modules/agenda/tests/test_api.py:1-60` — patrón de pruebas con `TransactionTestCase`, `ThreadPoolExecutor` y `Barrier` para concurrencia.
- `frontend/panel_admin/src/app/app.routes.ts:30-34` — ruta `agenda/configuracion/horarios` con `moduleGuard` y `personnelAdminGuard`; `src/assets/data/routes.json` define el menú; `features/agenda/` tiene un único `AgendaComponent` y `AgendaApiService`.
- `frontend/panel_admin/src/app/features/agenda/agenda.component.ts:1-60` — carga de profesionales paginada con `PersonnelApiService`, formularios reactivos, `takeUntilDestroyed`.
- `docs/design/design-system.md` secciones 4 y 5 — plantillas Lista, Formulario, Detalle con pestañas/acciones de ciclo de vida y Diálogo de acción irreversible con motivo.

### Hipótesis / supuestos no confirmados
- «Recepcionista» es un usuario con rol `admin` (no hay otros roles).
- No hay regla de compatibilidad profesional↔servicio en la tarjeta; `Service.specialty_id` no se exige contra especialidades del profesional.
- Crear/reprogramar en el pasado no está prohibido por la tarjeta; el servidor no lo restringe (solo marcar atendida/no asistió exige que el inicio haya pasado).
- Las ausencias/turnos creados después no revisan citas existentes (la tarjeta no lo pide).

### Módulos y dependencias relacionadas
Agenda (nuevo agregado Cita) → Clientes, Servicios, Personal por fachadas públicas; Dentistry no se toca.
### Implementaciones similares existentes
Reservas serializadas por fila de bloqueo (`Schedule`); diálogo con motivo (`receipt-revert-dialog`); lista con filtros en URL (`purchase-list`).
### Comportamiento actual
No existen citas ni endpoints `/api/agenda/appointments/`; solo se pueden consultar turnos, ausencias y disponibilidad semanal.
### Restricciones
Aislamiento por `company_id`; módulos no importan infraestructura ajena; estados por métodos del agregado; sin diagnósticos en notas; migraciones nuevas, sin editar `0001`.
### Riesgos identificados
Concurrencia de reservas; reprogramar atómico; datos de cliente/servicio que cambian después (se guarda snapshot de nombres); vínculo a ítem de tratamiento sin módulo proveedor; clientes sin perfil odontológico.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo agregado con máquina de estados, migración, contrato API nuevo, integración con tres módulos y concurrencia.

### Diseño requerido
**SI** — pantallas nuevas: calendario/listado, formulario, detalle con historial y diálogos de confirmar/reprogramar/cancelar.

## Diseño
Ver `docs/design/DDR-agendar-y-gestionar-citas-pantallas-citas.md`.

## Arquitectura
Ver `docs/adr/ADR-agendar-y-gestionar-citas-modelo-concurrencia-e-integracion.md`.

## Plan
`docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md` (v1, COMPLETO, READY).

## Implementación

Resumen: agregado `Appointment` con historial en Agenda, endpoints `/api/agenda/appointments/` y pantallas Agenda → Citas.

- **Dominio** (`agenda/domain/appointment.py`, INV-01..05): estados, transiciones, solapes semiabiertos, ajuste a un intervalo disponible, motivo obligatorio. 6 pruebas unitarias (`agenda/test_appointment.py`).
- **Persistencia** (`models.py`, migración `0002_appointments`): `Appointment` y `AppointmentEvent`, aditiva.
- **Aplicación** (`application/appointments.py`): bloqueo por `Schedule` (mismo patrón de PB-AGE-001); disponibilidad = turnos − pausas − ausencias; franjas libres; crear, confirmar, reprogramar (todo o nada, excluye la propia), cancelar, atendida / no asistió (AC-01..07). Fachadas de Clientes, Servicios y Personal vía `infrastructure/adapters.py`.
- **API** (`appointments_api.py`): lista con filtros y paginación, detalle con historial y `allowed_actions`, acciones, PATCH de notas, `free-slots` (AC-08). 409 para conflicto o transición inválida.
- **Frontend** (`features/agenda/`): servicio, lista/calendario diario y semanal textual, formulario, detalle con diálogos nativos `<dialog>` (mismo patrón que la configuración de horarios), rutas, menú e i18n (AC-09).

Pantallas de referencia: Lista (variante `purchase-list`), Formulario (`product-form`), Detalle con acciones (`purchase-detail`). Sin componentes compartidos nuevos.

Desviaciones respecto al plan:
- Las acciones usan `<dialog>` nativo y no `NgbModal`, por coherencia con `AgendaComponent` (que migró a diálogos nativos tras el gate de PB-AGE-001).
- La búsqueda por cliente filtra por el snapshot `customer_name` (`icontains`) en lugar de `search_customer_ids`: evita una llamada entre módulos y N+1; el ADR menciona la fachada solo como opción.
- `WeekView` ahora usa `week_records` (extraído a `application/week.py`) para compartir la consulta; sin cambio de comportamiento.

Correcciones tras el primer Quality Gate: REV-01..07 (profesional visible, filtros en la URL, autor legible con migración `0003`, ADR/DDR y design-system actualizados, paginación completa, pruebas de ausencia y specs de lista y formulario). Con el `.env` local copiado a petición de la persona: las pruebas de concurrencia (`test_concurrent_requests_accept_only_one` y `test_concurrent_overlapping_writes_accept_only_one`) pasan en PostgreSQL y `modules.agenda` completo corre en PostgreSQL (32 pruebas correctas); la suite completa del backend en PostgreSQL pasa (1383 pruebas) tras declarar en `modules/sales/tests/test_boundaries.py` que Agenda puede depender de Clientes y Servicios por sus fachadas. Karma de `features/agenda`: 18 correctas; lint limpio.

Deuda técnica / limitaciones: turnos y ausencias editados después no revisan citas existentes; `treatment_item_id` queda reservado sin UI ni validación; sin restricción de fechas pasadas al crear (pregunta abierta del plan).

Verificación propia de ingeniería (no es el Quality Gate): `manage.py check` y `makemigrations --check` sin cambios; 12 pruebas de dominio sin base de datos; 31 pruebas de `modules.agenda` sobre SQLite temporal, todas correctas salvo las dos de concurrencia (`test_concurrent_*`, incluida la de PB-AGE-001), que fallan por bloqueo de tabla de SQLite y **requieren PostgreSQL**. Sin credenciales de PostgreSQL en este entorno: AC-02 no está verificado. Frontend: `ngc` de plantillas, `ng lint` y Karma de `features/agenda` y `layout` (32 pruebas) correctos. Recorrido visual y de teclado en navegador pendiente.

## Review

**Primer Quality Gate: sin PASS (PASS condicionado, no publicable).** Sin Critical ni High. Frontend: lint, `ngc`, build, `npm audit` (0 vulnerabilidades) y Karma completo (1129 correctas; sentencias 86,03 %, ramas 77,64 %). Backend: `check` y `makemigrations --check` limpios; `modules.agenda` 31 pruebas sobre SQLite, solo fallan las dos de concurrencia (bloqueo de tabla de SQLite). **AC-02 (dos reservas simultáneas) no se verificó: requiere PostgreSQL y no hay credenciales en este entorno**; por revisión de código el bloqueo por `Schedule` serializa las escrituras. `bandit`/`ruff` no ejecutados. Revisión visual en navegador no verificada.

Hallazgos: [REV-01](../reviews/REV-2026-11-03-agendar-y-gestionar-citas-01.md) (Medium, IMPLEMENTATION: el profesional no se muestra en listado ni detalle) y REV-02 a REV-07 (Low).

Pendiente de una persona: ejecutar en PostgreSQL `test_concurrent_requests_accept_only_one` y `test_concurrent_overlapping_writes_accept_only_one`, recorrido visual/teclado, y decidir sobre REV-01.

**Segundo Quality Gate: PASS con limitaciones conocidas.** Sin Critical ni High. REV-01 a REV-07 verificados. Backend en PostgreSQL: `check` y `makemigrations --check` limpios, suite completa 1383 correctas, `modules.agenda` 32 correctas en 3 corridas (las dos pruebas de concurrencia estables), `bandit` 0 incidencias. Frontend: lint, `ngc`, build, `npm audit` (0) y Karma completo 1136 correctas (sentencias 85,83 %, ramas 77,57 %). Visual verificada en navegador (listado, calendario, detalle y diálogo de reprogramar, tema claro y oscuro) sobre una base temporal.

Limitaciones conocidas: [REV-08](../reviews/REV-2026-11-03-agendar-y-gestionar-citas-08.md) (Medium, DESIGN: a 390 px el listado y el historial usan `table-responsive` en lugar de tabla apilada y los botones de la cabecera se deforman), [REV-09](../reviews/REV-2026-11-03-agendar-y-gestionar-citas-09.md) (Low: la vista del calendario no va en la URL y con `?page` inexistente «Reintentar» queda atascado) y [REV-10](../reviews/REV-2026-11-03-agendar-y-gestionar-citas-10.md) (Low: la búsqueda de clientes del formulario no cancela respuestas anteriores). No verificados: `ruff` (no instalado ni configurado), recorrido con teclado del formulario y de los diálogos de confirmar, cancelar y atender.

**Tercer Quality Gate: PASS con limitaciones conocidas** (sobre `bf49cdd`). Sin Critical ni High. REV-08, REV-09 y REV-10 verificados; REV-01 a REV-07 sin regresiones. Backend en PostgreSQL: `check` y `makemigrations --check` limpios, suite completa 1383 correctas, `modules.agenda` 32 correctas en 2 corridas (las dos pruebas de concurrencia estables), `bandit` sin incidencias. Frontend: lint, `ngc`, build, `npm audit` (0) y Karma completo 1139 correctas (sentencias 86,15 %, ramas 77,73 %). Visual verificada en navegador a 390 y 1440 px, tema claro y oscuro, sobre una base temporal ya eliminada: listado e historial apilados sin scroll horizontal.

Limitaciones conocidas: [REV-11](../reviews/REV-2026-11-03-agendar-y-gestionar-citas-11.md) (Low: tras el 404 de una página inexistente, el reintento a la página 1 pierde el indicador de carga) y [REV-12](../reviews/REV-2026-11-03-agendar-y-gestionar-citas-12.md) (Low: abrir el calendario borra de la URL los filtros del listado). No verificados: `ruff` (no instalado ni configurado) y el recorrido con teclado del formulario y de los diálogos de confirmar, cancelar y atender.

**Merge con `main` (2026-11-04):** `main` incorporó los idiomas es/en/pt (sin texto fijo en pantallas y sin `de.json`). Hubo conflicto en `es.json`, `en.json` y `de.json`; se tomó el catálogo de `main` y se añadió `AGENDA.CITAS.*` (128 claves) y `MENUITEMS.AGENDA.APPOINTMENTS` en es/en/pt. Las pantallas, el modelo y los mensajes de error de Citas pasaron a `translate` / `tr()` y los specs usan `provideTestTranslations()`. Verificación tras el merge: `npm run i18n:check` (0 faltantes), lint, `ngc`, Karma completo 1173 correctas, backend 1383 correctas en PostgreSQL, `makemigrations --check` sin cambios. Los tres Quality Gates anteriores no cubren el código de traducción: conviene un último gate sobre este commit. Una prueba de `main` (`screens-i18n.spec.ts`, «labels coming from code follow the active language») es intermitente según el orden de ejecución, también ejecutada sola (preexistente, ajena a este task).

**Cuarto Quality Gate (tras el merge con `main` e i18n de Citas): PASS con limitaciones conocidas.** Sin Critical ni High. REV-01 a REV-10 siguen verificados. Backend en PostgreSQL: `check` y `makemigrations --check` limpios, suite completa 1383 correctas, `modules.agenda` 32 correctas (concurrencia incluida), `bandit` sin incidencias. Frontend: `i18n:check` (1486 claves, 0 faltantes), lint, `ngc`, build, `npm audit` (0) y Karma completo 1173 correctas (sentencias 86,34 %, ramas 77,6 %). Las 128 claves `AGENDA.CITAS.*` existen en es/en/pt con los mismos placeholders; sin texto fijo ni claves crudas en pantalla. Visual verificada en es/en/pt sobre una base temporal ya eliminada. La prueba intermitente de `screens-i18n.spec.ts` falla también sobre `origin/main`: preexistente y ajena al task.

Limitaciones conocidas: REV-11 y REV-12 (Low, ver arriba) y [REV-13](../reviews/REV-2026-11-03-agendar-y-gestionar-citas-13.md) (Low: los mensajes de error que llegan del servidor, como el detalle de un 409 o los errores por campo de un 400, se muestran en español aunque la interfaz esté en inglés o portugués). No verificados: `ruff`, recorrido con teclado y pantallas de error del servidor en en/pt.

**Correcciones tras el cuarto gate (2026-11-04):** REV-11 (el reintento tras una página inexistente conserva el indicador de carga) y REV-13 (los errores del servidor se traducen al idioma activo mediante códigos estables `code` / `codes`, claves `AGENDA.CITAS.VAL_*` en es/en/pt) están corregidos y pendientes de reverificación. REV-12 se deja abierto por decisión de la persona. Verificación: `i18n:check` 0 faltantes, lint, `ngc`, Karma 1173 correctas más la prueba intermitente de `main` (`screens-i18n.spec.ts`, preexistente), backend 1384 correctas en PostgreSQL.

**Quinto Quality Gate (sobre `a4c35dd`): PASS con limitaciones conocidas.** Sin Critical ni High. REV-11 y REV-13 verificados; REV-01 a REV-10 siguen verificados. Backend en PostgreSQL: `check` y `makemigrations --check` limpios, suite completa 1384 correctas, `modules.agenda` 33 correctas (concurrencia incluida), `bandit` sin incidencias. Frontend: `i18n:check` (0 faltantes), lint, `ngc`, build, `npm audit` (0) y Karma completo: 1174 correctas en una corrida y 1173 más la prueba intermitente de `main` (`screens-i18n.spec.ts`, preexistente) en otra; cobertura 86,31 % de sentencias y 77,65 % de ramas. Verificado en navegador sobre una base temporal: `?page=99` mantiene «Cargando…» y no muestra el vacío; los errores de alta y reprogramar salen traducidos en inglés y portugués.

Limitaciones conocidas: REV-12 (Low, abierto por decisión de la persona) y [REV-14](../reviews/REV-2026-11-03-agendar-y-gestionar-citas-14.md) (Low: `loadCalendar` no usa el identificador de consulta y, al cambiar de vista con una consulta en vuelo, una respuesta anterior puede pisar `loading`, las filas o el error; no se reprodujo en navegador). No verificados: `ruff`, recorrido con teclado, cancelar con motivo vacío en en/pt y un 409 de transición en vivo (cubiertos solo por pruebas automáticas).

## Publicación
PR #50 listo para aprobación humana; no se mergea. Toca base de datos (migraciones aditivas `0002` y `0003`), tiene un ADR y cambia la prueba de límites entre módulos. Limitaciones conocidas: REV-11, REV-12, `ruff` y teclado sin verificar.
