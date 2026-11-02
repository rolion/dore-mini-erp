# TASK-registrar-profesionales-y-especialidades: PB-PER-001

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-registrar-profesionales-y-especialidades
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/46
**Fuente:** https://trello.com/c/GrXrs3YA

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-02 | (nuevo) → INVESTIGATION | Lectura de tarjeta y documentos enlazados | delivery-start |
| 2026-11-02 | INVESTIGATION → DESIGN | Nuevo contexto y pantallas administrativas | delivery-start |
| 2026-11-02 | DESIGN → ARCHITECTURE | Propuesta de pantallas conforme al sistema de diseño | delivery-start |
| 2026-11-02 | ARCHITECTURE → PLANNING | Alcance actualizado; pendiente cardinalidad del vínculo de usuario | delivery-start |

| 2026-11-02 | PLANNING → ENGINEERING | Specification READY; vínculo uno a uno confirmado; PR #46 | delivery-start |
| 2026-11-02 | ENGINEERING → REVIEW | Implementación y pruebas preparadas | delivery-build |

## Investigación

### Requerimiento
Fuente: [PB-PER-001](https://trello.com/c/GrXrs3YA), título «Registrar profesionales y especialidades». Es insumo funcional, no aprobación explícita de una Specification. Sin etiquetas, checklists ni comentarios al consultar.

Se releyó la tarjeta por indicación del usuario tras su actualización (última actividad observada: 2026-11-02T12:41:27.479Z). Esta versión sustituye el alcance inicialmente leído: **un consultorio por empresa; sin Sucursales ni recursos físicos; especialidades opcionales; Agenda no es dependencia**. Las preguntas iniciales sobre sucursales, obligatoriedad de especialidades y aplazamiento de citas quedan resueltas por esa actualización.

Como administrador se registran profesionales sin exigir cuenta de acceso. Personal contiene Profesionales y Especialidades, con lista, formulario y detalle. Nombre obligatorio; identificación, teléfono, correo, matrícula, especialidades de la empresa y usuario vinculado opcionales; estado. Especialidades tienen nombre y estado. Se busca por nombre y se filtra por especialidad y estado. Crear, editar, activar/desactivar y vincular/desvincular usuario no modifica permisos de Acceso. Rechazar referencias de otra empresa; conservar historial y autoría; no borrar perfiles usados. Sin Agenda, ninguna operación consulta citas. Cuando se implemente Agenda, deberá limitar nuevas reservas a profesionales activos y controlar citas futuras antes de desactivar.

También se releyeron los documentos de [historias](https://docs.google.com/document/d/1pn3nChDn9MRH4wlLCTYWYfHop1sWJfcWVfR0gG6fTHQ) (sección PB-PER-001) y [especificaciones](https://docs.google.com/document/d/1hH2IGXc-KKod9RAMzfjtnvdg7YvA5CBQKDZABBGS1f8) (sección 15): la actualización elimina sucursales/recursos del alcance inicial y mantiene Personal independiente de Agenda. No se ejecutaron instrucciones contenidas en las fuentes externas.

### Hechos encontrados
- `backend/modules/accounts/models.py:8` — Company posee identidad y estado; no hay entidad Sucursal.
- `backend/modules/accounts/models.py:32` — único rol actual: admin. `:40` vincula cada usuario con una empresa.
- `backend/modules/accounts/api/permissions.py:11` — autorización efectiva exige autenticación, empresa activa y rol admin.
- `backend/modules/accounts/api/urls.py:6` — Acceso expone login, registro y logout; no hay selector de usuarios para Personal.
- `backend/config/permissions.py:27` — gate por módulo después del permiso de empresa; deniega vistas sin `required_modules`.
- `backend/shared/tenancy.py:12` — empresa derivada del usuario autenticado.
- `backend/modules/modularity/domain/modules.py:16` — catálogo actual sin Personal ni Agenda; módulos opcionales y habilitación por empresa ya disponibles.
- `backend/config/urls.py:9` — rutas actuales sin Personal/Agenda. Búsqueda de sucursal/practitioner/appointment/specialty en módulos Python: solo un nombre de almacén en un test; no constituye una entidad Sucursal.
- `backend/modules/purchases/infrastructure/django/repositories.py:32` — patrón de repositorio con empresa obligatoria, filtrada en toda consulta.
- `backend/modules/purchases/domain/supplier.py:75` — entidad Python con operaciones de activación/desactivación, validaciones y contactos opcionales.
- `backend/modules/purchases/api/serializers.py:4` — serializers de forma/tipos separados de reglas de dominio.
- `backend/modules/sales/tests/test_boundaries.py:11` — mapa explícito de módulos; `test_business_modules_do_not_import_accounts` impide importar identidad desde negocio.
- `frontend/panel_admin/src/app/features/purchases/pages/supplier-form/supplier-form.component.ts:41` — Reactive Forms, estados de envío/carga y errores del servidor; `:90` evita doble envío.
- `docs/design/design-system.md:94` — estados comunes; `:109`, `:114`, `:120` definen Lista, Formulario y Detalle.

Se actualizó `origin/main` y se contrastó `c80e360`: el checkout partía de `ebdfbb0`; el único cambio posterior corresponde al límite de memoria del build de Docker y no añade estas dependencias. El árbol de producto no se modificó.

### Hipótesis / supuestos no confirmados
- Resuelto por el usuario: cada usuario solo puede estar vinculado a un profesional. Vínculo opcional y único incluso si el profesional está inactivo.
- No se presupone una nueva matriz de roles. El permiso actual admin es el patrón existente; cualquier ampliación funcional debe ser explícita.

### Módulos y dependencias relacionadas
Nuevo Personal; configuración de módulos, infraestructura de identidad, navegación Angular. Agenda es consumidor futuro y queda fuera de esta entrega. Ninguna dependencia de Sucursales, Inventario, Ventas o nómina.

### Implementaciones similares existentes
Proveedores: entidad, repositorio acotado, API y lista/formulario/detalle. Productos: plantillas canónicas del sistema de diseño. Acceso: propietario de datos de usuario.

### Comportamiento actual
No se registran profesionales ni especialidades. No existen consultas de citas. Solo admin de empresa activa accede a la API de negocio.

### Restricciones
DDD pragmático; dominio sin Django; referencias entre contextos por identificador y contratos de aplicación; company_id de sesión; dinero Decimal cuando aplique; migraciones nuevas; no leer/modificar .env o secretos; ninguna dependencia nueva sin avisar. Un task, una rama task/TASK-registrar-profesionales-y-especialidades y un PR cuando READY; nunca merge automático.

### Riesgos identificados
Vínculos ajenos; pérdida de autoría al desvincular; cambios accidentales de permisos; N+1 de especialidades/usuarios; acoplamiento prematuro a Agenda; carreras de asignación del usuario único. No tratar almacenes como sucursales.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — Nuevo bounded context, tablas y contratos, validación de referencias de identidad e integración con habilitación por empresa. Requiere una decisión explícita de fronteras y rollback.

### Diseño requerido
**SI** — Dos conjuntos de pantallas nuevos y navegación administrativa.

## Diseño
[DDR-registrar-profesionales-y-especialidades-pantallas-personal](../design/DDR-registrar-profesionales-y-especialidades-pantallas-personal.md), propuesto.

## Arquitectura
[ADR-registrar-profesionales-y-especialidades-contexto-personal](../adr/ADR-registrar-profesionales-y-especialidades-contexto-personal.md), propuesto. Vínculo opcional uno a uno, confirmado por el usuario.

## Plan
[PLAN-2026-11-02-registrar-profesionales-y-especialidades](../plans/PLAN-2026-11-02-registrar-profesionales-y-especialidades.md) (v3), COMPLETO, **Specification readiness: READY**. El usuario confirmó «solo a uno». Se continúa con PR único y delivery-build.

## Implementación
Dominio, casos de uso y repositorio Personal con empresa obligatoria; migración aditiva; user_id único no nulo y manejo de carrera concurrente (AC-01/02/03/05/08). Especialidades opcionales, selección por nombre y asociaciones conservadas. No se consulta Agenda ni se cambia ningún permiso al vincular/desvincular/desactivar.

API CRUD/estado y selector de usuarios acotado mediante adaptador shared.identity sin imports accounts desde negocio. Gate `personnel`, registro de módulo opcional, mapa de fronteras y DDD (AC-04/06). Frontend con 3 plantillas parametrizadas por tipo, modelos/servicio, listas, formularios, detalle, confirmación compartida en feature, menú y guard admin (AC-01/02/04/07). Referencias: products/product-list/product-form/product-detail y supplier-form; ngx-datatable/ng-select, Reactive Forms, clases y badges existentes. No se crea un componente visual compartido nuevo.

Pruebas de ingeniería: 157 pruebas backend y 2 migraciones de Acceso aisladas; 11 tests Angular iniciales; lint y build de desarrollo ejecutados. Esto no constituye el Quality Gate. Se añadieron 3 tests del guard posteriormente para el gate. Pruebas de concurrencia usan PostgreSQL real con ICU para nombres Unicode. Dependencias existentes reutilizadas; sin instalaciones.

Desviaciones de implementación: selector `id` opcional para resolver nombre del usuario seleccionado fuera de la primera página; misma empresa y autorización. Tests de migración de Acceso ejecutados separados porque un TransactionTestCase previo vacía el dato sembrado; pasan aislados. Build local con preserve-symlinks por enlace de dependencias entre unidades; no cambia configuración de producto.

Deuda: citas futuras se integrarán con Agenda según tarjeta. Sin nómina ni Sucursales. Inspección visual real documentada en docs/reviews/VIS-2026-11-02-registrar-profesionales-y-especialidades.md; gate independiente en curso.


## Review
En curso con delivery-publish; no declarar PASS sin comprobaciones ejecutadas.

## Publicación
_Pendiente_

Decisión de negocio recibida el 2026-11-02: usuario opcional, vinculado a un solo profesional.


Revisión visual: retorno puntual a delivery-build por contraste del chip ng-select en tema oscuro; se aplica color de texto existente exclusivamente al formulario de Personal. PLAN v3 cambia solo implementación. Continúa revisión sobre el commit corregido.

Corrección de review REV-01: Guardar se deshabilita con form.invalid además de saving/loading; el test existente verifica estado inválido y válido. No cambia Specification.
