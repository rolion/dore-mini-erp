# PLAN-2026-11-04-proformas-odontologicas-con-pieza-dental (v1)

**Task:** TASK-proformas-odontologicas-con-pieza-dental · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** [DDR](../design/DDR-proformas-odontologicas-con-pieza-dental-proformas-en-ficha-del-paciente.md) · [ADR](../adr/ADR-proformas-odontologicas-con-pieza-dental-agregado-propio-en-odontologia.md)

## Objective
Permitir al doctor elaborar y presentar proformas de servicios dentro de Odontología, con la pieza dental (texto opcional) en cada línea, y ver todas las proformas del paciente con su estado en su ficha.

## Context
Ver el TASK. Copia adaptada de `quotations` (PLAN de PB-COT-001 v3); apilado sobre la rama del PR #52.

# Specification

## Domain context
Bounded context **Odontología**; consume Clientes (ya existente) y Servicios (nuevo) por fachadas.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Proforma odontológica | Documento de servicios para un paciente, con pieza dental por línea | Usuario |
| Pieza dental | Número o código del diente sobre el que se hace el trabajo; texto libre opcional | Usuario |
| Paciente | Perfil odontológico (identificado por `customer_id`) | ADR perfil odontológico |

## Current behavior
Odontología solo tiene pacientes y su historial; no hay proformas dentales.

## Expected behavior
Existe el agregado `DentalProforma` con numeración `ODO-NNNNNN`, líneas congeladas con pieza dental opcional, versiones y listado por paciente.

## Domain rules / invariantes
- INV-01 Cantidad > 0 (≤ 9999.99, 2 decimales), precio ≥ 0 (2 decimales), subtotal = cantidad × precio a 2 decimales (`ROUND_HALF_UP`), total = suma; `Decimal`.
- INV-02 Al incorporar una línea se copian nombre y precio vigentes del servicio activo; las líneas existentes no se releen.
- INV-03 Solo se edita un borrador; `present()` exige ≥ 1 línea; estados `draft → presented → superseded`.
- INV-04 Pieza dental: texto opcional; se recorta con `strip()`; máximo 20 caracteres; sin saltos de línea; vacío equivale a «sin pieza». Se conserva al crear una versión nueva.
- INV-05 El paciente sale de la URL (`customer_id`), nunca del cuerpo. Se exige perfil odontológico existente y **activo** y cliente activo al crear, guardar, presentar y crear versión.
- INV-06 Número `ODO-NNNNNN` consecutivo por empresa; único `(empresa, número, versión)`. «Nueva versión» solo desde `presented` y sin otro borrador del mismo número; al presentar la versión nueva la anterior pasa a `superseded`.
- INV-07 Moneda BOB. Sin ventas, cuentas por cobrar, pagos ni movimientos de stock.

## Acceptance criteria
- AC-01 Crear una proforma de un paciente activo con servicios de 100 y 150 da total 250.00 y número `ODO-000001`; cambiar luego el catálogo no altera la proforma.
- AC-02 Cada línea acepta una pieza dental opcional (`18`, `36`, `11-13`, vacía); se guarda, se devuelve en el detalle y se conserva en la nueva versión. Más de 20 caracteres, con salto de línea o que no sea texto da 400 con error en esa línea.
- AC-03 Cantidad 0/negativa y precio negativo se rechazan por línea; el servidor ignora subtotal/total del cliente.
- AC-04 Un precio distinto del vigente solo se acepta con `can_edit_price`; si no, 403.
- AC-05 Presentar exige ≥ 1 línea; una presentada es inmutable (409); «Nueva versión» y reemplazo según INV-06.
- AC-06 Paciente inexistente o de otra empresa → 404; archivado → 409 al crear/guardar/presentar/nueva versión; cliente inactivo → 400.
- AC-07 `GET patients/<customer_id>/proformas/` devuelve **solo** las proformas de ese paciente y empresa, más recientes primero, paginado, con número, versión, fecha, total y estado; filtro `status`; ninguna proforma de otros pacientes ni del módulo genérico.
- AC-08 Módulos `dentistry`, `customers` o `services` deshabilitados → 403 `module_disabled`; acceso clínico (admin) obligatorio.
- AC-09 Numeración única y sin huecos bajo creaciones concurrentes; independiente entre empresas.
- AC-10 UI: tarjeta «Proformas» en la ficha con estado de cada una y «Nueva proforma»; formulario con columna «Pieza dental»; detalle con pieza y versiones; estados cargando/vacío/error/éxito; doble envío bloqueado; todo texto en es/en/pt.
- AC-11 `quotations` y sus pruebas no cambian de comportamiento; el mapa de dependencias admite solo `dentistry → customers, service_catalog` mediante `adapters.py`.

## Edge cases / Error cases
Cabecera sin fecha → 400; vigencia anterior a la fecha → 400; más de 200 líneas → 400; `id` de línea repetido → 400; módulo deshabilitado → 403; proforma ajena → 404; transición inválida → 409.

## Authorization / permissions
`CompanyClinicalPermission` (admin de empresa activa) + `required_modules = ('dentistry', 'customers', 'services')`. Empresa siempre de la sesión.

## API contract
- API-01 `GET/POST /api/dentistry/patients/{customer_id}/proformas/` (filtro `status`, paginado).
- API-02 `GET/PUT /api/dentistry/proformas/{id}/`.
- API-03 `POST /api/dentistry/proformas/{id}/present/` y `/new-version/`.
- Cuerpo y respuesta: como `quotations` más `lines[].dental_piece` y `customer_id`/`patient_name`; `allowed_actions`, `can_edit_price`, `versions[]`. Rutas existentes de Odontología sin cambios.

## UI behavior
UI-01 tarjeta en la ficha · UI-02 formulario · UI-03 detalle · UI-04 diálogo de presentar, según el DDR y `design-system.md` §5.

## Non-functional requirements
Mensajes de API estables; consultas sin N+1; i18n es/en/pt idéntica; migración aditiva.

## Out of scope
Aceptar/rechazar, total aceptado, PDF, conversión a tratamiento/cobro, odontograma, menú global de proformas dentales, validar el código contra FDI/universal, cambiar `quotations`.

## Open questions
No bloquean: formato de código de diente (texto libre por ahora); si el doctor necesita ver también las proformas genéricas del cliente (decisión actual: no).

# Test Specification

## Unit tests
Dominio puro: INV-01..04, INV-06, AC-02 (validación de pieza), AC-05.

## Integration tests
API con dos empresas, paciente ajeno/archivado/inexistente, módulos deshabilitados, snapshot tras cambiar catálogo, precio no autorizado, lista del paciente (aislamiento y estados), pieza en nueva versión, numeración concurrente con `Barrier`, conteo de filas ajenas sin cambios; límites de módulos en `test_boundaries`.

## E2E
**NO** — se cubre con integración y recorrido local.

## Regression tests
Suites de `dentistry`, `quotations`, `modularity`, `service_catalog` y `sales` (límites).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Dominio + integración |
| AC-02 | Dominio + integración |
| AC-03 | Dominio + integración |
| AC-04 | Integración |
| AC-05 | Dominio + integración |
| AC-06 | Integración |
| AC-07 | Integración |
| AC-08 | Integración |
| AC-09 | Integración concurrente en PostgreSQL |
| AC-10 | Specs de servicio y componentes, `ng build`, `i18n:check`, recorrido local |
| AC-11 | `test_boundaries` + suites de `quotations` |

# Implementation Plan

## Architecture considerations
Según ADR: copia adaptada de `quotations`, agregado en `dentistry`, fachada de Servicios solo por adaptador, tablas propias.

## Proposed solution
`dentistry/domain/proforma.py`, `application/proformas.py`, `infrastructure/{proforma_models.py,proforma_repository.py,adapters.py}`, `api/proforma_views.py` y rutas; frontend en `features/dentistry/` (modelo, servicio, formulario, detalle y componente `patient-proformas` en la ficha).

## Files/components affected
- Backend: `modules/dentistry/{domain,application,infrastructure,api}/…`, `models.py` (exporta modelos), `migrations/0002_*`, `api/urls.py`, `sales/tests/test_boundaries.py`, tests.
- Frontend: `features/dentistry/{models,services,pages,components}`, `dentistry.routes.ts`, `patient-detail.component.html/ts`, i18n `es/en/pt`.
- Docs: `ddd.md` (nota breve de la dependencia nueva).

## Implementation steps
1. Dominio `DentalProforma` + validación de pieza y pruebas (INV-01..04, 06; AC-02, 03, 05).
2. Modelos, migración 0002 y repositorio con contador (AC-09).
3. Adaptadores a Servicios/Clientes, caso de uso con comprobación de paciente activo y política de precio (AC-01, 04, 06).
4. API, serializers, lista por paciente y registro en `urls.py` y `test_boundaries` (AC-07, 08, 11).
5. Frontend: modelo, servicio, formulario con columna «Pieza dental», detalle, tarjeta en la ficha, rutas, claves i18n (AC-10).
6. Verificaciones de la Test Specification y registro de resultados.

## Database / migrations
`dentistry/0002_dental_proformas` aditiva: `DentalProforma`, `DentalProformaLine` (con `dental_piece` CharField 20, vacío por defecto), `DentalProformaCounter`; restricciones e índices del ADR. No se editan migraciones aplicadas.

## Risks
Duplicación con `quotations` (aceptada); numeración concurrente (contador bloqueado + prueba); regla de paciente archivado; tamaño del cambio; conflictos de fusión con #52 en i18n y rutas.

## New dependencies
Ninguna.
