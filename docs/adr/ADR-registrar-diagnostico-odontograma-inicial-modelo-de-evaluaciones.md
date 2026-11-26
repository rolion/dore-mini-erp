# ADR-registrar-diagnostico-odontograma-inicial-modelo-de-evaluaciones: Modelo de evaluaciones odontológicas dentro de `dentistry`

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-diagnostico-odontograma-inicial
**Fecha:** 2026-11-26

## Contexto
PB-ODO-002 necesita registrar el estado dental por pieza FDI y superficie, con borrador, confirmación inmutable y corrección trazable. `dentistry` ya tiene perfil de paciente (`PatientModel`, clave natural `(company_id, customer_id)`) y proformas con versiones (`DentalProforma.new_version`), pero ninguna estructura clínica por pieza (`docs/architecture/ddd.md:1463`). El catálogo clínico es una propuesta técnica sin validar: debe poder cambiar sin tocar la lógica.

## Decisión
1. **Mismo módulo, nuevo agregado.** `Evaluation` (agregado raíz) con hijos `Finding` (pieza FDI opcional, superficies, condición, diagnóstico, notas) dentro de `modules/dentistry/` (`domain/odontogram.py`, `domain/odontogram_catalog.py`, `application/evaluations.py`, `infrastructure/evaluation_*.py`, `api/evaluation_views.py`). No se crea otro módulo: comparte paciente, permisos y ciclo de vida con Odontología.
2. **Evaluación = foto completa e inmutable.** Estados `draft` → `confirmed`. Confirmar fija `confirmed_at/by` y desde ahí ningún método del agregado muta (`replace_content` y `discard` lanzan error). Corregir crea una **nueva** evaluación en borrador (`amends_id` = anterior, `amendment_reason` obligatorio ≤ 500) con copia de los hallazgos como base; al confirmarla, la anterior sigue consultable y se muestra «Reemplazada por #n» (derivado, sin mutar la anterior). Numeración `sequence` por paciente (1, 2, …) bajo bloqueo de la fila del paciente; la evaluación «inicial» es la de menor `sequence` confirmada.
3. **Una sola evaluación en borrador por paciente** (restricción única parcial `(company_id, customer_id) WHERE status='draft'`), para evitar borradores divergentes.
4. **Catálogo como datos de dominio versionables**: `domain/odontogram_catalog.py` (condiciones, alcance pieza/superficies, reglas de coexistencia, rango FDI por dentición, superficies por tipo de pieza). El API lo expone en `GET /api/dentistry/odontogram/catalog/` con `catalog_version` y marca `pending_clinical_validation: true`. Los hallazgos guardan el **código** de condición, nunca la etiqueta.
5. **Validación solo en el dominio** (el serializer valida forma y tipos): pieza válida para la dentición; superficies válidas para el tipo de pieza; reglas de coexistencia; «Otro» exige nota; fecha clínica no futura; confirmar exige ≥ 1 hallazgo (de pieza o general).
6. **Profesional**: `professional_id` opcional (UUID, sin FK entre módulos), comprobado con la fachada `modules.personnel.services.professional_exists` desde `infrastructure/adapters.py`; el nombre se lee con `professional_names`. Autor y confirmador son siempre el usuario autenticado (id y nombre guardados), nunca datos del cliente.
7. **Sin efectos en otros módulos**: no se toca `DentalProforma`, Cobros ni planes; no se infieren diagnósticos.
8. **Aislamiento**: repositorio `DjangoEvaluationRepository(company_id)`; todas las consultas filtran por `company_id`; ids de otra empresa responden 404.
9. **Migración aditiva** `0005_odontogram_evaluations` (tres tablas nuevas: evaluaciones, hallazgos, hallazgos generales); sin datos previos que migrar.

## Alternativas consideradas
- *Hallazgos incrementales acumulados* (estado = suma de actos): descartado por el usuario; complica consultar «la versión inicial» y la inmutabilidad.
- *Tabla de catálogo en base de datos editable por empresa*: descartada, sobredimensiona antes de la validación clínica; un archivo de dominio es más simple y se migra después.
- *Nuevo módulo `odontogram`*: descartado, añade dependencias entre módulos sin límite de contexto propio.
- *Reutilizar el historial JSON de `PatientHistoryModel`*: descartado, no sirve para consultar versiones estructuradas.

## Estrategia de rollback / mitigación
Cambio puramente aditivo: nuevas tablas, rutas y pantalla. Rollback = revertir el PR y, si ya se migró, `migrate dentistry 0004` (borra solo las tablas nuevas; los datos de pacientes y proformas no se tocan). El backup previo al `migrate` del deploy (`docs/deployment/github-actions.md`) cubre datos ya capturados. Mitigación del catálogo sin validar: `catalog_version` guardado en cada evaluación y códigos estables permiten renombrar etiquetas o añadir condiciones sin migrar datos; retirar una condición exige una migración de datos explícita.

## Consecuencias
- Un dato clínico inmutable: un error de modelado sería costoso, de ahí el modo COMPLETO y las pruebas de inmutabilidad.
- Crecimiento: foto completa duplica hallazgos entre versiones (decenas de filas por evaluación; aceptable).
- Nueva dependencia permitida `dentistry → personnel`, solo vía fachada pública y desde `infrastructure/adapters.py`; actualizar `docs/architecture/ddd.md` con una nota PB-ODO-002.
