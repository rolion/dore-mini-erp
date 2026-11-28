# TASK-reportes-proformas-odontologia: Reportes «Proformas por cobrar» y «Proformas pagadas» en Odontología

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-reportes-proformas-odontologia
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-28 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-28 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (migración en `dentistry`, lectura entre módulos), diseño SI; 3 decisiones de negocio resueltas con el usuario | delivery-start |
| 2026-11-28 | PLANNING → ENGINEERING | Specification READY, PLAN v1 y PR | delivery-start |

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
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
