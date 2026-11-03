# PLAN-2026-11-02-administrar-catalogo-servicios (v3)

**Task:** TASK-administrar-catalogo-servicios · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-administrar-catalogo-servicios-pantallas; ADR-administrar-catalogo-servicios-contexto

## Objective
Administrar un catálogo de servicios con precio y duración independiente del stock, aislado por empresa. Regla confirmada por el usuario: los códigos siempre se guardan en mayúsculas.
## Context
Ver investigación del TASK. Fuentes leídas: Trello PB-SRV-001 y documentos vinculados, sección 15 y orden de implementación del 02/11/2026. Personal, Agenda y Cotizaciones no existen en main c80e360.

# Specification
## Domain context
Servicios con Catálogo/Acceso como bases; Personal proveedor opcional. Cotizaciones y Agenda consumidores posteriores. Sin Sucursales ni reserva de recursos físicos.
## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Servicio | Oferta con precio base y duración; sin stock/unidad | PB-SRV-001 |
| Especialidad | Clasificación opcional propiedad de Personal | PB-SRV-001 / PB-PER-001 |
| Uso histórico | Documento conserva valores aplicados en su creación | PB-SRV-001 |
## Current behavior
ProductModel (`backend/modules/catalog/infrastructure/django/models.py:27`) no contiene duración/especialidad. OrderItem (`backend/modules/sales/domain/order.py:139`) conserva precio de productos, no servicios. Rutas (`backend/config/urls.py:9`) sin consumidores clínicos/comerciales de servicios.
## Expected behavior
Listar, crear, consultar, editar y activar/desactivar servicios con campos de la tarjeta. Crear sin especialidad no requiere Personal. Inactivo se conserva y no se ofrece a nuevos usos. Actualizar maestro no reescribe datos históricos.
## Domain rules / invariants
- INV-01: empresa de sesión; consultas/escrituras y referencias siempre dentro de ella.
- INV-02: nombre obligatorio, precio BOB >=0 con Decimal, duración entera en minutos >0.
- INV-03: código opcional único por empresa, recortado y normalizado a mayúsculas antes de validar/persistir. Vacío se guarda como cadena vacía; LIM-01 y lim-01 colisionan. Longitud máxima de código 50, nombre 150, descripción 5000; precio máximo 9999999999.99 y dos decimales; duración entera de 1 a 2147483647. Límites técnicos alineados a los tipos persistidos.
- INV-04: servicios sin stock/unidad ni efectos de inventario. Sin borrado público, se desactivan.
- INV-05: precio/duración en documentos históricos son snapshots del consumidor. Contrato de lectura inmutable; persistencia real se prueba al entregar cada consumidor.
## Acceptance criteria
- AC-01: admin autorizado registra servicio sin especialidad con precio 120 y duración 30; lista/detalle conservan valores y moneda/unidad.
- AC-02: editar a 150/45 afecta lecturas para usos futuros; DTO obtenido antes conserva 120/30. La prueba completa con proforma/cita queda vinculada a PB-COT-001/PB-AGE-002; no declarar ejecutada esa aceptación end-to-end en esta base.
- AC-03: nombre vacío, precio negativo/no finito/exceso de precisión y duración cero/negativa/fraccionaria se rechazan sin escritura, con errores de campo.
- AC-04: código duplicado se rechaza dentro de la empresa y se permite en otra; vacíos no colisionan. Se normaliza a mayúsculas en backend, también si se envía por API; en UI se refleja al escribir/salir del campo.
- AC-05: activar/desactivar conserva datos; consulta histórica permite inactivos y selector para nuevas asignaciones solo devuelve activos.
- AC-06: empresa ajena no puede leer/editar/activar/desactivar el servicio. Módulo deshabilitado o usuario no autorizado no lee ni escribe.
- AC-07: especialidad seleccionada debe estar activa y pertenecer a la empresa; filtro y selector trabajan con Personal cuando su módulo está habilitado. Sin Personal habilitado, el selector/filtro queda deshabilitado y explica la limitación. POST/PATCH sin specialty_id o con null funciona; UUID ajeno, inactivo o inexistente se rechaza con error de campo. Una referencia histórica conserva su nombre y una edición ajena a especialidad no la elimina. No duplicar el catálogo de Personal.
- AC-08: lista/formulario/detalle cumplen UI-01..03 y estados/accesibilidad; conservar filtros y datos al fallar, impedir doble envío.
## Edge cases / Error cases
Duplicación concurrente de código debe traducir constraint a error de campo; UUID ajeno no revela datos. Limpiar código y especialidad opcionales sin perder otros campos. Fallo de proveedor no equivale a especialidad válida. Inactivos con referencias históricas siguen consultables.
## Authorization / permissions
Rol admin existente; empresa activa, sesión y gate services. No crear roles nuevos. UI refleja permisos; backend autoridad.
## API contract
Contrato: `/api/services/` GET paginado y POST; `/{uuid}/` GET/PATCH; `/{uuid}/activate/` y `/deactivate/` POST, sin DELETE. Datos name, code opcional, description opcional, base_price decimal string, duration_minutes entero, specialty_id opcional, active de lectura/acciones y fechas. search/active/specialty_id y page/page_size. 400 validación, 404 ajeno/inexistente, 403 permisos/módulo. company_id no editable. No cambia APIs existentes. GET de lista sin active incluye ambos estados; selector de nuevos usos usa active=true. Respuesta Page: count/next/previous/results. Nombre/código/descripción son strings, specialty_id UUID|null, specialty_name string|null; active y fechas solo lectura. Alta requiere name, base_price y duration_minutes, opcionales code/description con vacío por defecto. PATCH conserva campos omitidos. specialty_id no nulo sin proveedor devuelve 400 por campo y filtro specialty_id UUID válido sin proveedor devuelve lista vacía; none filtra sin especialidad. Parámetros inválidos 400. Límites de paginación como productos (20 por defecto, 100 máximo).
## UI behavior
- UI-01: Lista según design-system.md §5, rutas y componentes en DDR; nombre/precio/duración/especialidad/estado/acciones y filtros persistidos.
- UI-02: Formulario Reactive Forms, errores por campo, guardar/cancelar y salida con cambios; especialidad opcional deshabilitada con explicación mientras no haya proveedor.
- UI-03: Detalle dl.row, money, minutos, badges y acciones; carga/vacío/error/reintento/éxito, teclado y temas/responsividad según §§4/7.
## Non-functional requirements
Sin N+1, paginación servidor, constraints de datos y aislamiento tenant. Decimal backend; importes string frontend. Reutilizar componentes y dependencias existentes.
## Out of scope
Construir Personal, Agenda, Cotizaciones, Odontología, cobros, stock, Sucursales o recursos físicos. Cambiar pedidos de producto o afirmar pruebas reales de consumidores ausentes.
## Decisiones resueltas
- Q1: el usuario indicó «los codigo siempre deben estar en mayusculas». Normalización obligatoria en backend y UI, unicidad después de normalizar.
- Q2: se retiró como bloqueo: las fuentes ya permiten crear sin Personal/especialidad. No es una aprobación nueva del usuario; es aplicación del alcance documentado. Se explicita la limitación temporal y no se acepta un UUID sin validación.

# Test Specification
## Unit tests / Integration tests / Regression tests
Dominio: validaciones y transiciones de estado; aplicación: referencias y especialidad opcional; repositorios/API con PostgreSQL: CRUD, aislamiento dos empresas, gates, constraint y carrera de código. Fachada: snapshot DTO inmutable anterior/posterior a edición, histórico inactivo y consulta para uso nuevo. Angular: HttpTestingController, formularios, filtros, errores/doble envío y navegación. Regresión de modularidad, límites DDD y menú/router.
## E2E
NO instalar runner nuevo para este maestro. Verificación manual integrada de pantallas con API y móvil/escritorio/temas; pruebas reales cotizar/agendar se ejecutan cuando existan PB-COT-001/PB-AGE-002, tal como ordena la fuente (integraciones con consumidor posterior).
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| 01 | Integración API/BD y UI formulario/lista/detalle |
| 02 | Dominio/fachada DTO; pendiente E2E consumidor futuro, explícitamente no ejecutado aquí |
| 03 | Unit dominio y API con BD |
| 04 | Repositorio/API, constraint concurrente, incluyendo normalización a mayúsculas |
| 05 | API/BD y selector/fachada, UI acciones |
| 06 | API dos empresas, rol/gate; Angular rutas |
| 07 | API con Personal activo/inactivo/ajeno y módulo deshabilitado; UI selector/filtro real y referencia histórica |
| 08 | Specs Angular y revisión visual/manual |

# Implementation Plan
## Architecture considerations
Ver ADR propuesto. Dominio puro y empresa obligatoria en repositorios/fachadas; no imports de infraestructura ajena. Q1 resuelta explícitamente y Q2 retirada como bloqueo por alcance de la fuente.
## Proposed solution
Nuevo contexto service_catalog y feature Angular services; habilitación `services` independiente dentro del menú Catálogo. El puerto de especialidades usa una fachada pública de Personal con consultas por empresa, sin FK ni importación de infraestructura ajena. Angular consume el API existente de Personal cuando está habilitado.
## Files/components affected
backend/modules/service_catalog/{domain,application,infrastructure,api,tests,migrations}; config/settings/base.py y config/urls.py; modularity/domain/modules.py; mapa de límites de sales/tests/test_boundaries.py. frontend features/services, app.routes.ts, assets/data/routes.json e i18n; specs correspondientes. docs/architecture/ddd.md y design-system.md si requieren describir las nuevas rutas.
## Implementation steps
1. Registrar decisión del usuario, cerrar contrato v2 y abrir PR único con READY.
2. Modelo de dominio/repositorio y migración aditiva (AC-01..04, INV-01..04).
3. Casos de uso, fachada e integración opcional confirmada (AC-02,05,07).
4. API, permisos, gates, rutas y tests de dos empresas/concurrencia (AC-01..07).
5. UI y navegación según DDR, pruebas Angular (AC-08).
6. Validar migraciones/check, tests/lint/build y revisión independiente de delivery-publish. No prometer E2E de módulos inexistentes.
## Database / migrations
Tabla nueva, company_id UUID indexado, precio decimal 12/2, duración entera positiva y constraint de código no vacío normalizado por empresa y check de mayúsculas/recorte. Sin editar migraciones aplicadas ni tablas financieras. Rollback por deshabilitar gate, preservar datos.
## Risks
Contrato de Personal en trabajo paralelo, aceptación histórica requiere consumidores futuros. No cerrar historia afirmando capacidades ausentes.
## New dependencies
Ninguna nueva prevista; reutilizar entornos/dependencias ya instalados, informar antes de cualquier instalación.

## Changelog
- **v2** (2026-11-02): [Specification] INV-03/AC-04 cerrados por instrucción explícita del usuario: códigos siempre en mayúsculas. Q2 retirada como aclaración innecesaria: fuente permite operación sin Personal. Se explicita rechazo de referencias no verificables y limitación visible, sin adjudicar aprobación del usuario a esa interpretación. [Implementation Plan] Contrato/límites técnicos definidos y estado READY.
- **v3** (2026-11-03): [Specification] AC-07 se actualiza por la instrucción del usuario de resolver el último hallazgo tras integrar Personal en main. Se concreta aceptación de especialidades activas de la misma empresa y conservación histórica. [Implementation Plan] Fachada pública de Personal, API de especialidades ya existente y pruebas de integración. Sin migraciones nuevas.
