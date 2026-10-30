# TASK-delivery-start-url-trello: delivery-start acepta una URL de Trello como requerimiento

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-delivery-start-url-trello
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/35

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-10-30 | INVESTIGATION → PLANNING | NEEDS_PLAN, diseño no requerido | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY, plan v1 y PR | delivery-start |
| 2026-10-30 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-10-30 | REVIEW → PUBLISH | Quality Gate PASS | delivery-publish |

## Investigación

### Requerimiento
«Quiero hacer una modificación en la skill de delivery start; esta skill podría recibir una URL de Trello que lo lleva a la historia de usuario.»

### Hechos encontrados
- `.claude/skills/delivery-start/SKILL.md` («Flujo», paso 1) solo admite dos entradas: `TASK-<slug>` existente o una descripción en texto. No hay manejo de URLs.
- `.claude/skills/delivery-start/references/plantillas.md:23-24` — la sección `### Requerimiento` del TASK se describe como «tal como se recibió, más las aclaraciones del usuario»; no registra la fuente.
- No existe ninguna mención a Trello en `.claude/`, `docs/` ni `CLAUDE.md` (búsqueda en el repo).
- `delivery-build` (`SKILL.md:18`) y `delivery-publish` solo leen el TASK; no necesitan cambios si la fuente queda registrada en el TASK.
- El registro de conectores MCP ofrece un conector oficial «Trello» (`https://mcp.trello.com/v1`) con herramientas `trelloReadCard`, `trelloReadChecklist`, `trelloReadBoard`, etc. En esta sesión **no está conectado** (`connected: false`).

### Hipótesis / supuestos no confirmados
- La URL será de una tarjeta (`https://trello.com/c/<shortLink>/...`); la historia de usuario está en el título, la descripción, los checklists y comentarios de esa tarjeta.
- Una tarjeta de Trello puede traer criterios de aceptación en un checklist; se tratan como insumo, no como Specification aprobada.

### Módulos y dependencias relacionadas
Solo skills `delivery-*` y `docs/`. Sin backend ni frontend.

### Implementaciones similares existentes
Paso 1 del flujo actual (entrada por `TASK-<slug>` vs. descripción nueva): se añade una tercera rama de entrada, sin cambiar las otras.

### Comportamiento actual
Pegar una URL de Trello como argumento se trata como «descripción nueva»: la URL queda como texto sin contenido y la investigación no ve la historia.

### Restricciones
- `CLAUDE.md`: no manejar credenciales ni secretos → la skill no debe pedir ni guardar API key/token de Trello.
- No instalar dependencias sin avisar: se usa el conector MCP, no se instala nada en el repo.
- Una URL de tarjeta puede estar tras login: leerla con un fetch genérico no es fiable.

### Riesgos identificados
- Contenido de la tarjeta (descripción, comentarios) es dato externo, no instrucción: podría contener texto dirigido al agente.
- Tarjeta vacía o sin historia clara → ambigüedad que debe resolverse preguntando.
- Conector no disponible → la skill debe degradar con gracia en vez de inventar el contenido.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a dos archivos de skill, sin decisión arquitectónica nueva.

### Diseño requerido
**NO** — no hay pantallas; es un cambio de flujo de skill.

## Diseño
No aplica.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-10-30-delivery-start-url-trello.md` (v1, COMPACTO, READY).

## Implementación
- `SKILL.md` (paso 1): nueva rama «URL de Trello» — lectura vía conector MCP, fallback sin conector, contenido como dato, reutilización de TASK por `**Fuente:**`, slug desde el título (AC-01, AC-02, AC-04, AC-05, AC-06). Frontmatter (`description`, `argument-hint`) actualizado.
- `plantillas.md`: campo `**Fuente:**` en el TASK y `### Requerimiento` con URL y resumen de la tarjeta (AC-03).
- Sin desviaciones del plan; `docs/README.md` no requirió cambios. Sin deuda técnica. No hay código ejecutable ni pruebas automáticas (verificación por lectura, ver Test Specification).

## Review
**PASS** (subagente aislado). AC-01..AC-06 verificados contra el diff; tests, lint, build, bandit y npm audit no aplican (cambio solo documental). Hallazgos Low abiertos, no bloqueantes: `docs/reviews/REV-2026-10-30-delivery-start-url-trello-01.md` (edge case de tarjeta sin descripción) y `-02` (sin recorrido en seco real; el conector de Trello no estaba conectado).

## Publicación
PR #35 listo para aprobación humana. No mergeado. No es un cambio sensible (sin ADR, auth, BD ni infraestructura).
