# PLAN-2026-11-02-registrar-profesionales-y-especialidades (v3)

**Task:** TASK-registrar-profesionales-y-especialidades · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-registrar-profesionales-y-especialidades-pantallas-personal; ADR-registrar-profesionales-y-especialidades-contexto-personal (propuestos).

## Objective
Registrar profesionales y especialidades sin exigir cuentas de acceso, con aislamiento por empresa y módulo Personal independiente. La Specification incorpora la tarjeta actualizada y la respuesta explícita del usuario del 02/11/2026: cada usuario solo puede vincularse a un profesional.

## Context
Ver investigación del TASK. Nuevo bounded context y contrato API; los tres ejes exigen modo COMPLETO. Un consultorio por empresa; sin sucursales, recursos físicos ni dependencia de Agenda.

# Specification

## Domain context
Personal posee profesionales/especialidades. Acceso posee cuentas y permisos. Modularity configura habilitación. Agenda es consumidor futuro.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Profesional | Perfil de quien atiende, con o sin cuenta | PB-PER-001 |
| Especialidad | Clasificación opcional propia de la empresa, nombre y estado | PB-PER-001 actualizada |
| Usuario vinculado | Cuenta opcional; sus permisos no cambian por el vínculo | PB-PER-001 |
| Activo | Disponible para uso futuro en nuevas reservas | PB-PER-001; integración Agenda futura |

## Current behavior
Sin Personal/Agenda (`backend/config/urls.py:9`); admin es el único rol (`backend/modules/accounts/models.py:32`); catálogo de módulos sin Personal (`backend/modules/modularity/domain/modules.py:16`).

## Expected behavior
Listar, buscar, consultar, crear, editar, activar/desactivar profesionales y especialidades. Profesional: nombre obligatorio; identificación, teléfono, correo, matrícula, especialidades y usuario opcionales. Especialidad: nombre y estado. Vincular/desvincular no crea cuentas ni cambia roles. Las operaciones no requieren Agenda ni consultan citas en esta entrega. Retener registros y autoría; no exponer borrado.

## Domain rules / invariants
- INV-01: cada lectura, escritura y referencia pertenece a la empresa de sesión; jamás confiar en company_id del cliente.
- INV-02: perfil profesional y acceso son independientes; preservar autoría tras desactivación o desvinculación.
- INV-03: nombre no vacío; referencias a especialidades/usuarios ajenos se rechazan sin filtrar datos ajenos.
- INV-04: estado cambia mediante operaciones de dominio; no se elimina historial al desactivar.
- INV-05: no crear dependencias ni consultas a Agenda/Sucursales ausentes.

## Acceptance criteria
- AC-01: crear y editar un profesional con solo nombre, sin usuario ni especialidades; validar nombre y contactos suministrados.
- AC-02: crear/editar/consultar especialidades y gestionar su estado; seleccionar especialidades por nombre y conservar asociaciones históricas.
- AC-03: vincular/desvincular un usuario de la empresa sin modificar sus permisos; rechazar usuarios/especialidades ajenos.
- AC-04: listas paginadas con búsqueda por nombre y filtro de estado; profesionales filtran también por especialidad; detalle y edición muestran datos guardados.
- AC-05: activar/desactivar conserva el perfil, asociaciones y autoría; no exige ni consulta Agenda. El criterio de recibir/controlar citas se verifica al implementar Agenda, no mediante citas ficticias aquí.
- AC-06: módulo deshabilitado y usuarios no autorizados no acceden por API ni rutas directas; empresa A no consulta/modifica datos de B.
- AC-07: interfaz sigue DDR, muestra carga/vacío/error/éxito, conserva datos ante errores, impide doble envío y permite teclado.
- AC-08: cada usuario solo puede vincularse a un profesional, incluso si el perfil está inactivo; rechazar duplicados también con concurrencia. Desvincular libera el vínculo. El profesional sigue admitiendo usuario nulo.

## Edge cases / Error cases
Nombre vacío/espacios, correo inválido, ID desconocido/ajeno, múltiples especialidades, listas vacías, errores de red, módulo deshabilitado durante la edición y doble envío. No imponer unicidad de identificación/matrícula/nombre de profesional sin regla de negocio. Un usuario ya vinculado produce 400 con error en user_id y no guarda cambios parciales.

## Authorization / permissions
Reutilizar autorización actual CompanyModulePermission (admin de empresa activa) sin crear roles nuevos. Ocultar funciones administrativas sin permiso; servidor valida cada solicitud. Un usuario vinculado no obtiene permiso adicional.

## API contract
GET/POST `/api/professionals/` y `/api/specialties/`; GET/PATCH `/<uuid>/`; POST `/<uuid>/activate/` y `/deactivate/`. Filtros search, active, specialty_id (solo profesionales), page/page_size (máximo 100). Listas `{count,next,previous,results}`. Profesional: id, name (150), identification (50), phone (30), email (254), registration_number (100), active, user_id (entero o null), specialty_ids (UUID[]), specialties ({id,name,active}[]), created_by/updated_by (IDs históricos), created_at/updated_at. Especialidad: id, name (150), active, autoría y fechas. Nombres/contactos se recortan; campos opcionales ausentes valen vacío y listas vacías. No se impone unicidad de nombres/matrículas. PATCH conserva campos omitidos; `active` solo cambia con acciones. Rechazar campos desconocidos, incluidos company_id/autoría. IDs duplicados de especialidad se normalizan, no crean asociaciones duplicadas. Especialidades inactivas conservan asociaciones y pueden seguir consultándose; no se agrega una restricción funcional no pedida sobre esa asociación.

GET `/api/professionals/users/`: búsqueda/paginación de usuarios de la empresa, autorizada y sujeta al gate Personal; `{id,name}` sin correo ni roles. Incluye usuarios ya vinculados para permitir conservar el vínculo actual; la API de escritura valida unicidad. 201 alta, 200 consulta/edición/acción, 400 validación (incluido user_id ya vinculado), 404 registro ajeno/inexistente, 403 permiso/módulo, autenticación según DRF. No hay DELETE. user_id único no nulo en BD, incluso para profesionales inactivos. Actualizar perfil y asociaciones en una transacción, capturar constraint de usuario duplicado sin perder otros datos. Lista ordenada por nombre/id, sin N+1. Se conservan contratos existentes.

## UI behavior
UI-01: menú Personal → Profesionales/Especialidades y rutas propuestas en DDR; guard de módulo.
UI-02: plantillas Lista/Formulario/Detalle (§5 del sistema de diseño), especialidades por nombre, campos opcionales explícitos.
UI-03: estados §4, accesibilidad §7, clases/tokens existentes; sin sucursales ni calendario/citas ficticias.

## Non-functional requirements
Sin N+1, consultas acotadas y paginadas, dominio independiente de Django, ninguna importación de accounts desde negocio. Ninguna dependencia nueva prevista.

## Out of scope
Agenda/citas/horarios y su control de desactivación hasta integrar Agenda; sucursales y recursos; nómina/honorarios; crear cuentas/roles; clínica; borrado físico.

## Business decision resolved
Usuario: «solo a uno» ante la pregunta usuario–profesional. Se aprueba explícitamente esta regla, no se atribuye aprobación global del resto del diseño. Mantener el permiso admin existente.

# Test Specification

## Unit tests / Integration tests
Dominio: validación de datos, estado, edición y preservación. API con PostgreSQL y dos empresas: CRUD, relaciones, autoría, filtros/paginación, 400/403/404, gate y permiso; regresión de identidad y modularity, test de límites DDD. Cardinalidad y concurrencia del vínculo según AC-08. Angular: API con HttpTestingController, formularios opcionales/errores/doble envío, selector y listas/guard.

## E2E
**NO**: administración CRUD acotada cubierta por integración API y componentes. No hay flujo clínico/financiero/reserva operativo en esta entrega. Inspección visual real a 390/1440 px claro/oscuro durante publicación; no declararla verificada sin ejecutarla.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Dominio + API creación/edición mínima e inválida + formulario Angular |
| AC-02 | Dominio/API especialidades y asociaciones + selector Angular |
| AC-03 | Integración con dos empresas y permisos antes/después; selector |
| AC-04 | Integración búsqueda/filtros/paginación + listas/detalles Angular |
| AC-05 | Integración retención/autoría y operaciones sin Agenda |
| AC-06 | API sin autenticación/empresa/admin/módulo; URL/ID ajeno; guard Angular |
| AC-07 | Tests de componentes y revisión visual/teclado con evidencia |
| AC-08 | Test de vínculo duplicado y solicitudes concurrentes; solo una escritura tiene éxito |

# Implementation Plan

## Architecture considerations / Proposed solution
Aplicar ADR y DDR propuestos. Specification READY tras resolver la única pregunta de negocio pendiente.

## Files/components affected
Backend: nuevo `modules/personnel` (domain/application/infrastructure/api, models/apps/migrations/tests); adaptador de identidad en shared/composición; config urls/settings; modularity catálogo; tests de fronteras. Frontend: feature personnel (models/services/pages), app.routes, menú routes.json y traducciones. Docs: TASK/PLAN/ADR/DDR y mapa DDD.

## Implementation steps
1. Resolver vínculo de usuario; completar contrato, comportamiento de cardinalidad y verificaciones, versionando el plan si cambia la Specification. Marcar READY sin atribuir aprobación no recibida.
2. Crear rama desde origin/main, comitear documentos y abrir el único PR; registrar URL y pasar a ENGINEERING.
3. Dominio y persistencia de profesionales/especialidades con aislamiento y autoría (AC-01/02/05).
4. Puerto/adaptador de usuarios, contrato API y validación de relaciones (AC-03/04/08); registrar módulo/gate/rutas y actualizar límites (AC-06).
5. Implementar pantallas y navegación según DDR, reutilizando referencias (AC-01/02/04/07).
6. Implementar pruebas por AC, actualizar docs; continuar con delivery-publish y Quality Gate independiente según skill.

## Database / migrations
Solo migraciones aditivas generadas con makemigrations; nunca editar aplicadas. Constraint único de user_id no nulo, autoría histórica separada; rollback/retención según ADR.

## Risks
Vínculo duplicado y concurrencia; referencias ajenas; pérdida de autoría; import accounts que viole fronteras; acoplamiento prematuro a Agenda.

## New dependencies
Ninguna prevista; no se instaló ninguna.

## Changelog
- **v2** (2026-11-02): [Specification] AC-08 uno a uno tras respuesta explícita del usuario «solo a uno»; contrato final y readiness READY. [Implementation Plan] constraint único y composición del adaptador de identidad.

- **v2 implementation detail:** Selector de usuarios admite filtro opcional `id` validado y acotado a empresa para mostrar el nombre del usuario actualmente vinculado, aunque no esté en la primera página; no modifica permisos ni cardinalidad. Se reutilizan dependencias existentes mediante junction local; PostgreSQL temporal con colación ICU.

- **v3** (2026-11-02): [Implementation Plan] Inspección visual detecta chip de ng-select ilegible en oscuro. Ampliar archivos afectados a `frontend/panel_admin/src/assets/scss/skins/_dark.scss`, con selector exclusivo de app-personnel-form y token existente $color-font. No cambia Specification ni patrón visual; corrige UI-03/AC-07.

- **v3** (2026-11-02): [Implementation Plan] Conformidad visual: importar table-actions en lista, corregir clases compartidas y habilitar scroll horizontal nativo con mínimos de columna para no truncar nombre/estado en móvil; título con table-title existente. DDR aclara comportamiento responsive sin alterar alcance.

- **v3** (2026-11-02): [Implementation Plan] Observar el ancho real del contenedor con ResizeObserver y recalcular ngx-datatable cuando termina la animación del sidebar; evita un viewport residual de 11 px al cruzar breakpoints. Desconectar observador al destruir. API nativa, sin dependencias.

- **v3** (2026-11-02): [Implementation Plan] El scroll móvil se aplica al wrapper Bootstrap table-responsive con mínimo de lectura 45rem; se conserva columnMode force sin scrollbar interno, evitando que ngx-datatable retenga anchos transitorios del sidebar.
