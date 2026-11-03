# TASK-perfil-odontologico-pacientes: Registrar perfil odontológico de pacientes

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-perfil-odontologico-pacientes
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/47
**Fuente:** https://trello.com/c/MTgh7h0v

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-02 | (nuevo) → INVESTIGATION | Lectura de PB-ODO-001 y código | delivery-start |
| 2026-11-02 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Decisiones de negocio respondidas en el chat | delivery-start |
| 2026-11-02 | PLANNING → ENGINEERING | Specification READY; PR #47 abierto | delivery-start |
| 2026-11-02 | ENGINEERING → REVIEW | Implementación y pruebas de la Specification; se solicita Quality Gate independiente | delivery-build |
| 2026-11-02 | REVIEW → ENGINEERING | FAIL: regresión del menú y traducciones en/de faltantes (REV-01) | delivery-publish |
| 2026-11-03 | ENGINEERING → REVIEW | Actualizadas traducciones y cobertura de visibilidad del menú; se solicita segunda revisión | delivery-build |

## Investigación
### Requerimiento
Insumo, no Specification previamente aprobada: PB-ODO-001, tarjeta https://trello.com/c/MTgh7h0v, sin etiquetas, checklists ni comentarios. Extender un cliente existente sin duplicar identidad con perfil odontológico, antecedentes, alergias, medicación y observaciones opcionales; distinguir no informado de ausencia. Listado y ficha, separación administrativa/clínica, auditoría y archivo sin borrar historia. Un perfil por cliente/empresa. Un consultorio por empresa; no depende de Agenda.

Se consultó también el documento enlazado https://docs.google.com/document/d/1pn3nChDn9MRH4wlLCTYWYfHop1sWJfcWVfR0gG6fTHQ (actualizado 2026-11-02). Su convención general conserva solo admin, mientras la nueva vertical habla de acceso clínico y recepción/caja. Las historias PB-ODO-002/003/004/005 incorporan odontograma, planes, evolución y documentos respectivamente: quedan fuera de esta entrega.

Decisiones explícitas del usuario (2026-11-02):
- V1 conserva solo Administrador, con acceso clínico por defecto comprobado en backend. Profesional y Recepción/Caja se incorporarán después con permisos separados. Registrar un profesional en Personal no crea cuenta ni concede acceso.
- Menor de 18 años: responsable con nombre y teléfono.
- Perfil editable con auditoría; confirmaciones clínicas y enmiendas en historias posteriores.

### Hechos encontrados
- `backend/modules/accounts/models.py:32` — solo existe `UserRole.ADMIN`.
- `backend/modules/accounts/api/permissions.py:6` — acceso exige autenticación, empresa activa y admin.
- `backend/config/settings/base.py:90` y `backend/config/permissions.py:19` — permiso global compone empresa/rol y módulos declarados; se debe preservar su denegación por defecto.
- `backend/modules/accounts/admin.py:17` — cuentas adicionales se administran desde Django admin de plataforma.
- `backend/modules/customers/domain/customer.py:110` — Customer conserva identidad, contacto y notas; no tiene nacimiento/responsable ni datos clínicos.
- `backend/modules/customers/infrastructure/django/models.py:6` — CustomerModel tiene UUID y empresa, sin unicidad de teléfono.
- `backend/modules/customers/infrastructure/django/repositories.py:40` — toda lectura del repositorio se acota a empresa; búsqueda por nombre/teléfono en `:52`.
- `backend/modules/customers/application/commands.py:14` — el alta advierte coincidencias de teléfono, pero permite confirmarlas. No equivale a impedir dos perfiles del mismo cliente.
- `backend/modules/customers/services.py:20` y `:31` — fachadas actuales entregan cliente para venta y nombres, no ficha administrativa completa.
- `backend/modules/modularity/domain/modules.py:15` — no existe Odontología en el catálogo.
- `frontend/panel_admin/src/app/app.routes.ts:43` — Clientes ya tiene rutas protegidas por módulo.
- `frontend/panel_admin/src/app/features/customers/services/customer-quick-create.service.ts:10` — alta rápida reutilizable con advertencia de duplicados existente.
- `docs/architecture/ddd.md:817` y `:848` — integración solo por fachadas/DTO y aislamiento por empresa.
- `docs/design/design-system.md:109`, `:115`, `:121`, `:162` — referencias de lista, formulario, detalle y detalle con pestañas.

### Hipótesis / supuestos no confirmados
Ninguna ambigüedad bloqueante tras las respuestas. Decisión proporcional: nacimiento opcional, sin fecha no se deduce edad ni se presume mayoría de edad; el responsable puede informarse voluntariamente. Cuando hay nacimiento conocido menor de 18 se exigen ambos datos. Vacío clínico significa «No informado»; una ausencia declarada se registra como texto explícito.

### Módulos y dependencias relacionadas
Nuevo contexto dentistry → customers por fachada. accounts/config aplican autorización; modularity habilita dentistry con customers obligatorio. Sin dependencia de Personal ni Agenda.
### Implementaciones similares existentes
Clientes (lista, formulario, alta rápida, aislamiento), Compras (ficha con pestañas), configuración por módulo (historial).
### Comportamiento actual
No hay perfil odontológico, permiso clínico, módulo, rutas ni auditoría clínica.
### Restricciones
CLAUDE.md, DDD, no leer .env, migraciones nuevas, una rama/PR, sin dependencias nuevas.
### Riesgos identificados
Fuga clínica por APIs administrativas, ampliación accidental del permiso global, duplicados concurrentes, pérdida de auditoría, edad límite y fechas futuras. Pruebas específicas en el plan.
### Veredicto de complejidad
**NEEDS_ARCHITECTURE**: nuevo contexto, persistencia, contrato y autorización clínica; requiere ADR.
### Diseño requerido
**SI**: menú, lista, alta y ficha con pestañas; requiere DDR.

## Diseño
`docs/design/DDR-perfil-odontologico-pacientes-ficha-y-listado.md`.
## Arquitectura
`docs/adr/ADR-perfil-odontologico-pacientes-identidad-y-acceso.md`.
## Plan
`docs/plans/PLAN-2026-11-02-perfil-odontologico-pacientes.md` (v1), COMPLETO, READY.
## Implementación
Implementados AC-01/02/05/06 en dentistry (dominio, API, restricción de unicidad y auditoría atómica); AC-04/05 en Customers (demografía administrativa e historial separados, dominio con fecha inyectada); AC-03 en permiso clínico explícito compuesto con empresa/módulo; AC-07/08 en feature Angular con lista, alta vinculada y ficha de dos formularios independientes.

Referencias visuales: Clientes/Productos para lista, formulario y detalle; Compras para pestañas. Reutilizados ngx-datatable, Reactive Forms, alta rápida de Clientes, badges, botones, guard de cambios sin guardar y componentes de layout. `PatientHistoryComponent` es específico del expediente; no se agregó un patrón compartido global.

Pruebas implementadas: dominio/HTTP de textos, edad/responsable, unicidad concurrente (dos peticiones reales), autorización/módulos/multiempresa, rollback de escritura si falla auditoría, archivo/reactivación, HTTP Angular, guard, errores, envío único y conservación del otro formulario. Corridas locales de ingeniería: 250 pruebas backend y primeras 21 frontend, lint y build completados; no constituyen aprobación del Quality Gate. Se añadieron después dos pruebas del componente de historial y el formato local de fechas; requieren corrida final independiente.

Desviaciones de implementación: la prueba existente de migración de Accounts se hizo independiente del orden (migra desde BEFORE), porque un nuevo TransactionTestCase de concurrencia vacía datos iniciales; no se modificó ninguna migración aplicada. El catálogo esperado de módulos incorpora dentistry. Sin cambios de Specification ni dependencias nuevas.

Entorno: dependencias reutilizadas del checkout existente mediante junction local ignorado; build/test requieren `--preserve-symlinks` en este worktree entre discos. Vite dev presenta fallo de enlaces Windows, por lo que la revisión de navegador se hace sobre build de producción servido con un helper temporal fuera del repositorio. PostgreSQL 16 temporal con ICU es-BO en 127.0.0.1:55433, sin usar credenciales/base existentes. No se leyó .env.

Recorrido de navegador de ingeniería: alta desde Customer existente, validación visible de menor/responsable, guardados administrativo/clínico y auditoría, ficha clara/oscura en 1440 y 390 px. En móvil, documento 375 px para viewport 390: sin desbordamiento de página; tablas de historial con scroll horizontal local. Confirmación de archivo observada; el adaptador de navegador no mantuvo el diálogo para aceptarlo, así que archivo/reactivación se verifica con integración API y componentes. Pendiente aprobación independiente y revisión visual del build final (incluye buscador Bootstrap y fechas dd/MM/yyyy).
## Review
Ciclo 1: **FAIL** en b0086a9. 250 pruebas backend pasaron; dos pruebas Angular del menú fallaron al ampliar su estructura y requerir etiquetas en/de. Ver `docs/reviews/QA-2026-11-02-perfil-odontologico-pacientes.md` y `docs/reviews/REV-2026-11-02-perfil-odontologico-pacientes-01.md`.

Corrección: traducciones de los dos títulos en inglés/alemán y regresión del menú para incluir Odontología y verificar su visibilidad por módulo. Sin cambio de Specification, rutas ni permisos. Ciclo 2 pendiente.
## Publicación
Pendiente.
