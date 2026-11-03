# PLAN-2026-11-02-perfil-odontologico-pacientes (v1)

**Task:** TASK-perfil-odontologico-pacientes · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-perfil-odontologico-pacientes-ficha-y-listado; ADR-perfil-odontologico-pacientes-identidad-y-acceso.

## Objective
Registrar pacientes odontológicos sobre Clientes existentes, con separación administrativa/clínica, acceso clínico para admin y auditoría sin duplicar identidad.
## Context
Ver investigación del TASK y decisiones explícitas del usuario del 2026-11-02. No hay autorización por registrar un profesional en Personal.

# Specification
## Domain context
Dentistry posee perfil/antecedentes e historial clínico; Customers identidad/contacto/demografía administrativa. accounts/config autorizan; modularity habilita.
## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Paciente | Customer existente con un perfil odontológico por empresa | PB-ODO-001 |
| No informado | Campo opcional sin declaración, no ausencia confirmada | PB-ODO-001 |
| Menor | Edad conocida inferior a 18 años al guardar | Usuario |
| Acceso clínico | Permiso verificado en backend; admin autorizado en v1 | Usuario |
| Auditoría | Cambios con autor/fecha, sin confirmación clínica | Usuario |
## Current behavior
Solo admin (`accounts/models.py:32`), sin dentistry en catálogo (`modularity/domain/modules.py:15`), Customer sin clínica/demografía (`customers/domain/customer.py:110`). Ver rutas completas en TASK.
## Expected behavior
Alta desde selección/búsqueda o alta rápida de Customer; lista paginada y ficha administrativa/clínica separada. Textos clínicos opcionales, editables con historial. Archivo conserva datos. Nacimiento opcional; responsable con nombre y teléfono obligatorio si nacimiento conocido indica menor de 18.
## Domain rules / invariants
- INV-01: empresa sale de sesión; nunca se acepta company_id del cliente como autoridad.
- INV-02: un perfil por empresa/cliente incluso en concurrencia o archivado; ID expuesto igual al Customer.
- INV-03: identidad y demografía solo en Customers; antecedentes solo en Dentistry; ninguna API administrativa contiene clínica.
- INV-04: permisos clínicos y módulos en cada operación; rol admin recibe acceso v1 sin nuevos roles.
- INV-05: perfil e historial se guardan juntos; auditoría no editable; archivado no borra ni desactiva Customer.
- INV-06: desconocido no es ausencia; sin nacimiento no se deduce edad. Futuro inválido; fecha exacta de 18 aniversario ya no exige responsable. Datos de responsable opcionales se guardan como pareja nombre/teléfono para no dejar contacto incompleto.
## Acceptance criteria
- AC-01: crear para Customer de la empresa conserva su ID; búsqueda/alta rápida reutilizan flujo de Clientes; duplicar retorna conflicto sin crear otro Customer/perfil.
- AC-02: ver/editar cinco campos clínicos opcionales; blancos visibles como No informado y sin valor automático de ausencia.
- AC-03: admin ve clínica con permiso verificado; no autenticado, rol distinto, empresa inactiva/ausente, ajena y módulo deshabilitado no acceden ni por URL directa. Roles futuros no se implementan ni simulan.
- AC-04: demografía administrativa opcional; menor de 18 conocido exige nombre/teléfono del responsable; rechazar fecha futura y contacto incompleto sin perder formulario. 18 cumplidos no exige responsable.
- AC-05: alta, edición efectiva y archivo/reactivación quedan auditados con autor, fecha y valores anteriores/nuevos; no hay eliminación ni actualización pública del historial.
- AC-06: archivo conserva historia y unicidad, no altera Customer; edición clínica de archivado rechazada; reactivar conserva ID.
- AC-07: navegación Odontología → Pacientes respeta módulo/capacidad; lista con filtros/paginación conserva contexto al volver; ficha separa Perfil/Antecedentes y solo ofrece capacidades implementadas.
- AC-08: carga, vacío, error/reintento, éxito, validación por campo; conservar datos, impedir doble envío, avisar cambios sin guardar, teclado y presentación móvil/claro/oscuro según DDR.
## Edge cases / Error cases
Cliente ajeno/inexistente → 404; perfil duplicado → 409; edición archivada → 409; inválidos → 400; sin autorización → 401/403 conforme DRF. Fecha ausente → desconocida. Edad se calcula con fecha local del servidor; cumpleaños 29/02 se considera alcanzado el 1/03 en año no bisiesto (comparación mes/día, sin inventar edad). Búsquedas no devuelven clínica; límite de texto clínico 4000, responsable nombre 150/teléfono 30 conforme Clientes.
## Authorization / permissions
Solo admin de empresa activa, customers y dentistry habilitados, con chequeo clínico explícito. Administración de roles/cuentas y pantallas de recepción/caja futuras fuera de alcance por respuesta explícita. No relajar permiso global.
## API contract
- API-01: `/api/dentistry/capabilities/` GET → `{clinical_access:true}` para autorizado.
- API-02: `/api/dentistry/patients/` GET con search/active/page/page_size → página administrativa `{count,next,previous,results}`; POST `{customer_id,...campos_clinicos}` → 201. Resultados exponen id del Customer y su resumen administrativo, estado/fechas; sin notas clínicas en listado.
- API-03: `/api/dentistry/patients/<customer_id>/` GET/PATCH → ficha con resumen administrativo y clínica (`medical_history,dental_history,allergies,medication,clinical_notes`), active y autor/fechas. Identidad/referencia no editables.
- API-04: POST `.../archive/`, `.../activate/`; GET `.../history/` paginado y solo lectura.
- API-05: `/api/customers/<customer_id>/demographics/` GET/PATCH devuelve `{birth_date,responsible_name,responsible_phone}`; GET `.../demographics/history/` paginado. Misma autorización de Clientes, sin campos clínicos, cambios auditados atómicamente. API existente de Customer conserva forma.
## UI behavior
UI-01 lista/formulario/detalle según sistema §5 y DDR. UI-02 Perfil guarda demografía con acción independiente de Antecedentes, evitando escritura parcial entre contextos. UI-03 pestañas de futuras historias ausentes. UI-04 sin permiso no cargar clínica ni historial; backend siempre revalida.
## Non-functional requirements
Paginación servidor; evitar N+1 por fachadas de lectura en lote. Migraciones aditivas y consultas por company_id. Sin dependencias nuevas.
## Out of scope
Odontograma, planes, evolución, adjuntos, citas, roles nuevos, gestión de permisos/cuentas, confirmaciones/enmiendas, sucursales, recursos físicos, cálculos financieros.

# Test Specification
## Unit tests
Validación de textos/edad/responsable y transiciones, desconocidos, exacto aniversario y fecha futura. Dominio sin Django.
## Integration tests
API DRF con PostgreSQL: unicidad, fuga multitenant, módulos, permisos, archivo, auditoría atómica y sin fuga de clínica a Customers. Tests Angular de contratos HTTP y componentes de lista/ficha/formulario, validación y errores. Regresión de Customers, accounts, módulos y límites.
## E2E
NO: no existe Agenda/atención crítica de punta a punta en esta entrega; contratos de autorización se verifican en integración real. Recorrido manual con navegador para diseño, alta/edición/archivo y estados.
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API creación/duplicado/cliente ajeno + frontend búsqueda/selección/alta rápida |
| AC-02 | Dominio textos y API PATCH + componente antecedentes |
| AC-03 | Integración matriz de permiso/empresa/módulo y guard/capacidad Angular |
| AC-04 | Dominio límites edad/contacto/futuro + API demografía + formulario |
| AC-05 | Integración snapshot/autor/no-op/rollback/historial ajeno, clínico y administrativo |
| AC-06 | Dominio transición + API archivo/reactivación/edición bloqueada |
| AC-07 | Componentes/rutas/HTTP paginado + recorrido navegador |
| AC-08 | Componentes errores/doble envío/guard salida + revisión visual 390/1440 claro/oscuro |

# Implementation Plan
## Architecture considerations
Aplicar ADR: dentistry con capas mínimas; adaptador a fachada Customers; permiso en config, sin accounts en contexto. Demografía administrativa separada preserva contratos existentes.
## Proposed solution
Modelo perfil e historial clínico en dentistry; modelo demografía e historial en customers. Dominio puro, casos de uso transaccionales con repositorios acotados. Frontend feature dentistry con servicio tipado, guard y tres páginas. Formularios independientes por contexto.
## Files/components affected
`backend/modules/dentistry/**`, `backend/modules/customers/{domain,application,infrastructure,api,services.py,migrations,tests}/**`; accounts permiso clínico, config permisos/settings/urls; modularity catálogo y regresión. Frontend `features/dentistry/**`, app.routes.ts, assets/data/routes.json, i18n/es.json y servicios de demografía de Clientes. Documentos de arquitectura/diseño/producto y pruebas manuales.
## Implementation steps
1. Crear demografía/validación/repositorio/casos de uso y API/historial administrativos (AC-04/05, INV-03/06).
2. Crear dominio dentistry, persistencia, unicidad y auditoría transaccional (AC-01/02/05/06).
3. Integrar fachada administrativa, módulos y permiso clínico explícito; API paginada y matriz de aislamiento (AC-03, INV-01/02/04).
4. Implementar frontend lista/alta/ficha, filtros/navegación/capacidad y formularios separados según DDR (AC-01/02/04/07/08).
5. Ejecutar pruebas planificadas, build/lint y revisión independiente delivery-publish; documentar evidencia y limitaciones.
## Database / migrations
Nuevas migraciones customers/dentistry; sin modificar las aplicadas. No habilitar dentistry automáticamente. Rollback conservando tablas con datos según ADR.
## Risks
Permisos globales y fuga clínica: regresión y matriz API. Duplicado: restricción DB. Auditoría: transacción/bloqueo. Demografía opcional: no presumir edad.
## New dependencies
Ninguna. Reutilizar entornos y librerías existentes sin leer .env ni instalar paquetes.

## Ajuste de implementación del 2026-11-03

La revisión de interfaz del DDR reemplaza la pantalla intermedia de alta por un modal sobre el listado. El alcance frontend incluye el formulario compartido de alta rápida de Clientes para habilitar su modo embebido, con regresión de su uso existente desde Pedidos. La ficha conserva sus guardados independientes y presenta el historial en listas desplegables.
