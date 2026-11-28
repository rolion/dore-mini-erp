# TASK-reportes-proformas-odontologia: Reportes «Proformas por cobrar» y «Proformas pagadas» en Odontología

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-reportes-proformas-odontologia
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/145

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-28 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-28 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (migración en `dentistry`, lectura entre módulos), diseño SI; 3 decisiones de negocio resueltas con el usuario | delivery-start |
| 2026-11-28 | PLANNING → ENGINEERING | Specification READY, PLAN v1 y PR | delivery-start |
| 2026-11-28 | ENGINEERING → REVIEW | Implementación completa; pendiente Quality Gate | delivery-build |
| 2026-11-28 | REVIEW → PUBLISH | Quality Gate PASS con observaciones (REV-01 Medium, REV-02 Low abiertos) | delivery-publish |
| 2026-11-28 | PUBLISH | REV-01 y REV-02 cerrados por petición del usuario (pruebas agregadas; PUT sin `professional_id` conserva el doctor) | delivery-build |

## Investigación

### Requerimiento
«En el módulo de odontología debemos agregar un submenú para los reportes: proformas por cobrar y proformas pagadas. Los reportes deben tener filtros de búsqueda por rango de fecha y se debe poder exportar a PDF y Excel. El reporte incluye: proforma (código), cliente, doctor, monto.»

Aclaraciones del usuario (2026-11-28, respuestas a las preguntas de negocio):
1. **Doctor:** campo nuevo en la proforma (profesional elegido al crear/editar); las proformas anteriores muestran «—».
2. **Monto:** «por cobrar» = saldo pendiente (incluye parcialmente pagadas); «pagadas» = total cobrado.
3. **Fecha del filtro:** fecha de la proforma.

### Hechos encontrados
- `backend/modules/dentistry/infrastructure/proforma_models.py:6-21` — `DentalProformaModel` (`number`, `version`, `status`, `customer_id`, `patient_name`, `date`, …); **no tiene doctor**. El doctor solo existe en evaluaciones (`domain/odontogram.py:152`) y atenciones (`domain/encounter.py:49`), sin vínculo con la proforma.
- `backend/modules/dentistry/domain/proforma.py:12-13,157-170,172-191` — estados `draft/presented/superseded`; `total`, `totals['accepted']` y `acceptance_status` se derivan del libro de decisiones por línea (no son columnas SQL).
- `backend/modules/dentistry/api/proforma_views.py:68-80,118-125` — `ProformaInputSerializer` (fecha, vigencia, notas, líneas) y `summary_data` (`accepted_total`, `collectible` = presentada y aceptado > 0).
- `backend/modules/dentistry/services.py` — fachada hacia Cobros: `get_commitments(company_id, numbers)` con DTO `CommitmentSnapshot` (`shared/domain/commitment.py`).
- `backend/modules/receivables/infrastructure/django/models.py:6-45` — `ObligationModel` (clave `source_kind='dental'` + `source_number`; se crea al primer pago) y `PaymentModel.amount`; `domain/obligation.py:144-147` `_status(accepted, paid)` → `pending/partial/paid`. `receivables/services.py:27` ya es una fachada de solo lectura (`list_historical_payments`).
- `backend/modules/dentistry/infrastructure/adapters.py:8,33-37` — `ProfessionalLookup` (`exists`, `names`) sobre la fachada de `personnel`; `application/evaluations.py:20-22` valida el profesional con el mensaje «El profesional no existe en esta empresa.».
- Precedente directo (en `main`): reportes de compras — `backend/modules/purchases/api/purchase_report_views.py` (lista paginada + totales + exportación `xlsx|pdf`, `MAX_EXPORT_ROWS`), `purchases/application/purchase_report_queries.py`, `backend/shared/report_export.py` (`build_xlsx`/`build_pdf`, **cuatro columnas fijas** código/tercero/total/saldo, neutraliza fórmulas) y, en el frontend, `shared/components/document-report`, `shared/models/document-report.ts` (`DOCUMENT_REPORT_CONFIG` por tipo), `shared/services/document-report-api.service.ts`.
- `backend/requirements/base.txt:5-6` — `openpyxl` y `reportlab` ya instalados (sin dependencias nuevas).
- `frontend/panel_admin/src/assets/data/routes.json:66-100` — menú «Odontología» (Pacientes, Citas con `module: agenda`); los reportes de ventas/compras se añadieron como entradas del submenú del módulo (`routes.json:127-138,268-279`).
- `frontend/panel_admin/src/app/features/dentistry/pages/encounter-list.component.ts:45-62` — patrón de selector de profesionales (`personnel.list('professionals', …)` con `fetchAll`); `dental-proforma-form.component.*` es el formulario donde falta el selector.

### Hipótesis / supuestos no confirmados
- Universo de ambos reportes: proforma **presentada vigente** (una fila por número) con importe aceptado > 0; borradores y reemplazadas no entran. «Pagada» = cobrado ≥ aceptado (misma regla `_status` de Cobros); «por cobrar» = aceptado − cobrado > 0.
- El filtro de fechas es inclusivo en ambos extremos; sin fechas = todo. No se pide período fiscal.
- El doctor es opcional en el formulario (no se rompe ningún flujo existente) y se hereda a las versiones nuevas.
- Las proformas presentadas antes de este cambio no se pueden editar, así que seguirán con «—» salvo que se cree una versión nueva.

### Módulos y dependencias relacionadas
`dentistry` (modelo, API, reporte), `receivables` (nueva lectura de pagos por proforma en su fachada), `personnel` (nombres de profesionales, ya usado), `shared` (exportación), frontend `features/dentistry`, `shared/components/document-report`, menú e i18n.

### Implementaciones similares existentes
Reportes de compras pagadas/por pagar y de ventas (ver arriba); `DDR-reporte-ingresos-por-venta-pantalla`.

### Restricciones
`CLAUDE.md`: `company_id` siempre, `Decimal`, sin texto hardcodeado (i18n es/en/pt), módulos solo por fachada, nunca editar migraciones aplicadas, sin dependencias nuevas.

### Riesgos identificados
- El importe aceptado sale del libro de decisiones, no de SQL: el reporte calcula en Python sobre las proformas presentadas del rango (como ya hace Cobros); el tope de exportación (5000) y la paginación lo acotan.
- `shared/report_export` solo admite el esquema de cuatro columnas con dos de dinero: hay que generalizarlo sin romper ventas ni compras.
- Dependencia nueva `dentistry → receivables.services` (solo lectura, DTO): sin ciclo porque esa fachada solo importa modelos de `receivables`.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — migración sobre una tabla existente, dependencia nueva de lectura entre dos módulos y generalización de un componente compartido en backend y frontend.

### Diseño requerido
**SI** — dos pantallas nuevas, una entrada nueva en el menú y un campo nuevo en el formulario de proforma.

## Diseño
`docs/design/DDR-reportes-proformas-odontologia-pantallas.md`.

## Arquitectura
`docs/adr/ADR-reportes-proformas-odontologia-ubicacion-y-doctor.md`.

## Plan
`docs/plans/PLAN-2026-11-28-reportes-proformas-odontologia.md` (v1, COMPLETO, READY).

## Implementación
**Resumen.** Backend (`dentistry`): `professional_id` (UUID, nullable) en `DentalProformaModel` con migración aditiva `0007_proforma_professional`; el agregado lo guarda, `replace_content` lo cambia en borrador y `new_version()` lo hereda; el servicio lo valida con `ProfessionalLookup.exists` (400 en `professional_id`); resumen y detalle exponen `professional: {id, name} | null` (nombres resueltos en lote). Nuevo caso de uso `application/proforma_reports.py` (`ProformaReports`) que lee las proformas presentadas del rango (`presented_between` en el repositorio), calcula el aceptado con el dominio y lo cobrado con el puerto `CollectionsReader` (adaptador sobre `receivables.services.paid_totals`, nueva lectura agrupada de solo lectura); vistas de lista y exportación en `api/proforma_report_views.py`, rutas `/api/dentistry/reports/proformas/{receivable|paid}/` y `…/export/{xlsx|pdf}/` con `CompanyClinicalPermission` y módulos `dentistry` + `receivables`. `shared/report_export.py` gana `build_table_xlsx` / `build_table_pdf` (columnas y pie declarados); `build_xlsx` / `build_pdf` delegan en ellos con la misma salida.
Frontend: `DocumentReport` admite los tipos `dental-receivable` y `dental-paid` (`doctorColumn`: columnas Doctor y Monto, sin período fiscal, totales con suma de Monto); rutas `dentistry/reports/{receivable,paid}` (guards `moduleGuard` + `clinicalGuard`); dos entradas en el submenú de Odontología (con `module: receivables`); formulario de proforma con selector «Doctor» (opcional) y detalle con el doctor; i18n es/en/pt.

**Cobertura.** AC-01/AC-02 + INV-01/02: `test_proforma_professional_api.py`, `DentalProformaProfessionalTests`, specs del formulario, detalle y servicio de proformas. AC-03..09 + INV-03/04: `test_proforma_reports_api.py` (por cobrar/pagadas con cobro parcial y total, fechas inclusivas e inválidas, totales de todo el conjunto, exportación xlsx/pdf, neutralización de `=`, límite de filas, aislamiento por empresa, 403 sin módulos, una sola fila con versiones) y `test_paid_totals.py`. AC-10: `sidebar-menu.spec`, `menu-layout.spec`, spec de `document-report` con el tipo dental y del servicio. AC-11: specs del formulario y detalle. AC-12: pruebas existentes de ventas y compras siguen en verde. AC-13: `npm run i18n:check`.

**Desviaciones respecto al plan.**
- `build_xlsx`/`build_pdf` no se «generalizaron» en sitio: se añadieron `build_table_*` y los anteriores delegan en ellos (misma salida; evita tocar ventas y compras).
- En el menú «Odontología» de empresas de tipo `odontologia`, «Presupuestos» (anidado por `menu-layout.ts`) queda **después** de los dos reportes; se ajustaron los specs de orden.
- El `ng-select` de Doctor usa `NgSelectComponent` como `encounter-list`.

**Deuda técnica.** Cálculo del aceptado en memoria sobre el rango (ver ADR). `professional_id` ausente en un PUT equivale a «sin doctor» (el formulario siempre lo envía).

**Pantallas.** Referencia: reporte compartido `document-report` (DDR-reporte-ingresos-por-venta-pantalla) y formulario `dental-proforma-form`; sin componentes compartidos nuevos.

**Entorno / verificación propia (no es el Quality Gate).** Se copió `backend/.env` del proyecto principal (no versionado, sin leerlo) y se enlazó `frontend/panel_admin/node_modules` por *junction* al del proyecto principal (sin instalar dependencias). Backend: 237 pruebas de `dentistry`, `receivables`, ventas y compras OK; `ruff`/`flake8` sin avisos nuevos en lo cambiado. Frontend: `ng test` 1970 OK, `ng lint`, `ng build` e `i18n:check` OK. Suite completa del backend: 2649 pruebas OK (en serie; el ejecutor paralelo aborta por una prueba intermitente del reloj, ajena). Una prueba de fronteras (`test_boundaries`) obligó a declarar la dependencia `dentistry → receivables` del ADR.


## Review
**Quality Gate: PASS con observaciones** (subagente aislado, sobre `ba2a49be`). Backend: suite completa 2649 pruebas OK. Frontend: 1970 OK, `lint`, `build`, `i18n:check` y `npm audit` (0 vulnerabilidades) OK; `ruff`/`flake8`/`bandit` sin avisos nuevos. Sin revisión visual en navegador (no verificada) ni E2E (el plan lo descarta).
Hallazgos: [REV-01](../reviews/REV-2026-11-28-reportes-proformas-odontologia-01.md) Medium (faltan pruebas del plan: sobrepago, doctor borrado, `report_export` unitario, 403 clínico); [REV-02](../reviews/REV-2026-11-28-reportes-proformas-odontologia-02.md) Low (PUT sin `professional_id` borra el doctor). **Cerrados** después del Quality Gate: se agregaron las pruebas de REV-01 y el PUT sin `professional_id` ahora conserva el doctor (REV-02); verificado con las pruebas de dentistry, sales y shared (513 OK) y lint. No se repitió el Quality Gate completo.

## Publicación
PR #145 listo para aprobación humana (no se mergea). Cambios sensibles: **base de datos** (migración aditiva 0007) y dependencia nueva entre módulos (`dentistry → receivables`), respaldados por el ADR; sin cambios de autenticación ni infraestructura. Pendiente de la persona que aprueba: revisar en navegador los dos reportes y el selector de doctor (estados, contraste, móvil 390 px, tema oscuro) (REV-01/02 ya cerrados).
