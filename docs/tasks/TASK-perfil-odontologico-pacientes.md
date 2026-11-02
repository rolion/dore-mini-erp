# TASK-perfil-odontologico-pacientes: Registrar perfil odontológico de pacientes

**Etapa actual:** PLANNING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-perfil-odontologico-pacientes
**Pull Request:** Pendiente de apertura
**Fuente:** https://trello.com/c/MTgh7h0v

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-02 | (nuevo) → INVESTIGATION | Lectura de PB-ODO-001 y código | delivery-start |
| 2026-11-02 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Decisiones de negocio respondidas en el chat | delivery-start |

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
Pendiente.
## Review
Pendiente.
## Publicación
Pendiente.
