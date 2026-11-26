# TASK-registrar-diagnostico-odontograma-inicial: Registrar diagnóstico y odontograma inicial

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-registrar-diagnostico-odontograma-inicial
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/136
**Fuente:** https://trello.com/c/2dTNRKfq/9-pb-odo-002-registrar-diagn%C3%B3stico-y-odontograma-inicial
**Specification readiness:** READY (catálogo clínico provisional, a validar luego)

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → PLANNING | Investigación hecha; Specification BLOCKED por catálogo clínico sin validar (decisión del usuario: detener hasta validarlo) | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | El usuario decide usar la lista inicial del catálogo y modificarla luego; DDR, ADR y PLAN v1 (COMPLETO) listos | delivery-start |
| 2026-11-26 | ENGINEERING → REVIEW | Implementación completa de backend y frontend según PLAN v1 | delivery-build |

## Investigación

### Requerimiento
Insumo (tarjeta PB-ODO-002, no es Specification aprobada). Orden 09/16, prioridad P2. Dependencias: PB-ODO-001 (perfil odontológico) y PB-PER-001 (Personal), ambas ya en `main`. Alcance: un consultorio por empresa, sin Sucursales ni reserva de sillón/sala/equipo.

- **Historia:** como odontólogo, registrar diagnósticos y odontogramas para documentar el estado inicial y su evolución por pieza y superficie.
- **Menú/vistas:** Odontología → Pacientes → Odontograma: vista gráfica, alternativa en tabla, selector de fecha/versión y formulario de hallazgo; dentición permanente, temporal y mixta.
- **Campos:** paciente; tipo de dentición; pieza FDI (a validar clínicamente); superficie cuando aplique; condición/hallazgo; diagnóstico; notas; profesional, fecha clínica, autor y fecha de registro. Hallazgos generales sin pieza se registran aparte.
- **Acciones:** guardar borrador y confirmar evaluación; validar pieza/superficie según dentición, empresa y permiso; confirmar conserva versión inmutable; corregir con nueva evaluación/enmienda con motivo y vínculo anterior. El catálogo de condiciones y superficies requiere validación del odontólogo antes de implementar. No inferir diagnósticos ni alterar planes/cobros.
- **Interfaz:** pieza seleccionada y leyenda textual además del color; distinguir temporal/permanente en mixta; tabla accesible equivalente al gráfico; fecha/autor e historial; borrador vs. confirmado claramente distinguidos.
- **Aceptación funcional:** hallazgo en pieza temporal y permanente de paciente con dentición mixta; consultar versión inicial tras otra evaluación y conservar ambas; rechazar pieza/superficie inválida y cambios directos a evaluación confirmada.
- Transversales: módulos habilitados, empresa de sesión, permisos; reutilizar componentes de PocketBiz; carga/vacío/error/éxito; conservar datos ante fallos, evitar doble envío, teclado, confirmar acciones irreversibles; backend es la autoridad.
- Aclaración del usuario: «usa la rama de odontología» → se parte del código de odontología ya integrado en `main` (ver Hipótesis).

### Hechos encontrados
- `backend/modules/dentistry/` existe con `domain/ application/ infrastructure/ api/`; solo cubre perfil de paciente (`domain/patient.py:19-53`) y proformas (`domain/proforma.py`). No hay odontograma, evaluación, hallazgo ni catálogo de condiciones (Grep sin resultados).
- Rutas actuales: `backend/modules/dentistry/api/urls.py:9-21` (`patients/<customer_id>/…`, `proformas/…`); `ClinicalView` exige módulos `dentistry` y `customers` y `CompanyClinicalPermission` (`api/views.py:60-69`, `backend/config/permissions.py:40-43`); acceso clínico solo admin en v1 (`docs/architecture/ddd.md:1463`).
- El paciente se identifica por `customer_id` (perfil único por `(company_id, customer_id)`); las operaciones comprueban paciente activo con `PatientGate.require_active` (`infrastructure/adapters.py:27-43`).
- Auditoría de cambios de paciente: `PatientHistoryView` (`api/views.py:112-121`); autor desde `request.user` vía `ClinicalView.actor` (`api/views.py:71-73`).
- Patrón de versiones/inmutabilidad ya existente en proformas: `DentalProforma.new_version`, `present`, `supersede`, `rectify` con motivo (`domain/proforma.py:254-321`). La «pieza dental» actual es texto libre ≤20 caracteres (`domain/proforma.py:18,52-61`), sin FDI; no se valida contra ninguna nomenclatura.
- Personal expone fachada `professional_exists`, `professional_names` (`backend/modules/personnel/services.py:20-26`); los módulos de negocio no se importan infraestructura entre sí (`docs/architecture/ddd.md`).
- Frontend: `features/dentistry/dentistry.routes.ts` (rutas bajo `/pocketbiz/dentistry/…`, `clinicalGuard`, `unsavedChangesGuard`); la ficha usa pestañas Perfil/Antecedentes (`pages/patient-detail.component.html:196-201`). El design-system §6 dice «no mostrar pestañas de capacidades futuras» (`docs/design/design-system.md:224`), por lo que Odontograma se añade ahora como pestaña o subruta.
- Plantillas de pantalla aplicables (`docs/design/design-system.md`): «Detalle con pestañas…» (§5), «Detalle con selección de líneas y registro de decisión» (§5) y «Diálogo de acción irreversible con motivo» (§5); no existe un componente de odontograma gráfico en Oreva ni en el proyecto.
- Convenciones obligatorias: i18n en es/en/pt, `company_id` en repositorios, migraciones nuevas (último número de dentistry: `0004_dentalproformalinemodel_collected.py`).

### Hipótesis / supuestos no confirmados
- «Rama de odontología»: `task/TASK-perfil-odontologico-pacientes`, `…-proformas-odontologicas-con-pieza-dental` y similares ya están integradas en `main`; la rama `task/TASK-odontologia-boton-ver-pacientes` no (diverge desde un commit anterior, con otros cambios amplios) y no se usa. Si se pretendía otra rama, confirmarlo.
- Sin confirmar con el odontólogo: lista de condiciones, superficies por tipo de pieza, validez FDI temporal (51-85) y permanente (11-48), y semántica de «borrador» y «enmienda».
- Propuesta de trabajo (no aprobada): una evaluación confirmada es una foto completa e inmutable de todas las piezas; corregir crea una evaluación nueva con motivo obligatorio y vínculo a la anterior; permisos como PB-ODO-001 (solo admin, autor = usuario autenticado, profesional opcional de Personal).

### Módulos y dependencias relacionadas
`dentistry` (nuevo agregado dentro del módulo), `customers` (identidad del paciente, vía `CustomersAdapter`), `personnel` (profesional, solo fachada), `modularity`/`config.permissions` (módulos y política clínica). No debe tocar `quotations`, `receivables` ni `service_catalog`.

### Implementaciones similares existentes
Proformas odontológicas (versiones, rectificación con motivo, historial) en `domain/proforma.py` y `application/proformas.py`; ficha con edición por sección en `patient-detail`.

### Comportamiento actual
No hay forma de registrar estado dental por pieza/superficie; la pieza solo aparece como texto en líneas de proforma.

### Restricciones
`CLAUDE.md` (DDD, `company_id`, i18n, sin `any`, migraciones nuevas, avisar antes de instalar dependencias); backend autoridad; sin inferencia automática de diagnósticos; sin alterar planes/cobros.

### Riesgos identificados
- Catálogo clínico incorrecto con consecuencias en documentación médica → mitigación: aislarlo en datos versionables y validarlo antes de construir.
- Gráfico del odontograma sin librería: probablemente SVG propio (sin dependencia nueva) con accesibilidad por tabla equivalente.
- Dato clínico inmutable: error de modelado de versiones es costoso de revertir.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo agregado clínico con migraciones, inmutabilidad/versionado, permisos clínicos y contrato API nuevo; dato sensible con costo de reversa alto.

### Diseño requerido
**SI** — pantalla nueva con gráfico, tabla alternativa, selector de versión y formulario de hallazgo.

## Diseño
`docs/design/DDR-registrar-diagnostico-odontograma-inicial-pantalla-odontograma.md` — pantalla `/pocketbiz/dentistry/patients/:id/odontogram` con gráfico SVG, tabla equivalente, selector de versión, panel de pieza y diálogos de confirmar/corregir; patrón «Odontograma» añadido a `design-system.md`.

## Arquitectura
`docs/adr/ADR-registrar-diagnostico-odontograma-inicial-modelo-de-evaluaciones.md` — agregado `Evaluation` dentro de `dentistry`, foto completa inmutable, enmienda por nueva evaluación, catálogo como datos de dominio, migración aditiva 0005, rollback documentado.

## Plan
`docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md` (v1, modo COMPLETO, Specification READY). Decisiones del usuario: catálogo inicial provisional (propuesta técnica a validar con el odontólogo después), evaluación = foto completa, permisos solo administrador con profesional opcional de Personal. Pregunta abierta no bloqueante: validación clínica del catálogo (versión aprobada, nombre del odontólogo y fecha, a adjuntar a la tarjeta).

## Implementación

**Backend** (`backend/modules/dentistry/`): `domain/odontogram_catalog.py` (catálogo provisional, FDI, superficies; INV-01…04), `domain/odontogram.py` (agregado `Evaluation`: validación, `confirm`, `amend`, inmutabilidad; INV-05…11), `infrastructure/evaluation_models.py` + migración `0005_odontogram_evaluations` (aditiva), `evaluation_repository.py`, `application/evaluations.py` (casos de uso, bloqueo de la fila del paciente, un solo borrador, INV-12), `api/evaluation_views.py` y rutas API-01…05, adaptador `ProfessionalLookup` hacia la fachada de Personal.

**Frontend** (`features/dentistry/`): ruta `patients/:id/odontogram`, botón «Odontograma» en la ficha, servicio API tipado, utilidades FDI, componente SVG del gráfico (botones por pieza, leyenda textual, T/P, teclado), página con selector de versión, tabla equivalente, panel de pieza, hallazgos generales y diálogos de confirmar/corregir/descartar; 121 claves i18n en es/en/pt.

**Cobertura:** AC-01…AC-10, AC-12 y AC-13 con `test_odontogram_domain.py` (16) y `test_odontogram_api.py`; AC-11 con specs Karma de utilidades, servicio, gráfico y página.

**Desviaciones respecto al plan**
- La tabla usa `table-responsive` y no la variante apilada < `lg` del DDR (ajuste menor pendiente).
- Los nombres de `allowed_actions` (`edit`, `confirm`, `discard`, `amend`) los define el plan solo implícitamente; quedaron fijados en backend y en `models/odontogram.ts`.
- Un borrador nuevo sin guardar se cancela sin diálogo; uno guardado pide confirmación y hace `DELETE`.
- Se actualizó un test de PB-ODO-001 que afirmaba que la ficha no mostraba «Odontograma».
- `design-system.md` y `ddd.md` ya se actualizaron en el commit de documentos (patrón Odontograma, nota PB-ODO-002).

**Deuda técnica:** la migración generada excede 120 caracteres por línea (igual que migraciones previas; no se edita); catálogo clínico pendiente de validación por el odontólogo (`pending_clinical_validation: true`).

**Pantalla de referencia:** Detalle con pestañas/acciones de ciclo de vida y diálogo de acción irreversible con motivo; componente nuevo `odontogram-chart` (no se movió a `shared/` por tener un único uso).

## Review
_Pendiente_

## Publicación
_Pendiente_
