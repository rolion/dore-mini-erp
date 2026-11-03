# REV-2026-11-03-administrar-catalogo-servicios-03: Replanificar integración con Personal

**Status:** Open
**Severity:** High
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-02-administrar-catalogo-servicios.md (v2)
**Spec reference:** AC-07, API-01 y UI-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El PLAN v2 y el ADR se redactaron sobre `main` c80e360, cuando Personal no estaba disponible. `main` avanzó a f6839a4 e incorporó Personal y perfil odontológico. La implementación conserva el proveedor de especialidades deshabilitado y el PR #48 presenta conflictos al integrar la base vigente.

## Expected behavior
Reevaluar el contrato de especialidades de AC-07 frente al proveedor real, actualizar plan/ADR según corresponda y resolver los conflictos antes de un nuevo Quality Gate. El PR debe ser integrable con `main`.

## Actual behavior
El selector y filtro de especialidad siguen deshabilitados; el adaptador `UnavailableSpecialties` rechaza todo UUID no nulo. La rama no fusiona limpiamente con `main` vigente.

## Evidence
- `git ls-remote origin refs/heads/main`: `f6839a41becd65acd4567df239d5a2015923c9ba`.
- `git merge-tree c80e360 origin/main HEAD`: cuatro bloques de conflicto, incluidos `backend/modules/modularity/domain/modules.py` y rutas/menú compartidos.
- `backend/modules/personnel/api/urls.py` en `origin/main` expone `/api/specialties/`.
- GitHub PR #48 reportó `mergeable: false`; permanece draft.

## Triage
Tercer FAIL consecutivo del task. Detener reintentos automáticos según `delivery-publish`; volver a planificación antes de continuar. La Specification no se modifica en este ciclo.

## Avance del 2026-11-03
El usuario pidió resolver los conflictos con `main`. Se integró f6839a4 en el commit 2028f60, conservando Servicios, Personal y Odontología en el catálogo de módulos y sus pruebas. GitHub PR #48 volvió a `mergeable: true`. Verificación tras el merge: Django 1350 tests OK con PostgreSQL local de pruebas; Karma 1115/1115 OK con cobertura; lint y build OK. El hallazgo sigue **Open** por el contrato de especialidades de AC-07 y el PLAN/ADR pendientes de actualización; resolver conflictos no equivale a aprobar el PR.

## Corrección propuesta para revisión
El usuario pidió resolver el último hallazgo. PLAN v3, ADR y DDR actualizados; adaptador de Servicios consulta la fachada pública de Personal. Nuevas asignaciones exigen especialidad activa de la misma empresa y módulo Personal habilitado. Nombres históricos siguen visibles; selector y filtro Angular usan el API real de Personal. Autoverificación sobre la corrección: 1351 tests Django con PostgreSQL OK; 1118/1118 Karma con cobertura OK; lint, build y Bandit OK. Pendiente de Quality Gate independiente antes de cerrar el hallazgo.
