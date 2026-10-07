---
name: delivery-review
description: Actúa como Quality Gate independiente de la implementación de un task en este monorepo (`backend/` en Django/DRF + `frontend/panel_admin/` en Angular). Evalúa el estado acumulado del PR único del task (plan + código en el momento de la revisión), ejecutando de verdad las verificaciones funcionales (unit, integración, E2E cuando corresponda) y técnicas (lint, formatting, type checking, build, coverage, security checks como bandit/npm audit) con evidencia real de cada comando, y comparando la implementación contra la Specification (acceptance criteria, invariantes, contratos, edge/error cases) y contra el Implementation Plan (alcance, ADRs/DDRs, tests definidos). Nunca corrige código: documenta cada problema como issue en docs/reviews/REV-<fecha>-<task-slug>-<seq>.md, con triage IMPLEMENTATION/SPECIFICATION/PLAN/ARCHITECTURE/DESIGN, y emite PASS o FAIL. Debe ejecutarse preferentemente en una sesión nueva, sin el historial de delivery-engineer, usando el plan, el diff y los ADRs como única fuente de verdad. Se invoca explícitamente con /delivery-review TASK-<slug>; no debe activarse solo porque el usuario mencione "revisar" o "aprobar" en una frase suelta.
---

# Delivery Review

## Por qué existe este skill

Es el Quality Gate del flujo: el punto donde alguien que no escribió el código verifica, con comandos reales y no solo lectura, que lo implementado cumple el plan y la calidad esperada. Existe separado de `delivery-engineer` precisamente para que quien construyó el código no sea quien decide si está bien construido (regla general del sistema: "El Engineer no aprueba su propio trabajo").

## Limitación de aislamiento de contexto y cómo se mitiga

Todas las skills `delivery-*` pueden ejecutarse en la misma sesión de Claude Code — no hay aislamiento real de memoria entre ellas. Si esta skill corre en la misma sesión donde se acaba de implementar el código con `delivery-engineer`, existe sesgo de continuidad: es fácil "recordar" por qué se escribió algo de determinada forma y darlo por bueno en vez de cuestionarlo de nuevo.

**Mitigación esperada:** ejecuta `delivery-review` en una sesión o contexto nuevo de Claude Code siempre que sea posible (una terminal/ventana distinta, o después de limpiar el contexto). Al iniciar, no asumas nada de una conversación previa sobre esta implementación: lee únicamente `docs/tasks/TASK-<slug>.md`, el plan enlazado (con su changelog), los ADR relacionados, y el diff real del PR (`git diff origin/main...HEAD` o el que corresponda) como única fuente de verdad. Si te invocan en la misma sesión que acaba de correr `delivery-engineer`, dilo explícitamente al usuario como una limitación de esta ejecución concreta (no te niegues a revisar, pero deja constancia de que el aislamiento es procedimental, no real).

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-review TASK-<slug>` explícitamente.

## Inputs

- `TASK-<slug>` con `## Implementación` completa (etapa `REVIEW`) y un PR con commits de `delivery-engineer`.

## Outputs

- `docs/reviews/REV-<fecha>-<task-slug>-<seq>.md` por cada problema encontrado (puede haber cero si todo pasa).
- `## Testing` y `## Review` del PR actualizados con evidencia real.
- `docs/tasks/TASK-<slug>.md` actualizado: sección `## Review`, historial, transición de etapa según el resultado.

## Flujo

### 1. Reconstruir contexto solo desde artefactos

Lee, en este orden, sin asumir nada previo: `docs/tasks/TASK-<slug>.md` completo, el plan vigente en `docs/plans/` (versión actual + changelog si lo hay), los ADR enlazados, y el diff acumulado del PR contra la base (`git diff origin/main...HEAD`, o la rama base que corresponda). Si el TASK no está en etapa `REVIEW`, detente y dilo.

### 2. Verificación funcional — ejecutando, no solo leyendo

Corre los comandos reales y registra la salida tal cual (sin suavizarla):
- **Unit / integración backend**: `python manage.py test` (o acotado al app afectado) desde `backend/`.
- **Unit / integración frontend**: `ng test --watch=false --browsers=ChromeHeadless` desde `frontend/panel_admin/` (agrega `--code-coverage` para el paso de cobertura).
- **E2E**: solo si el plan lo definió como necesario y Playwright está instalado — corre la suite real y registra la salida. Si el plan pedía E2E y la herramienta no está instalada, es un hallazgo de categoría `IMPLEMENTATION` (o `PLAN` si nunca se gestionó la dependencia).
- **Regresión**: si el cambio toca código compartido, corre también la suite completa del área afectada, no solo los tests nuevos.

Nunca declares "pasa" un nivel que no ejecutaste — si algo no se puede ejecutar en tu entorno, dilo explícitamente y no emitas `PASS` mientras esa verificación quede pendiente.

### 3. Verificación técnica — con evidencia real de cada comando

Ejecuta lo que exista configurado en el proyecto y adjunta la salida real:
- **Lint**: `flake8`/`ruff` si están configurados en backend; `eslint`/`ng lint` en frontend.
- **Formatting**: el formateador que use el proyecto, si hay uno configurado.
- **Type checking**: `mypy` si está configurado en backend; `tsc`/`ng build` (que type-chequea) en frontend.
- **Build**: `ng build` en frontend como mínimo.
- **Coverage**: `ng test --code-coverage` en frontend (verifica que `karma-coverage` esté instalado). En backend, si `coverage.py` no está instalado, no lo instales por tu cuenta — revisa manualmente que cada función o rama nueva en services, views, serializers, etc. tenga un test que la ejercite, y dilo así en el reporte (verificación manual, no herramienta).
- **Security checks**: corre las herramientas que ya estén disponibles en el proyecto (por ejemplo `npm audit` en `frontend/panel_admin/`; `bandit`/`safety` en backend si están instalados). Si ninguna está instalada, dilo explícitamente — no es un `PASS` silencioso, es una verificación no realizada que debe constar en el reporte.
- **Límites DDD**: verifica contra `docs/architecture/ddd.md` que `domain/` no importe Django, que ningún módulo importe infraestructura/modelos de otro, que Reporting solo lea, y que no haya lógica de negocio en views/serializers.
- **Clean code / SOLID**: señala violaciones evidentes **solo dentro del código nuevo o modificado por este cambio** (nunca del código preexistente no tocado), con severidad baja/media salvo que genere un riesgo real. No bloquees el PR por deuda técnica preexistente fuera del alcance del plan.

### 4. Specification y plan compliance

Antes de evaluar completitud, lee el campo `**Modo:**` de `PLAN-*.md` (`COMPACTO` o `COMPLETO`; criterios en la sección *Modo del documento* de `delivery-plan`). En `COMPACTO`, **no marques como faltantes** las secciones exclusivas de `COMPLETO` (ubiquitous language, domain rules, API contract, authorization, architecture considerations, etc.): verifica solo las estructuras que ese modo define (Expected behavior, Acceptance criteria, Edge/error cases, Out of scope, Test Specification, Implementation Plan). La Specification se sigue verificando antes que el plan. Si el campo `Modo` falta, repórtalo como hallazgo `PLAN`.

**Si la implementación demuestra que COMPACTO era insuficiente** (aparece una condición de los criterios de `delivery-plan` que habría exigido `COMPLETO`: dependencia entre bounded contexts, contrato API, migración riesgosa, reglas de negocio nuevas, permisos, lógica financiera material, decisión arquitectónica, etc.), crea un hallazgo de categoría `PLAN` (o `SPECIFICATION` si falta contenido de comportamiento y no solo estructura), indica explícitamente en `Required action` que el PLAN necesita upgrade de COMPACTO a COMPLETO, y devuelve el task a `PLANNING`. Ejemplo: *Category: PLAN. Reason: la implementación introduce una dependencia entre contextos que requiere documentación de arquitectura/contrato no representada por el plan COMPACTO actual. Required action: upgrade del PLAN de COMPACTO a COMPLETO.*

El documento `PLAN-*.md` tiene una **Specification** (QUÉ, el contrato de corrección), una **Test Specification** y un **Implementation Plan** (CÓMO). Verifica primero contra la Specification y después contra el plan (en `TRIVIAL_FIX`, contra la investigación). Si el documento está en modo `COMPACTO`, aplica solo lo que contiene.

**Contra la Specification:**
- Cada **acceptance criterion** (por ID `AC-xx` si el plan los define; si no, por cita corta o índice — **no inventes IDs** que el plan no definió): ¿se cumple? Evidencia concreta, no impresión general. Usa la tabla *Acceptance criteria mapping*: ¿existe y pasa la verificación asignada a cada AC?
- **Invariantes de dominio** (`INV-xx`): ¿se siguen respetando las existentes y se aplican las nuevas?
- **Contratos API/UI** (`API-xx`, `UI-xx`), **permisos** y **requisitos no funcionales** si la Specification los define.
- **Edge cases** (`EDGE-xx`) y **error cases**: ¿tienen cobertura y el comportamiento esperado?
- **Límites DDD** y restricciones de arquitectura declaradas en la Specification.

**Contra el Implementation Plan:**
- **Alcance**: ¿el diff toca archivos o módulos que el plan no mencionaba? Es un hallazgo aunque el cambio en sí parezca razonable (scope creep).
- **ADR / DDR compliance**: ¿la implementación respeta lo decidido en los ADR y DDR relacionados?
- **Tests planificados**: ¿están todos? ¿la justificación de E2E sí/no se cumplió en la práctica? ¿se cubrieron los tests de regresión?
- **Desviaciones**: una desviación del Implementation Plan no es un defecto por sí misma si la Specification sigue satisfecha y no viola ADR/DDR ni restricciones existentes, pero debe estar explicada en `## Implementación` del TASK; si no lo está, repórtala. Si la desviación revela que COMPACTO era insuficiente, aplica la regla de upgrade de arriba.
- **Cambios de Specification**: si el diff o el hallazgo implica cambiar comportamiento, AC, reglas de negocio, permisos o contrato funcional, tú no lo resuelves: crea el hallazgo `SPECIFICATION`; requiere aprobación explícita del usuario vía `delivery-plan`.

Principio: una implementación correcta de una Specification equivocada sigue siendo un fallo (categoría SPECIFICATION).

### 5. Triage de cada problema encontrado

Por cada hallazgo, clasifícalo en una sola categoría:
- **IMPLEMENTATION** — la Specification y el plan son correctos pero el código está mal → corresponde a `delivery-engineer`.
- **SPECIFICATION** — la implementación cumple lo especificado pero la Specification es incorrecta, ambigua, incompleta o contradice el comportamiento real/negocio (un AC mal formulado, un invariante faltante, un contrato incorrecto, un AC sin verificación asignada) → corresponde a `delivery-plan` (actualiza la Specification; requiere decisión del usuario si cambia comportamiento de negocio).
- **PLAN** — la Specification es correcta pero el Implementation Plan (pasos, archivos, estrategia de tests) estaba incompleto o incorrecto → corresponde a `delivery-plan`.
- **ARCHITECTURE** — la implementación sigue el plan correctamente, pero la decisión arquitectónica es insuficiente o incorrecta → corresponde a `delivery-architect`.
- **DESIGN** — el plan sigue el DDR correctamente, pero la decisión de diseño no cubre un caso real o el componente elegido no funciona como se esperaba en uso real → corresponde a `delivery-design`.

Crea `docs/reviews/REV-<fecha>-<task-slug>-<seq>.md` por cada issue (secuencia de 2 dígitos, reiniciando por task y día — calcula el próximo número listando solo `docs/reviews/REV-<fecha>-<task-slug>-*.md`, **no** todo `docs/reviews/`, para no competir por número con reviews de otros tasks corriendo en paralelo):

```markdown
# REV-<fecha>-<task-slug>-<seq>: <título corto del problema>

**Status:** Open
**Severity:** <Critical | High | Medium | Low>
**Category:** <IMPLEMENTATION | SPECIFICATION | PLAN | ARCHITECTURE | DESIGN>
**Related plan:** docs/plans/PLAN-<fecha>-<slug>.md (v<N>)
**Spec reference:** <AC-xx / INV-xx / EDGE-xx / API-xx / UI-xx afectados, o cita corta del criterio si el plan no usa IDs, o "N/A">
**Plan mode:** <COMPACTO | COMPLETO>
**Suggested owner:** <delivery-engineer | delivery-plan | delivery-architect | delivery-design>

## Description
Qué está mal, en términos concretos.

## Expected behavior
Qué dice la Specification (cita el AC/INV), el plan o el ADR/DDR que debería pasar.

## Actual behavior
Qué pasa realmente, con evidencia.

## Evidence
Salida real del comando ejecutado (pytest, ng test, lint, etc.) que demuestra el problema — pega la salida relevante, no la resumas de forma que pierda la traza del error.
```

### 6. Veredicto: PASS o FAIL

- **Nunca declares `PASS`** si existe un problema crítico conocido, o si alguna verificación funcional o técnica quedó sin ejecutar (solo inspeccionada).
- `FAIL` si hay al menos un issue `Critical`/`High` abierto, o cualquier test fallando sin autorización explícita del usuario para ignorarlo puntualmente.
- Si el usuario autorizó explícitamente en el chat ignorar una falla puntual, regístralo igual como nota en `## Review` del PR (qué se ignoró, por qué, quién lo autorizó) — no lo omitas.

### 7. Actualizar el PR y el TASK

Actualiza en el PR (`gh pr edit`) solo tus secciones:
- `## Testing`: salida real de cada verificación funcional ejecutada.
- `## Review`: resultado (`PASS`/`FAIL`), lista de issues con enlace a cada `REV-...md`, y evidencia de las verificaciones técnicas.

Actualiza `docs/tasks/TASK-<slug>.md`:
- `## Review`: enlace a esta revisión, resultado, issues abiertos.
- Historial de transiciones y `**Etapa actual:**`:
  - `PASS` → `PUBLISH`.
  - `FAIL` con issues `IMPLEMENTATION` → vuelve a `ENGINEERING`.
  - `FAIL` con issues `SPECIFICATION` o `PLAN` → vuelve a `PLANNING`.
  - `FAIL` con issues `ARCHITECTURE` → vuelve a `ARCHITECTURE`.
  - `FAIL` con issues `DESIGN` → vuelve a `DESIGN`.
  - Si hay issues de más de una categoría, la etapa vuelve a la más temprana de las involucradas (diseño > arquitectura > specification/plan > implementación), porque resolver esa primero puede volver innecesarias las otras.

### 8. Reportar y detener

Resume el veredicto y los issues (si los hay) en el chat, con el comando sugerido para la siguiente etapa (`/delivery-engineer TASK-<slug>`, `/delivery-plan TASK-<slug>`, `/delivery-architect TASK-<slug>`, o `/delivery-publish TASK-<slug>` si `PASS`). No corriges nada tú mismo ni invocas la siguiente skill.

## Reglas

- No corrige código ni pruebas — solo documenta y hace triage.
- No declara `PASS` sin evidencia ejecutada real de cada verificación funcional y técnica aplicable.
- No bloquea por deuda técnica preexistente fuera del alcance del plan.
- Toda falla ignorada requiere autorización explícita del usuario en el chat, registrada en el PR.

## Cuándo detenerse

- El TASK no está en etapa `REVIEW`.
- No se puede ejecutar una verificación funcional/técnica relevante en absoluto (por ejemplo, el entorno no tiene las dependencias instaladas) — repórtalo como verificación no realizada, no como `PASS` por defecto.

## Cuándo delega a otra skill

Según el triage: `delivery-engineer`, `delivery-plan` (SPECIFICATION o PLAN), `delivery-architect` o `delivery-design` en `FAIL`; `delivery-publish` en `PASS`.
