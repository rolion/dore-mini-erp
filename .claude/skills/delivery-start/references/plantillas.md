# Plantillas del flujo de entrega

Usadas por `delivery-start`, `delivery-build` y `delivery-publish`. Cada skill edita solo sus secciones.

## TASK (`docs/tasks/TASK-<slug>.md`)

```markdown
# TASK-<slug>: <título corto de la tarea>

**Etapa actual:** INVESTIGATION
**Veredicto de complejidad:** <TRIVIAL_FIX | NEEDS_PLAN | NEEDS_ARCHITECTURE>
**Diseño requerido:** <SI | NO>
**Rama:** _sin asignar todavía_
**Pull Request:** _sin abrir todavía_
**Fuente:** <URL de la tarjeta de Trello, si el requerimiento vino de una; omitir la línea si no>

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| <fecha real> | (nuevo) → INVESTIGATION | Task creado | delivery-start |

## Investigación

### Requerimiento
<tal como se recibió, más las aclaraciones del usuario. Si vino de Trello: URL de origen y resumen fiel de la tarjeta (historia, criterios de aceptación, checklists, comentarios relevantes), marcado como insumo y no como Specification aprobada>

### Hechos encontrados
- `archivo:línea` — ...

### Hipótesis / supuestos no confirmados
- ...

### Módulos y dependencias relacionadas
### Implementaciones similares existentes
### Comportamiento actual
### Restricciones
### Riesgos identificados

### Veredicto de complejidad
**<VEREDICTO>** — <justificación>

### Diseño requerido
**<SI | NO>** — <justificación>

## Diseño
_Pendiente / No aplica_

## Arquitectura
_Pendiente / No aplica según veredicto_

## Plan
_Pendiente_

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
```

Etapas válidas de `**Etapa actual:**`: `INVESTIGATION`, `DESIGN`, `ARCHITECTURE`, `PLANNING`, `ENGINEERING`, `REVIEW`, `PUBLISH`, `PUBLISHED`. Fecha siempre real (del sistema), nunca inventada. Al actualizar un TASK no reescribas secciones de etapas posteriores que ya tengan contenido.

## DDR (`docs/design/DDR-<task-slug>-<decision-slug>.md`)

```markdown
# DDR-<task-slug>-<decision-slug>: <título de la decisión>

**Estado:** Propuesto
**Task relacionado:** TASK-<task-slug>
**Fecha:** <fecha real>

## Contexto
## Pantallas/flujos afectados
## Componentes/patrones elegidos
Por pantalla: plantilla de `docs/design/design-system.md` (sección 5) y componentes compartidos; si se sale del sistema, justificación y página de `panel_admin_doc/` o archivo de código.
## Alternativas consideradas
## Comportamiento por privilegio/estado
Nota explícita de lo que debe aplicar el backend (el frontend no es la barrera).
## Consecuencias
Deuda visual aceptada y pantallas que quedarían inconsistentes.
```

## ADR (`docs/adr/ADR-<task-slug>-<decision-slug>.md`)

```markdown
# ADR-<task-slug>-<decision-slug>: <título de la decisión>

**Estado:** Propuesto
**Task relacionado:** TASK-<slug>
**Fecha:** <fecha real>

## Contexto
## Decisión
## Alternativas consideradas
## Estrategia de rollback / mitigación
Si no aplica, justificar.
## Consecuencias
```

## PLAN (`docs/plans/PLAN-<YYYY-MM-DD>-<slug>.md`)

### COMPACTO

```markdown
# PLAN-<fecha>-<slug> (v1)

**Task:** TASK-<slug> · **Modo:** COMPACTO · **Specification readiness:** READY | BLOCKED
**DDRs / ADRs:** <lista, o "Ninguno">

## Objective
1-3 frases.

# Specification
- **Expected behavior:** qué debe ser verdad al terminar (comportamiento, no pasos).
- **Acceptance criteria:** lista corta verificable (IDs AC-xx solo si hay más de 2).
- **Edge/error cases:** solo los relevantes.
- **Out of scope:** qué no se toca.

# Test Specification
Qué se prueba por AC y nivel (unit/integración), más **E2E: NO/SÍ** con una línea de motivo.

# Implementation Plan
- **Files affected:** backend / frontend.
- **Steps:** pasos pequeños y ordenados, referenciando el AC que cumplen.
- **Risks / New dependencies:** solo si hay.
```

### COMPLETO

Mismo encabezado con `**Modo:** COMPLETO`, más (omite lo que no aplique, sin encabezados vacíos):

```markdown
## Objective
## Context            (resumen; referencia al TASK)

# Specification
## Domain context     (Bounded Context y contextos relacionados confirmados)
## Ubiquitous language (tabla Término | Significado | Fuente; inconsistencias declaradas)
## Current behavior   (con archivo:línea)
## Expected behavior
## Domain rules / invariants   (INV-01…; existentes vs. nuevas)
## Acceptance criteria         (AC-01…; Given/When/Then solo si ayuda)
## Edge cases / Error cases
## Authorization / permissions
## API contract       (API-01…; compatibilidad hacia atrás)
## UI behavior        (UI-01…; derivado del DDR y de design-system.md: estados, navegación, plantilla de pantalla)
## Non-functional requirements
## Out of scope
## Open questions     (solo las que no bloquean)

# Test Specification
## Unit tests / Integration tests / E2E (¿corresponde? SÍ|NO + motivo) / Regression tests
## Acceptance criteria mapping   (tabla AC | Verification; ningún AC sin verificación)

# Implementation Plan
## Architecture considerations
## Proposed solution
## Files/components affected   (backend, frontend, migraciones, tests, docs)
## Implementation steps        (pequeños, ordenados, con AC/INV que satisfacen)
## Database / migrations       (nunca editar una migración aplicada)
## Risks
## New dependencies            (requieren confirmación)
## Changelog                   (desde v2)
```

Changelog:

```markdown
- **v2** (<fecha>): [Implementation Plan] <motivo>. Solicitado por <delivery-build | delivery-publish, REV-... si aplica>.
- **v3** (<fecha>): [Implementation Plan] Plan upgraded from COMPACT to FULL after <quién> identified <razón>.
- **v4** (<fecha>): [Specification] AC-03 changed after explicit user approval.
```

## Cuerpo del PR único

Cada skill edita solo su sección: `delivery-start` → Summary inicial, Task, Specification / Plan, DDRs, ADRs; `delivery-build` → Changes; `delivery-publish` → Testing, Review, Architecture decisions, Known limitations y el Summary final.

```markdown
## Summary
<resumen de una línea>

## Task
TASK-<slug> (docs/tasks/TASK-<slug>.md)

## Specification / Plan
docs/plans/PLAN-<fecha>-<slug>.md (v<N>) · Modo: <COMPACTO | COMPLETO>

## DDRs relacionados
- <enlace, o "Ninguno">

## ADRs relacionados
- <enlace, o "Ninguno">

## Changes
_Pendiente de implementación (delivery-build)_

## Testing
_Pendiente (delivery-publish)_

## Review
_Pendiente (delivery-publish)_

## Known limitations
_Ninguna conocida todavía_
```

Para `TRIVIAL_FIX`, `## Specification / Plan` dice: `_No aplica — veredicto TRIVIAL_FIX, ver Investigación en TASK-<slug>_`.
