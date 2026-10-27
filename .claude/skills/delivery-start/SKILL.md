---
name: delivery-start
description: Primera etapa del flujo de entrega del monorepo (`backend/` Django/DRF + `frontend/panel_admin/` Angular). Dado un requerimiento (o un TASK-<slug> existente), investiga el código, aclara el requerimiento con el usuario, decide diseño (DDR) y arquitectura (ADR) solo cuando aplican, y produce la Specification y el Implementation Plan, abriendo el único PR del task. Solo se detiene a preguntar ante decisiones de negocio abiertas o dudas reales sobre el requerimiento; si la Specification queda READY continúa sola con delivery-build. Para pantallas, aplica el lenguaje visual de docs/design/design-system.md. Úsala al recibir cualquier tarea nueva o al retomar un task en INVESTIGATION, DESIGN, ARCHITECTURE o PLANNING (incluidos los retornos desde delivery-build o delivery-publish por cambios de plan, diseño o arquitectura). Invocación: /delivery-start <descripción> o /delivery-start TASK-<slug>.
argument-hint: "<descripción de la tarea> | TASK-<slug>"
---

# Delivery Start

Cubre las etapas INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING del flujo `delivery-start → delivery-build → delivery-publish`. Reúne hechos, decide solo lo necesario y deja una Specification verificable más un plan. No escribe código de producto.

Plantillas (TASK, DDR, ADR, PLAN, cuerpo del PR): `references/plantillas.md` en esta carpeta. Léela antes de escribir el primer documento.

## Principios

- **Hechos antes que soluciones.** La investigación describe el sistema como es hoy, con `archivo:línea` reales. Nunca mezcles hechos con hipótesis.
- **Nunca inventes reglas de negocio ni resuelvas una ambigüedad de dominio en silencio.** Pregunta.
- **Proporcionalidad.** Cada etapa opcional se ejecuta solo si el veredicto lo pide. Una tarea pequeña genera un documento corto.
- **Una tarea, una rama, un PR** (`task/TASK-<slug>`). Nunca abras un segundo PR.
- Reglas del proyecto de `CLAUDE.md`: `Decimal` para dinero, no editar migraciones aplicadas, no tocar `.env`, avisar antes de instalar dependencias, aislamiento por `company_id`, arquitectura de `docs/architecture/ddd.md`.

## Cuándo preguntar y cuándo seguir

Pregunta al usuario (con `AskUserQuestion`, agrupando las preguntas) **solo** si:
- el requerimiento es tan ambiguo que no se puede investigar nada concreto;
- hay una decisión de negocio abierta: una pregunta cuya respuesta cambia comportamiento, acceptance criteria, permisos, contrato API o cálculo de dinero, y el código y los documentos no la responden;
- una Specification existente tendría que cambiar (los cambios de Specification requieren aprobación explícita).

En todo lo demás decide con criterio, deja constancia en el documento y continúa. No pidas confirmación por trámite, ni entre etapas, ni para abrir el PR.

## Flujo

### 1. Ubicar o crear el TASK
- `TASK-<slug>` dado: lee `docs/tasks/TASK-<slug>.md` y retoma desde su `**Etapa actual:**`. Si no existe, dilo y detente.
- Descripción nueva: deriva un slug descriptivo (kebab-case, minúsculas, sin tildes, 3-6 palabras; **sin numeración secuencial**, hay sesiones en paralelo). Con Glob verifica si existe `docs/tasks/TASK-<slug>.md`: si es el mismo requerimiento, continúalo y avisa; si es otro, añade `-2`, `-3`… y dilo. Crea `docs/tasks/` si falta.

### 2. Investigar (etapa INVESTIGATION)
1. Entiende el problema de negocio. Si el requerimiento es genuinamente ambiguo, pregunta ahora, una sola vez y con todas las dudas juntas.
2. Explora con Grep/Glob y cita siempre `archivo:línea`: bounded context y capas tocadas (`backend/modules/...`), componentes y servicios del frontend, implementaciones similares que se deben seguir, comportamiento actual con evidencia, migraciones, lenguaje de dominio e invariantes existentes, restricciones de `CLAUDE.md` y `docs/`, y riesgos observables.
3. Si la tarea toca pantallas, lee `docs/design/design-system.md` y localiza la pantalla de referencia del mismo tipo (lista, formulario, detalle, reporte).
4. Separa **Hechos encontrados** de **Hipótesis / supuestos no confirmados**.
5. Emite el **veredicto de complejidad** con 1-3 frases de justificación:
   - `TRIVIAL_FIX`: typo, ajuste cosmético o cambio de una línea sin lógica de negocio, contrato, modelo, permisos ni varios archivos relacionados.
   - `NEEDS_PLAN`: cambio acotado sin decisión arquitectónica nueva (la mayoría).
   - `NEEDS_ARCHITECTURE`: cambio estructural, nuevo módulo o bounded context, integración externa, cambios importantes de base de datos, autenticación/autorización, infraestructura, impacto en varios módulos o decisión con deuda técnica importante. Ante duda entre PLAN y ARCHITECTURE, elige ARCHITECTURE.
6. Emite **Diseño requerido: SI/NO**: SI si hay pantallas nuevas, flujos de varios pasos o riesgo de inconsistencia visual; NO si es solo backend o un ajuste cosmético menor. Ante duda, SI.
7. Escribe `## Investigación` en el TASK (plantilla en `references/plantillas.md`) con la fecha real del sistema.

`TRIVIAL_FIX`: salta a «Entrega» sin plan ni PR previo; `delivery-build` lo abrirá. Si al mirar de cerca deja de ser trivial, reclasifica.

### 3. Diseño (etapa DESIGN, solo si Diseño requerido = SI)
Decide **qué ve y hace la persona**, no la arquitectura técnica.
1. Lista las pantallas y flujos afectados y qué hace la persona en cada una. No inventes pantallas no pedidas.
2. **Parte de `docs/design/design-system.md`**: usa la plantilla de pantalla de su tipo (sección 5), los componentes compartidos (sección 3) y los tokens (sección 2). Elige componentes de la plantilla Oreva solo cuando el sistema de diseño no cubra la necesidad, citando la página de `frontend/panel_admin_doc/` o el archivo de código.
3. Si hay más de una opción razonable, compáralas (consistencia con lo existente, esfuerzo). Cualquier desviación del sistema de diseño se justifica en el DDR.
4. Define estados (cargando, vacío, error, éxito) y comportamiento por privilegio, dejando explícito que el frontend no es la barrera de seguridad.
5. Escribe `docs/design/DDR-<task-slug>-<decision-slug>.md`. Si reemplazas un DDR, márcalo `Reemplazado por ...`.
6. Si el DDR introduce un patrón o componente nuevo y reutilizable, proponlo como actualización de `docs/design/design-system.md` (se incluye en el mismo PR).

### 4. Arquitectura (etapa ARCHITECTURE, solo si NEEDS_ARCHITECTURE)
1. Parte de `docs/architecture/ddd.md` y de los ADR previos en `docs/adr/`; una decisión que los contradiga debe justificarlo.
2. Evalúa impactos concretos: contrato API que Angular consume, migraciones sobre datos existentes, autenticación/autorización, aislamiento por `company_id`, infraestructura, acoplamiento entre módulos.
3. Compara alternativas con sus trade-offs. Gana la más simple que resuelve el problema real; no diseñes para requerimientos hipotéticos.
4. Todo cambio sensible (infraestructura, auth, base de datos) lleva **estrategia de rollback/mitigación** o la justificación de por qué no aplica.
5. Escribe `docs/adr/ADR-<task-slug>-<decision-slug>.md`. Si reemplazas un ADR, márcalo `Reemplazado por ...`.
6. Si la decisión depende de información de negocio que no está en el código, pregunta.

### 5. Plan (etapa PLANNING)
1. Verifica que lo citado siga vigente (rutas, firmas). Lo que no cuadre se anota, no se ignora.
2. Calcula **Specification readiness**:
   - `READY`: el comportamiento está definido para implementar.
   - `BLOCKED`: hay una ambigüedad de negocio que permitiría implementaciones razonables pero distintas. Pregunta (ver «Cuándo preguntar»), no avances, no abras el PR, deja el TASK en `PLANNING` con las preguntas abiertas y detente.
3. Elige el **modo** (`COMPACTO` o `COMPLETO`). Basta un eje activo para exigir COMPLETO; ante duda real, COMPLETO:
   1. Comportamiento de dominio afectado: reglas, invariantes, transiciones de estado, cálculos, lógica financiera (excepción COMPACTO: regla simple, local a un contexto, sin nuevas transiciones, sin permisos/finanzas/contratos, 1-2 AC claros).
   2. Frontera cruzada: dos o más bounded contexts o dependencia nueva entre módulos.
   3. Contrato o datos con costo de reversa: contrato API, migración riesgosa, permisos, ADR, DDR con impacto visual relevante.
4. Define la **estrategia de pruebas derivada de la Specification**: todo acceptance criterion tiene una verificación asignada. Justifica explícitamente si corresponde E2E (solo para flujos críticos de punta a punta); si requiere instalar Playwright u otra dependencia, márcalo en «New dependencies» (requiere confirmación antes de instalar).
5. Escribe `docs/plans/PLAN-<YYYY-MM-DD>-<slug>.md` (v1) con la plantilla del modo elegido. Omite lo que no aplica; los IDs (AC-, INV-, EDGE-, UI-, API-) solo cuando mejoren la trazabilidad. Para pantallas, incluye `UI-xx` que referencien la plantilla del sistema de diseño.
6. **Abre el PR único** (solo con READY): `git status`, trae `origin/main`, crea `task/TASK-<slug>`, comitea los documentos (TASK, DDR, ADR, PLAN, y `design-system.md` si cambió), `git push` y `gh pr create` con el cuerpo de `references/plantillas.md`. Título: `TASK-<slug>: <título corto>`. Si el TASK ya tiene PR, reutilízalo.
7. Actualiza el TASK: `## Diseño`, `## Arquitectura`, `## Plan`, rama, PR, historial de transiciones y `**Etapa actual:**` = `ENGINEERING`.

### 6. Actualizaciones (retornos desde build o publish)
Cuando el TASK vuelve con `PLAN_UPDATE_REQUIRED`, `DESIGN_REVIEW_REQUIRED`, `ARCHITECTURE_REVIEW_REQUIRED` o un FAIL de review de categoría SPECIFICATION/PLAN/DESIGN/ARCHITECTURE:
1. Lee la nota (`## Implementación` o `## Review`) y el REV correspondiente.
2. Corrige solo lo afectado, empezando por la etapa más temprana (diseño > arquitectura > specification/plan).
3. **Versiona el PLAN** (`v2`, `v3`…) en el mismo archivo y PR, con `## Changelog` que distinga `[Implementation Plan]` de `[Specification]`. No sobrescribas en silencio. Si un plan COMPACTO necesita dos o más secciones de COMPLETO, o una por condición de los tres ejes, haz el upgrade formal a COMPLETO (nueva versión, mismo PR); no lo parches.
4. Un **cambio de Specification** (comportamiento, AC, reglas, permisos, contrato funcional) requiere aprobación explícita del usuario: pregunta, espera y luego aplica. Un cambio solo del Implementation Plan no.
5. Si reemplazas un DDR o ADR, no borres el anterior.
6. Actualiza historial, etapa y descripción del PR (`gh pr edit`).

## Entrega

- `READY` (o `TRIVIAL_FIX`): resume en el chat veredicto, decisiones y enlace al PR, y **continúa sin esperar** invocando la skill `delivery-build` con `TASK-<slug>`.
- `BLOCKED`: detente con las preguntas abiertas. Cuando el usuario responda, retoma en el paso 5.

## Reglas

- No implementa código de producto ni toca `frontend/panel_admin/src/` ni `backend/` (solo escribe documentos en `docs/` y comitea la rama del task).
- No reinterpreta un DDR o ADR vigente; si hay contradicción real, repórtala y corrige con una versión nueva.
- No marca nada como aprobado por el usuario sin aprobación explícita.
- Nunca fuerza push sobre la rama del PR.

## Cuándo detenerse

- Requerimiento demasiado ambiguo para investigar, o `TASK-<slug>` inexistente.
- `Specification readiness: BLOCKED`.
- Cambio de Specification sin aprobación.
- Duda real sobre en qué rama debe vivir el trabajo.
