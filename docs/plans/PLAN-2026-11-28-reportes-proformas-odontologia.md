# PLAN-2026-11-28-reportes-proformas-odontologia (v1)

**Task:** TASK-reportes-proformas-odontologia · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-reportes-proformas-odontologia-pantallas · ADR-reportes-proformas-odontologia-ubicacion-y-doctor

## Objective
Añadir al módulo Odontología dos reportes («Proformas por cobrar» y «Proformas pagadas») con filtro por rango de fechas y exportación a PDF y Excel, y un campo «Doctor» en la proforma que alimenta la columna del reporte.

## Context
Ver TASK. Reutiliza el patrón de los reportes de ventas y compras (`document-report`, `shared/report_export`).

# Specification

## Domain context
Bounded context `dentistry` (proforma, paciente, doctor). Contextos relacionados: `receivables` (cobrado, solo lectura), `personnel` (nombre del profesional).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Proforma | Presupuesto odontológico numerado y versionado; vigente = versión presentada | `dentistry/domain/proforma.py` |
| Aceptado | Suma de líneas con decisión «aceptada» | `proforma.totals['accepted']` |
| Cobrado | Suma de pagos de Cobros (`source_kind='dental'`, número de proforma) | `receivables` |
| Por cobrar | Aceptado − cobrado > 0 (sin cobrar o parcial) | `receivables/domain/obligation.py:144` |
| Pagada | Cobrado ≥ aceptado (> 0) | idem |
| Cliente (petición) = Paciente (UI) | Cliente de Odontología | `proforma_models.py:12` |

## Current behavior
La proforma no tiene doctor (`proforma_models.py:6-21`); no hay reportes de Odontología; el menú solo tiene Pacientes y Citas (`routes.json:66-100`).

## Expected behavior
- La proforma guarda un doctor opcional (profesional de la empresa), editable solo en borrador y heredado por las versiones nuevas.
- Dos reportes de solo lectura listan **una fila por proforma presentada vigente con aceptado > 0**, filtradas por fecha de la proforma (inclusive), con columnas Proforma, Paciente, Doctor, Monto, totales (cantidad y suma de Monto), paginación y exportación PDF/Excel con los mismos filtros.
- «Por cobrar»: Monto = saldo (aceptado − cobrado), solo filas con saldo > 0. «Pagadas»: Monto = total cobrado, solo filas con cobrado ≥ aceptado.

## Domain rules / invariants
- INV-01 (nueva): el doctor, si existe, pertenece a la empresa (`ProfessionalLookup.exists`); error de campo `professional_id`.
- INV-02 (nueva): `new_version()` copia el doctor; `replace_content` lo cambia solo en borrador (regla existente de estados).
- INV-03: dinero en `Decimal` con dos decimales; una proforma aparece como máximo una vez (por número, versión presentada).
- INV-04: toda lectura filtra por `company_id`.

## Acceptance criteria
- AC-01: Al crear/editar un borrador se puede elegir doctor (opcional); un doctor inexistente o de otra empresa devuelve 400 en `professional_id`; el detalle y el resumen de la API traen `professional: {id, name} | null`.
- AC-02: Una versión nueva hereda el doctor de la anterior.
- AC-03: «Por cobrar» incluye proformas presentadas vigentes con saldo > 0 (sin cobros y parcialmente cobradas) y excluye borradores, reemplazadas, sin aceptado, y pagadas; Monto = saldo.
- AC-04: «Pagadas» incluye solo las totalmente cobradas; Monto = total cobrado; excluye las demás.
- AC-05: `date_from`/`date_to` filtran por la fecha de la proforma (inclusive); fecha mal formada o `date_from > date_to` → 400; sin fechas = todo.
- AC-06: Cada fila muestra proforma (número), paciente, doctor («—» si no tiene) y monto; la respuesta incluye totales (cantidad, suma de Monto) del conjunto filtrado completo, no solo de la página.
- AC-07: Exportar a `xlsx` y `pdf` devuelve archivos con las mismas filas, columnas y totales; más de 5000 filas → 400 con mensaje; texto que empieza por «=» en nombres no se evalúa como fórmula en Excel.
- AC-08: Aislamiento: una empresa nunca ve proformas, pagos ni doctores de otra.
- AC-09: Los endpoints requieren los módulos `dentistry` y `receivables` habilitados y los mismos permisos que la lista de proformas; sin ellos responden 403.
- AC-10: El submenú de Odontología muestra «Proformas por cobrar» y «Proformas pagadas» (solo con ambos módulos activos) y llevan a pantallas con filtros de fecha, tabla, totales, estados cargando/vacío/error y botones de exportación PDF y Excel.
- AC-11: El formulario de proforma tiene el selector «Doctor» (opcional, «Sin doctor») y el detalle muestra el doctor.
- AC-12: Los reportes de ventas y compras siguen funcionando igual (regresión de la exportación y del componente compartido).
- AC-13: Todo texto visible está en `es/en/pt` y `npm run i18n:check` pasa.

## Edge cases / Error cases
Proforma sin doctor o con profesional borrado → «—»; paciente con nombre que empieza por `=`; rango vacío → lista vacía con totales 0; pago mayor al aceptado (por rectificación) → se trata como pagada; proforma con aceptado 0 no aparece; módulo `receivables` deshabilitado → 403.

## Authorization / permissions
Mismo gate que Cobros/Odontología: módulos `dentistry` + `receivables`; implementación verifica el permiso de lectura de proformas existente. El frontend solo oculta el menú.

## API contract
- API-01: `GET /api/dentistry/reports/proformas/{receivable|paid}/?date_from&date_to&page&page_size` → `{count, next, previous, results: [{id, code, order_date, customer: {id, name}, doctor: {id, name}|null, amount}], totals: {count, amount}}`. Se conserva la forma `code/order_date/customer` de los reportes existentes para reutilizar el servicio del frontend; `doctor` y `amount` son nuevos.
- API-02: `GET …/{receivable|paid}/export/{xlsx|pdf}/?date_from&date_to`.
- API-03 (aditivo): `professional_id` (opcional, nullable) en el POST/PUT de proformas; `professional` en resumen y detalle. Compatible hacia atrás.

## UI behavior
Ver DDR. UI-01 menú (dos entradas con `module` dentistry y receivables); UI-02 pantalla de reporte con plantilla *reporte* (sección 5 del sistema de diseño), filtros fecha inicio/fin, sin período fiscal; UI-03 columnas Proforma (enlace al detalle), Paciente, Doctor, Monto; UI-04 formulario con selector de doctor; UI-05 detalle con doctor.

## Non-functional requirements
Calcula en memoria sobre las presentadas del rango con `prefetch` (sin N+1); sin dependencias nuevas.

## Out of scope
Filtro por doctor, paciente o período fiscal; asignar doctor a proformas ya presentadas (migración de datos); reportes por tratamiento; cambios en Cobros fuera de la nueva lectura.

# Test Specification

## Unit tests
Dominio: `professional_id` en create/replace/new_version (AC-02, INV-02). `shared/report_export`: columnas declaradas, formato de dinero, neutralización de fórmulas (AC-07).

## Integration tests
Backend (`dentistry/tests/test_proforma_reports_api.py` y ajustes en `test_proforma_api.py`): AC-01, 03–09, incluida otra empresa (AC-08), módulos deshabilitados, fechas inválidas, límite de exportación, apertura de los archivos con `openpyxl` y cabecera `%PDF`. Facade de Cobros: `paid_totals` agrupa por número y empresa.
Frontend (specs): servicio de reporte con los dos tipos nuevos, componente con columna Doctor/sin período fiscal, formulario y detalle de proforma con doctor, `sidebar-menu.spec` y rutas; `i18n:check` y la prueba de claves iguales en es/en/pt (AC-13).

## E2E
NO — flujo cubierto por pruebas de API y de componentes; no es un flujo crítico de punta a punta y evitaría instalar Playwright.

## Regression tests
`sales/tests/test_paid_report.py`, `test_receivable_report.py`, `purchases/tests/test_purchase_reports.py`, specs de `document-report` (AC-12).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | `test_proforma_api.py`, `test_proforma_domain.py`, spec del formulario |
| AC-03, AC-04 | `test_proforma_reports_api.py` (por cobrar / pagadas con cobros parciales y totales) |
| AC-05, AC-06 | idem (fechas, totales de todo el conjunto, doctor «—») |
| AC-07 | idem + `shared/tests/test_report_export` |
| AC-08, AC-09 | idem (otra empresa, módulo deshabilitado) |
| AC-10 | `sidebar-menu.spec`, spec de rutas, spec de `document-report` con los tipos dentales |
| AC-11 | specs del formulario y detalle de proforma dental |
| AC-12 | regresión listada |
| AC-13 | `npm run i18n:check` + prueba de claves |

# Implementation Plan

## Architecture considerations
Según ADR: reporte en `dentistry`, cobrado por la fachada de `receivables`, doctor como columna UUID sin FK.

## Proposed solution
Ver ADR y DDR.

## Files/components affected
- Backend `dentistry`: `infrastructure/proforma_models.py`, migración `0007_proforma_professional`, `domain/proforma.py`, `infrastructure/proforma_repository.py`, `application/proformas.py`, `api/proforma_views.py`, nuevos `application/proforma_reports.py` y `api/proforma_report_views.py`, `api/urls.py`, `infrastructure/adapters.py`. `receivables/services.py` (`paid_totals`). `shared/report_export.py`.
- Frontend: `features/dentistry` (formulario, detalle, modelo y servicio de proformas, rutas), `shared/models/document-report.ts` y `shared/components/document-report` (configuración con columna Doctor y filtro de período opcional), `assets/data/routes.json`, `layout/sidebar/menu-layout.ts` si el orden por tipo de empresa lo requiere, `assets/i18n/{es,en,pt}.json`.
- Tests y docs: los citados; actualizar `docs/architecture/ddd.md` solo si lista dependencias entre módulos.

## Implementation steps
1. Dominio + modelo + migración + repositorio + API: doctor en la proforma (AC-01, AC-02, INV-01/02).
2. `receivables.services.paid_totals` con pruebas (AC-08).
3. Generalizar `shared/report_export` sin cambiar la salida actual (AC-07, AC-12).
4. Caso de uso de reporte en `dentistry` + vistas de lista y exportación + rutas (AC-03..09).
5. Frontend: doctor en formulario y detalle (AC-11).
6. Frontend: tipos de reporte dentales, rutas, menú, i18n (AC-10, AC-13).
7. Verificación: `manage.py test`, `ruff`/`flake8` sobre lo cambiado, `npm run lint`, `build`, `test`, `i18n:check`.

## Database / migrations
Una migración nueva aditiva (`professional_id` UUID null); no se edita ninguna aplicada.

## Risks
Cálculo en memoria del aceptado (acotado por rango y tope); regresión de ventas/compras por generalizar la exportación y el componente (cubierta por sus pruebas existentes); proformas antiguas sin doctor (aceptado).

## New dependencies
Ninguna.
