# PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial (v1)

**Task:** TASK-registrar-diagnostico-odontograma-inicial · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-registrar-diagnostico-odontograma-inicial-pantalla-odontograma.md` · `docs/adr/ADR-registrar-diagnostico-odontograma-inicial-modelo-de-evaluaciones.md`

## Objective
Permitir al administrador de una empresa odontológica registrar evaluaciones (odontogramas) por pieza FDI y superficie, guardarlas como borrador, confirmarlas como versión inmutable y corregirlas mediante una nueva evaluación enlazada, consultando todas las versiones desde una vista gráfica y una tabla equivalente.

## Context
Trello PB-ODO-002 (ver TASK). Decisión del usuario (2026-11-26): se usa la lista inicial del catálogo (sano, caries, obturación, corona, ausente, endodoncia, implante, fractura, otro) como **propuesta técnica pendiente de validación clínica**, y se ajustará después; el odontólogo validará nombres, coexistencias y superficies. Toda decisión de detalle de este plan sobre el catálogo es provisional y está aislada en un archivo de datos.

# Specification

## Domain context
Bounded context **Odontología** (`dentistry`). Relacionados por fachada: Clientes (identidad del paciente), Personal (profesional). Sin relación con Cotizaciones/Cobros.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Evaluación | Foto completa del estado dental de un paciente en una fecha clínica; borrador o confirmada | Trello PB-ODO-002 |
| Versión | Número `sequence` de la evaluación por paciente (#1 = inicial) | este plan |
| Enmienda | Nueva evaluación que corrige a una confirmada, con motivo y vínculo | Trello |
| Hallazgo | Condición registrada en una pieza (y superficies) o general sin pieza | Trello |
| Pieza | Diente por nomenclatura FDI | Trello (a validar) |
| Sin evaluar | Pieza sin ningún hallazgo en la evaluación | este plan (a validar) |
| Sano | Hallazgo explícito de que la pieza fue evaluada sin patología | este plan (a validar) |

## Current behavior
No existe registro por pieza/superficie; la pieza de proforma es texto libre ≤ 20 caracteres (`backend/modules/dentistry/domain/proforma.py:18,52-61`). Rutas actuales en `backend/modules/dentistry/api/urls.py:9-21`.

## Expected behavior
Existe una pantalla `/pocketbiz/dentistry/patients/:id/odontogram` y una API que cubren el ciclo borrador → confirmada → enmienda, con consulta de cualquier versión.

## Domain rules / invariants
- **INV-01 Dentición y FDI.** `permanent`: 11–18, 21–28, 31–38, 41–48. `temporary`: 51–55, 61–65, 71–75, 81–85. `mixed`: ambos conjuntos. Una pieza fuera del conjunto de la dentición es inválida.
- **INV-02 Tipo de pieza** (por el último dígito): 1–2 incisivo, 3 canino (anteriores); 4–8 premolar/molar (posteriores; en temporales 4–5 molares).
- **INV-03 Superficies** (abreviatura): M mesial, D distal, V vestibular, O oclusal (solo posteriores), I incisal (solo anteriores), P palatina (cuadrantes superiores 1, 2, 5, 6), L lingual (cuadrantes inferiores 3, 4, 7, 8). Anteriores admiten M, D, V, I, P/L; posteriores M, D, V, O, P/L. Cualquier otra combinación es inválida.
- **INV-04 Catálogo inicial (provisional)**:

| Código | Nombre visible | Alcance | Coexistencia | Abrev. | Color (clase) |
|---|---|---|---|---|---|
| `healthy` | Sano | pieza completa | exclusivo (solo hallazgo de la pieza) | SAN | success |
| `caries` | Caries | 1+ superficies | con obturación en otras superficies, endodoncia, fractura, otro | CAR | danger |
| `filling` | Obturación | 1+ superficies | con caries en otras superficies, endodoncia, fractura, otro | OBT | info |
| `crown` | Corona | pieza completa | con endodoncia, implante, fractura, otro | COR | warning |
| `missing` | Ausente | pieza completa | exclusivo | AUS | secondary |
| `endodontics` | Endodoncia | pieza completa | con caries, obturación, corona, fractura, otro | END | primary |
| `implant` | Implante | pieza completa | con corona, otro | IMP | dark |
| `fracture` | Fractura | pieza completa o superficies (opcional) | con caries, obturación, corona, endodoncia, otro | FRA | danger-subtle |
| `other` | Otro | pieza completa o superficies (opcional); **nota obligatoria** | con cualquiera salvo sano/ausente | OTR | light |

- **INV-05** Por pieza: sin condición repetida; caries y obturación no comparten superficie; las condiciones de alcance «pieza completa» no llevan superficies.
- **INV-06** Pieza sin hallazgos = «Sin evaluar»; evaluada sin patología = hallazgo `healthy`. No hay inferencia automática de diagnósticos.
- **INV-07** Hallazgo general (sin pieza): `diagnosis` requerido (≤ 500), `notes` ≤ 1000; se guardan en colección aparte.
- **INV-08** Fecha clínica requerida y no futura; `diagnosis` ≤ 500, `notes` ≤ 1000 por hallazgo.
- **INV-09** Confirmar exige ≥ 1 hallazgo (de pieza o general) y dentición definida; tras confirmar la evaluación es inmutable (ninguna operación de edición/descarte).
- **INV-10** Una sola evaluación en borrador por paciente. Solo se enmienda una evaluación confirmada y, como el borrador es único por paciente, solo mientras no exista otro borrador; una confirmada admite como máximo una enmienda en curso.
- **INV-11** Enmienda: motivo requerido tras recortar (≤ 500), `amends` apunta a la confirmada; copia los hallazgos como base y hereda dentición/profesional.
- **INV-12** Paciente archivado o cliente inactivo: sin crear/editar/confirmar/enmendar; lectura permitida.
- **INV-13** Todo filtrado por `company_id`; autor/confirmador = usuario autenticado.

## Acceptance criteria
- **AC-01** Con paciente de dentición mixta se registra en una misma evaluación un hallazgo en pieza temporal (p. ej. 54) y otro en permanente (p. ej. 16) y ambos se consultan.
- **AC-02** Tras confirmar la evaluación #1 y crear/confirmar la #2, ambas se listan y consultan con sus propios hallazgos; #1 no cambia.
- **AC-03** Pieza inválida para la dentición (p. ej. 19, 54 en permanente, 16 en temporal) se rechaza con 400 indicando la pieza.
- **AC-04** Superficie inválida para la pieza (O en incisivo, I en molar, L en cuadrante superior, P en inferior) o repetida se rechaza con 400.
- **AC-05** Editar o descartar una evaluación confirmada se rechaza con 409 y no cambia datos.
- **AC-06** Enmendar requiere motivo; crea nueva evaluación en borrador enlazada con la anterior; la anterior queda intacta y muestra «Reemplazada por #n» al confirmar la nueva.
- **AC-07** Borrador y confirmada se distinguen en API (`status`) y UI (badge con texto); `allowed_actions` gobierna los botones.
- **AC-08** Los hallazgos generales sin pieza se guardan, listan y consultan aparte.
- **AC-09** Otra empresa → 404; usuario no administrador → 403; módulo `dentistry` o `customers` deshabilitado → 403; paciente archivado no permite crear/editar/confirmar/enmendar.
- **AC-10** Reglas del catálogo: «Otro» sin nota → 400; condición repetida/ coexistencia incompatible/ caries y obturación en la misma superficie → 400.
- **AC-11** Interfaz: gráfico con pieza seleccionada, leyenda textual además del color, distinción T/P en dentición mixta, tabla equivalente, selector de versión con fecha/autor, estados cargando/vacío/error/éxito, navegación por teclado y sin doble envío.
- **AC-12** Pieza sin hallazgos se muestra «Sin evaluar»; pieza con `healthy` se muestra «Sano».
- **AC-13** Registrar o confirmar evaluaciones no modifica proformas, planes ni cobros.

## Edge cases / Error cases
- Cambiar dentición de un borrador con piezas que dejan de ser válidas → 400 listando piezas; no se pierde el borrador.
- Dos confirmaciones simultáneas → la segunda 409 (bloqueo de fila).
- Confirmar una evaluación sin hallazgos → 400.
- Profesional de otra empresa o inexistente → 400.
- Crear segundo borrador → 409 con id del borrador existente.
- Fallo de red al guardar: el formulario conserva lo escrito (UI).

## Authorization / permissions
`CompanyClinicalPermission` con `required_modules = ('dentistry', 'customers')`, igual que PB-ODO-001 (solo administrador en v1; `docs/architecture/ddd.md:1463`).

## API contract
Base `/api/dentistry/`; errores 400 (validación por campo), 403, 404, 409.
- **API-01** `GET odontogram/catalog/` → `{catalog_version, pending_clinical_validation, dentitions, teeth, surfaces, conditions}`.
- **API-02** `GET patients/<customer_id>/evaluations/` (paginado, `-sequence`) y `POST` (crea borrador `{dentition, clinical_date, professional_id?, findings[], general_findings[]}`).
- **API-03** `GET|PUT|DELETE evaluations/<id>/` (PUT reemplaza el contenido del borrador; DELETE descarta el borrador).
- **API-04** `POST evaluations/<id>/confirm/` · **API-05** `POST evaluations/<id>/amend/` `{reason}`.
- Respuesta de evaluación: `id, customer_id, sequence, status, dentition, clinical_date, professional{id,name}|null, author{id,name}, created_at, confirmed_at, confirmed_by, amends_id, amends_sequence, amendment_reason, replaced_by_id, replaced_by_sequence, catalog_version, findings[{id, piece, surfaces[], condition, diagnosis, notes}], general_findings[{id, diagnosis, notes}], allowed_actions[]`. Contratos existentes sin cambios.

## UI behavior
- **UI-01** Pantalla de detalle con pestañas/acciones de ciclo de vida (§5) según DDR: cabecera, selector de versión, datos, vista Gráfico/Tabla, panel de pieza, hallazgos generales.
- **UI-02** Gráfico SVG con botones por pieza, leyenda textual, T/P, «Sin evaluar»; tabla equivalente.
- **UI-03** Diálogos `NgbModal` estáticos: confirmar (resumen + inmutabilidad) y corregir (motivo, `btn-warning`).
- **UI-04** Líneas de estado por sección, `aria-invalid`/`role="alert"` en errores, foco al primer campo inválido, botones deshabilitados al enviar, `unsavedChangesGuard`.
- **UI-05** Todo texto con `translate` en es/en/pt; `tr()` en TS.

## Non-functional requirements
Accesibilidad mínima de `design-system.md` §7; consultas por paciente indexadas `(company_id, customer_id, sequence)`; sin dependencias nuevas.

## Out of scope
Impresión/PDF, radiografías o adjuntos, planes de tratamiento, evolución clínica, cobros, validación clínica final del catálogo, permisos para roles no administradores, múltiples consultorios, edición del catálogo por empresa.

## Open questions
- Validación clínica del catálogo (nombres, coexistencias, superficies y obligatoriedad de nota) por el odontólogo; adjuntar versión aprobada con nombre y fecha a la tarjeta. No bloquea: queda aislada en `odontogram_catalog.py` y expuesta por API-01.

# Test Specification

## Unit tests
`backend/modules/dentistry/tests/test_odontogram_domain.py`: INV-01…INV-11 (piezas por dentición, superficies por tipo, coexistencias, «Otro», confirmar/inmutabilidad, enmienda, fecha futura). Frontend: pruebas del servicio API, utilidades de odontograma (códigos FDI, tipo de pieza) y componentes.
## Integration tests
`test_odontogram_api.py` con PostgreSQL: autorización por empresa/rol/módulo, flujos API-01…05, paginación, bloqueo de segundo borrador, 409 por confirmada, paciente archivado, no efectos en proformas. Karma: página de odontograma (estados cargando/vacío/error, gráfico, tabla, diálogos, doble envío, teclado), pruebas de claves i18n.
## E2E
**NO** — el flujo se cubre con integración de API y pruebas de componentes; no se instala Playwright.
## Regression tests
Suites existentes de `dentistry` y `npm run i18n:check`/prueba de claves iguales.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | API test (mixta, 54 y 16); componente: gráfico muestra T/P |
| AC-02 | API test (dos evaluaciones, consulta de #1); componente: selector de versión |
| AC-03 | unit INV-01 + API 400 |
| AC-04 | unit INV-03 + API 400 |
| AC-05 | unit INV-09 + API 409 PUT/DELETE |
| AC-06 | unit INV-10/11 + API amend; componente: diálogo con motivo |
| AC-07 | API `status`/`allowed_actions`; componente: badge y botones |
| AC-08 | unit INV-07 + API |
| AC-09 | API: 404 otra empresa, 403 no admin / módulo off, paciente archivado |
| AC-10 | unit INV-04/05 + API 400 |
| AC-11 | componentes Karma (leyenda, tabla, estados, teclado, doble envío) + revisión visual |
| AC-12 | unit/INV-06; componente: «Sin evaluar»/«Sano» |
| AC-13 | API test: conteo de proformas/líneas sin cambios tras confirmar |

# Implementation Plan

## Architecture considerations
Ver ADR. Dominio sin Django; repositorio por empresa; fachada de Personal solo en `infrastructure/adapters.py`; serializers solo forma/tipos; estados por métodos del agregado (`confirm()`, `replace_content()`, `amend()`).

## Proposed solution
Agregado `Evaluation` + `Finding`/`GeneralFinding`, catálogo en dominio, casos de uso `EvaluationCommands/Queries`, vistas DRF delgadas, pantalla Angular con SVG propio y servicio API tipado.

## Files/components affected
- Backend (`backend/modules/dentistry/`): `domain/odontogram_catalog.py`, `domain/odontogram.py`, `application/evaluations.py`, `infrastructure/evaluation_models.py`, `infrastructure/evaluation_repository.py`, `infrastructure/adapters.py` (profesional), `api/evaluation_views.py`, `api/urls.py`, `models.py`, `migrations/0005_odontogram_evaluations.py`, tests.
- Frontend (`features/dentistry/`): `models/odontogram.ts`, `services/odontogram-api.service.ts`, `services/odontogram-utils.ts`, `pages/odontogram.component.{ts,html,scss}`, `components/odontogram-chart.component.ts`, `dentistry.routes.ts`, botón en `patient-detail.component.html`, `assets/i18n/{es,en,pt}.json`, specs.
- Docs: `docs/design/design-system.md` (patrón Odontograma, §5 y §6), `docs/architecture/ddd.md` (nota PB-ODO-002).

## Implementation steps
1. Dominio y catálogo con pruebas unitarias (INV-01…11; AC-03/04/05/06/08/10/12).
2. Modelos, migración 0005 y repositorio por empresa (INV-10, INV-13).
3. Casos de uso y adaptador de Personal (INV-12; AC-09).
4. Serializers y vistas API-01…05, `allowed_actions`; pruebas de API (AC-01/02/07/09/13).
5. Servicio y modelos TS, utilidades FDI.
6. Pantalla, gráfico SVG, tabla, panel de pieza, diálogos, i18n es/en/pt (AC-11).
7. Botón en la ficha, ruta con guards, actualización de `design-system.md` y `ddd.md`.
8. Lint (`ruff`/`flake8` en cambiados, `npm run lint`, `i18n:check`) y suites.

## Database / migrations
Nueva `0005_odontogram_evaluations`: `dentistry_evaluation` (company_id, customer_id, sequence, status, dentition, clinical_date, professional_id, author/confirmed por id y nombre, fechas, amends FK propio nullable, amendment_reason, catalog_version; únicas `(company_id, customer_id, sequence)` y parcial de borrador), `dentistry_evaluation_finding`, `dentistry_evaluation_general_finding`. No se edita ninguna migración existente.

## Risks
- Catálogo sin validación clínica (aislado y versionado).
- Complejidad de accesibilidad del SVG (mitigada con tabla equivalente y botones nativos).
- Concurrencia en `sequence` y borrador único (bloqueo de fila del paciente + restricción).

## New dependencies
Ninguna.
