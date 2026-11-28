# ADR-reportes-proformas-odontologia-ubicacion-y-doctor: Dónde vive el reporte y de dónde sale el doctor

**Estado:** Propuesto
**Task relacionado:** TASK-reportes-proformas-odontologia
**Fecha:** 2026-11-28

## Contexto
El reporte combina datos de tres contextos: la proforma y el paciente (`dentistry`), lo cobrado (`receivables`) y el nombre del doctor (`personnel`). La proforma no tiene doctor. Cobros es genérico y no debe conocer Odontología (`TASK-simplificar-flujo-proforma-cobro`); `docs/architecture/ddd.md`: los módulos no se importan infraestructura entre sí, solo fachadas con DTO.

## Decisión
1. **El reporte vive en `dentistry`** (`application/proforma_reports.py`, vistas en `api/proforma_report_views.py`, rutas `/api/dentistry/reports/proformas/receivable/` y `…/paid/` con sufijo `export/<xlsx|pdf>/`). Es el único contexto que conoce paciente, doctor y estado de aceptación.
2. **Lo cobrado se lee por la fachada de Cobros**: nueva función de solo lectura `receivables.services.paid_totals(company_id, source_kind, numbers) -> dict[str, Decimal]` (suma de `PaymentModel.amount` por `source_number`, una consulta agrupada). `dentistry` la consume mediante un puerto/adaptador en `infrastructure/adapters.py`; no se importan modelos de `receivables`. Sin ciclo: `receivables.services` solo importa modelos propios.
3. **Doctor = columna nueva `professional_id` (UUID, `null=True`) en `DentalProformaModel`** (migración aditiva `0007`), sin FK entre módulos. El agregado `DentalProforma` lo guarda, se valida con `ProfessionalLookup.exists`, se copia en `new_version()` y solo se edita en borrador. El nombre se resuelve con `ProfessionalLookup.names` al listar.
4. **Cálculo**: el importe aceptado y el estado de aceptación salen del dominio (`totals['accepted']`) sobre las proformas presentadas del rango (consulta con `prefetch` de líneas y decisiones); el estado de cobro con `_status`-equivalente (cobrado ≥ aceptado → pagada). Todo en `Decimal`.
5. **Exportación**: `shared/report_export` se generaliza a columnas declaradas (encabezados, columnas de dinero, fila de totales) conservando el comportamiento actual de ventas y compras; el reporte de Odontología declara Proforma, Paciente, Doctor, Monto.

## Alternativas consideradas
- **Reporte en `receivables`**: obligaría a Cobros a conocer paciente y doctor (acoplamiento a Odontología). Descartada.
- **Reporte en `reporting`**: el módulo solo lee, pero hoy no hay lectura de proformas ni cobros; crearía dos dependencias nuevas y duplicaría la regla de aceptación. Descartada.
- **Doctor derivado de la última atención/evaluación del paciente**: sin cambio de formulario, pero aproximado y engañoso si el paciente tiene varios doctores. Descartada por el usuario.
- **Guardar el cobrado en la proforma (desnormalizar)**: evita consultar Cobros, pero crea una segunda fuente de verdad. Descartada.

## Estrategia de rollback / mitigación
La migración es aditiva y nullable: no toca datos existentes. Rollback del código: `git revert`; la columna sobrante es inocua. Rollback completo: `migrate dentistry 0006` elimina la columna (se pierde solo el doctor asignado desde el despliegue). El campo nuevo es opcional en la API: los clientes que no lo envían siguen funcionando.

## Consecuencias
`dentistry` pasa a depender en lectura de la fachada de `receivables` (documentar en `ddd.md` si hay tabla de dependencias). El reporte calcula en memoria sobre el rango filtrado: aceptable para el volumen de una clínica, acotado por el tope de exportación; si creciera, habría que materializar el aceptado. Las proformas presentadas antes del despliegue mostrarán doctor «—».
