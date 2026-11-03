# TASK-agendar-y-gestionar-citas: PB-AGE-002 · Agendar y gestionar citas de pacientes

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-agendar-y-gestionar-citas
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/wXPEdZkA/4-pb-age-002-agendar-y-gestionar-citas-de-pacientes

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-03 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello | delivery-start |
| 2026-11-03 | INVESTIGATION → DESIGN | Nuevas pantallas de citas | delivery-start |
| 2026-11-03 | DESIGN → ARCHITECTURE | Agenda consume Clientes, Servicios y Personal; concurrencia; migración | delivery-start |
| 2026-11-03 | ARCHITECTURE → PLANNING | Decisiones registradas en ADR/DDR | delivery-start |
| 2026-11-03 | PLANNING → ENGINEERING | Specification READY | delivery-start |

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
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
