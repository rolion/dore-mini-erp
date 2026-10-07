---
name: delivery-plan
description: Consolida la investigación, el DDR (si existe) y los ADR (si existen) de un task en una Specification autoritativa y verificable (QUÉ debe ser verdad al terminar) y luego produce un Implementation Plan ejecutable (CÓMO se implementará) para este monorepo (`backend/` en Django/DRF + `frontend/panel_admin/` en Angular). Lee docs/tasks/TASK-<slug>.md, incorpora DDR de docs/design/ y ADR de docs/adr/, y define lenguaje ubicuo, invariantes, acceptance criteria con identificadores verificables, edge/error cases, permisos, contrato API/UI según aplique, estrategia de testing derivada de la Specification (incluyendo el criterio explícito de si corresponde E2E con Playwright), cambios backend/frontend/base de datos, riesgos y fuera de alcance. Evalúa Specification readiness (READY | BLOCKED) y no entrega plan listo si hay ambigüedad de negocio. Guarda el documento versionado en docs/plans/PLAN-<fecha>-<slug>.md y abre el único Pull Request del task (con Specification + Plan como primer contenido, sin código todavía), dejando el enlace registrado en el TASK. Si se le pide una actualización (PLAN_UPDATE_REQUIRED), no sobrescribe en silencio: versiona e incluye un changelog que indica si cambió la Specification o solo el Implementation Plan. Respeta las reglas de docs/CLAUDE.md. Se invoca explícitamente con /delivery-plan TASK-<slug>; no debe activarse solo porque el usuario mencione "plan" o "implementar" en una frase suelta.
---

# Delivery Plan

## Por qué existe este skill

`CLAUDE.md` del proyecto (si existe) o la práctica del equipo pide: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación." Este skill es esa práctica hecha repetible, y además el punto donde nace el único Pull Request de un task: abre el PR con la Specification y el Implementation Plan como contenido inicial, para que un humano pueda revisarlos y aprobarlos antes de que exista una sola línea de código de implementación. `delivery-engineer` seguirá empujando commits a esa misma rama/PR — este skill nunca abre un segundo PR para el mismo task.

## Filosofía

Consolidar la investigación, las decisiones de diseño y las decisiones arquitectónicas en una **Specification** autoritativa y verificable, y luego producir un **Implementation Plan** ejecutable que implemente esa Specification.

- **Specification** = QUÉ debe ser verdad cuando la tarea esté completa. Es el contrato contra el cual `delivery-engineer` implementa y `delivery-review` verifica.
- **Implementation Plan** = CÓMO el equipo pretende implementar esa Specification.

Separación de responsabilidades en el flujo (este skill no la rompe):

| Etapa | Responsabilidad |
|---|---|
| `delivery-investigate` | Descubre hechos |
| `delivery-design` | Decide comportamiento UX (DDR) |
| `delivery-architect` | Decide estructura técnica (ADR) |
| **`delivery-plan`** | Consolida esas decisiones en una Specification y define cómo implementarla |
| `delivery-engineer` | Implementa la solución siguiendo el Implementation Plan, sin violar la Specification |
| `delivery-review` | Verifica conformidad |

Este skill **no reinterpreta** decisiones ya tomadas por DDR o ADR: son restricciones, no sugerencias.

## Principios

1. La Specification define la corrección.
2. El Implementation Plan define la ejecución prevista.
3. Los tests verifican la Specification, no detalles de implementación.
4. Nunca inventes reglas de negocio.
5. Nunca resuelvas en silencio una ambigüedad de dominio.
6. Las decisiones existentes de DDR y ADR son restricciones, no sugerencias.
7. Los hechos de la investigación no se reescriben como suposiciones.
8. Una implementación correcta de una Specification equivocada sigue siendo un fallo.
9. Desviarse del Implementation Plan no es automáticamente un defecto si la Specification sigue satisfecha, pero debe explicarse y revisarse.
10. Las tareas pequeñas se mantienen livianas: evita ceremonia que no aporta valor.

## Proporcionalidad (importante)

No conviertas cada tarea en un documento enorme. Escala el documento a la complejidad:

- Tarea simple → Specification corta; omite las secciones que no aplican (no dejes secciones vacías ni "N/A" de relleno).
- No generes API/UI/permisos/DDD si no aplican.
- Given/When/Then solo cuando ayude, no por obligación.
- Identificadores (AC-, INV-, EDGE-, UI-, API-) solo cuando mejoren la trazabilidad; no uno por frase.
- `TRIVIAL_FIX` sigue sin pasar por este skill.
- La estructura completa se usa cuando la complejidad lo justifica.

## Modo del documento: COMPACTO o COMPLETO

Antes de escribir, elige el modo y decláralo en el encabezado del PLAN con la convención única `**Modo:** COMPACTO` o `**Modo:** COMPLETO` (y repítelo en la sección `## Specification / Plan` del PR). `delivery-engineer` y `delivery-review` leen este valor para saber por qué ciertas secciones pueden no existir. `TRIVIAL_FIX` no entra aquí: sigue yendo directo a `delivery-engineer`.

**Esta sección es la única fuente de los criterios de modo.** `delivery-engineer` y `delivery-review` los referencian, no los copian.

### Criterio de selección: tres ejes

Basta **un** eje activo para exigir COMPLETO:

1. **Domain behavior affected** — reglas de dominio nuevas o modificadas: invariantes, transiciones de estado de un agregado, cálculos, políticas de negocio, reglas ambiguas. Incluye la lógica financiera con peso de negocio (cálculos, fórmulas, redondeo, precisión, currency handling, pagos, saldos, descuentos, impuestos, reembolsos, reversos, consecuencias contables). Una regla de negocio va al dominio; la validación de forma y tipos del serializer no cuenta.
   - **Excepción (regla simple y local → puede seguir COMPACTO)** solo si se cumplen *todas*: la regla es simple y no ambigua; es local a un único bounded context; no introduce nuevas transiciones de estado; no cambia invariantes centrales; no afecta permisos, finanzas, contratos ni límites entre contextos; y se expresa con 1–2 acceptance criteria claros. Ejemplo COMPACTO: "no permitir guardar un producto con cantidad negativa" sobre un flujo existente.
   - **COMPLETO obligatorio** si la regla cambia una invariante, agrega una transición de estado, afecta varias entidades/agregados, introduce ambigüedad de negocio o tiene consecuencias relevantes fuera del flujo local. Ejemplo COMPLETO: "una venta confirmada ahora puede cancelarse y debe revertir inventario".
2. **Frontera cruzada** — dos o más bounded contexts afectados, una dependencia nueva entre módulos, o un dato que ahora viaja entre contextos. Consumir sin cambios una interfaz ya existente no cuenta.
3. **Contrato o datos con costo de reversa** — cambio de contrato API, migración riesgosa, cambio de permisos/autorización, decisión arquitectónica (ADR / `NEEDS_ARCHITECTURE`), o un DDR con impacto visual relevante.

**COMPACTO** — solo si ningún eje está activo, salvo la excepción de regla simple y local del eje 1 (veredicto `NEEDS_PLAN`). Típicamente: un campo pasivo sin reglas, un ajuste de UI, un endpoint CRUD dentro de un solo contexto, mostrar un importe o transportar un `Decimal` existente.

**No fuerzan COMPLETO por sí solos:** tocar más de un archivo; frontend + backend de forma sencilla; un campo `Decimal` o un precio mostrado sin cambiar su lógica; tests de integración; varias capas dentro del mismo bounded context. Tampoco infles el modo por exceso de precaución. Pero **ante duda real entre ambos, elige COMPLETO.** El dinero siempre se maneja en `Decimal`, nunca `float`, en cualquiera de los dos modos.

### Upgrade COMPACTO → COMPLETO

Si el plan es COMPACTO y aparece una condición de cualquiera de los tres ejes (por ti al actualizar, o reportada por `delivery-engineer` / `delivery-review` mediante `PLAN_UPDATE_REQUIRED`), **no sigas agregando excepciones al plan COMPACTO**. Haz el upgrade formal:

- el mismo archivo `PLAN-*.md`, con nueva versión (`vN+1`) — nunca un plan nuevo ni un PR nuevo (mismo task, misma rama, mismo PR);
- cambia el encabezado a `**Modo:** COMPLETO` y expande a la plantilla completa;
- entrada de changelog, por ejemplo: `v2: [Implementation Plan] Plan upgraded from COMPACT to FULL after <delivery-engineer | delivery-review> identified <razón>.`;
- actualiza el modo en el PR (`gh pr edit`);
- el upgrade es un cambio **estructural** del documento y no requiere aprobación por sí mismo. Si el motivo del upgrade implica cambiar comportamiento, reglas de negocio, AC, permisos o contrato (cambio de Specification), ese cambio sí requiere aprobación explícita del usuario (ver paso 8) y se registra como entrada separada `[Specification]`.

**No parchees un plan COMPACTO hasta convertirlo de facto en COMPLETO.** Regla medible: si una actualización necesita agregar dos o más secciones exclusivas de COMPLETO (por ejemplo ubiquitous language, domain rules/invariants, API contract, authorization, architecture considerations), o una sola de ellas por una condición de los tres ejes, haz el upgrade formal. *Do not patch a COMPACT plan into a FULL plan incrementally. Upgrade the mode explicitly.*

Plantilla COMPACTO (todo en 1-2 pantallas; añade una sección de la plantilla completa solo si hace falta):

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

El modo COMPACTO conserva los mismos principios: Specification antes que plan, ningún AC sin verificación, BLOCKED ante ambigüedad, versionado, changelog y PR único. Un plan COMPACTO legítimo **no** es un plan incompleto por carecer de las secciones propias de COMPLETO.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-plan TASK-<slug>` explícitamente. No lo dispares por tu cuenta al detectar "plan" o "implementar" en una conversación normal.

## Inputs

- `TASK-<slug>` con `## Investigación` completa (y `## Arquitectura` completa si el veredicto fue `NEEDS_ARCHITECTURE`).
- DDR relacionados (`docs/design/DDR-*.md`) si `delivery-design` participó.
- ADR relacionados (`docs/adr/ADR-*.md`) si `delivery-architect` participó.
- `docs/architecture/ddd.md` como referencia de bounded contexts y restricciones DDD.

## Outputs

- `docs/plans/PLAN-<fecha>-<slug>.md` (Specification + Implementation Plan), versionado (`v1`, `v2`, ...).
- El Pull Request único del task, abierto (primera vez) o actualizado con un nuevo commit (actualizaciones posteriores).
- `docs/tasks/TASK-<slug>.md` actualizado: sección `## Plan`, rama, enlace al PR, historial.

## Flujo

### 1. Leer el TASK y verificar que está listo para planificar

Lee `docs/tasks/TASK-<slug>.md`. Reglas de entrada:
- Si `## Investigación` está vacía o dice "Pendiente": detente, pide correr `/delivery-investigate TASK-<slug>` primero.
- Si el veredicto de complejidad es `TRIVIAL_FIX`: este skill no aplica — ese camino va directo a `delivery-engineer`. Dilo y detente.
- Si `**Diseño requerido:**` es `SI` y `## Diseño` sigue "Pendiente": detente, pide correr `/delivery-design TASK-<slug>` primero.
- Si el veredicto es `NEEDS_ARCHITECTURE` y `## Arquitectura` sigue "Pendiente": detente, pide correr `/delivery-architect TASK-<slug>` primero.

### 2. Consolidar fuentes y verificar vigencia

Parte de la investigación, los DDR y los ADR existentes — no repitas la exploración de código desde cero. Sí verifica que lo citado siga vigente: el código pudo cambiar entre la investigación y ahora (¿el archivo sigue en esa ruta? ¿la función sigue con esa firma?). Si algo no cuadra, dilo en el documento como una nota, no lo ignores en silencio. Los hechos de la investigación se citan como hechos; no los reformules como suposiciones.

Lee también `docs/architecture/ddd.md`. Sus restricciones (bounded contexts, dominio sin Django/infraestructura, módulos sin importarse infraestructura entre sí, Reporting solo lectura, estados cambiados por métodos del agregado) se tratan como parte de la Specification / restricciones de arquitectura. DDD es una preocupación transversal, no una etapa nueva.

### 3. Detectar ambigüedad y calcular Specification readiness

Antes de escribir la versión final, evalúa:

**Specification readiness:** `READY` | `BLOCKED`

- `READY`: el comportamiento esperado está suficientemente definido para implementar.
- `BLOCKED`: existe una ambigüedad de negocio o de comportamiento que podría producir implementaciones razonables pero distintas. Ejemplo: "el requisito dice que una factura completada puede cancelarse, pero no define si cancelar significa eliminar, anular o revertir financieramente".

Si una pregunta cambia comportamiento de negocio, acceptance criteria, arquitectura o contrato API → es bloqueante: detente y pide aclaración **antes** de producir el plan final. Solo pueden quedar como `Open questions` las que no bloquean la implementación.

En `BLOCKED`:
- no abras ni actualices el PR como listo para ENGINEERING ni muevas la etapa a `ENGINEERING`;
- documenta las preguntas abiertas (en el TASK y en el chat; puedes dejar un borrador del documento marcado `BLOCKED` si ayuda al usuario a responder);
- pide aclaración al usuario;
- no inventes una decisión.

Si detectas inconsistencias semánticas entre requisito, UI, API o modelo de dominio, decláralas explícitamente en el documento (ver *Ubiquitous language*). No las resuelvas en silencio.

### 4. Evaluar consideraciones de arquitectura propias del plan

Aunque el veredicto haya sido `NEEDS_PLAN` (sin `delivery-architect` de por medio), todo plan incluye una sección de arquitectura — a este nivel, más liviana. Revisa activamente:
- **Contrato API**: ¿rompe algo que Angular ya consume? ¿hay que coordinar despliegue backend/frontend?
- **Datos existentes**: ¿una migración puede fallar o dejar datos inconsistentes?
- **Dinero y precisión**: todo cálculo de precios/pagos en `Decimal`, nunca `float`.
- **Rendimiento**: consultas N+1, cálculos en loop sobre grandes conjuntos de datos.
- **Seguridad y permisos**: vistas de admin o endpoints que deberían estar restringidos.
- **Acoplamiento**: ¿tocar este archivo tiene efectos secundarios en otra parte?
- **Consistencia visual**: si el task pasó por `delivery-design`, los componentes/patrones ya están decididos en el DDR — no los reinventes, tradúcelos a `UI behavior` y a pasos de implementación.
- **Cumplimiento de ADR**: si existen, resúmelos y respétalos. No reabras decisiones arquitectónicas salvo contradicción real; si la detectas, detente y escala a `/delivery-architect TASK-<slug>`.

### 5. Definir la estrategia de testing derivada de la Specification

Los tests se derivan de la Specification (acceptance criteria, invariantes, edge/error cases), no solo de los pasos de implementación. Cada acceptance criterion debe tener una verificación asignada.

No agregues E2E con Playwright por reflejo. Justifica explícitamente sí o no:
- **Sí corresponde E2E** cuando el cambio afecta un flujo crítico de usuario de punta a punta (ej. login → flujo principal de negocio → confirmación), cambia navegación o un formulario multi-paso, o depende de la integración real entre frontend y backend de una forma que un test de integración aislado no puede validar.
- **No corresponde E2E** en el resto de los casos — dilo explícitamente con el motivo, no lo omitas.
- Verifica si Playwright ya está en `frontend/panel_admin/package.json`; si no lo está y el plan concluye que sí hace falta E2E, marca la instalación de Playwright en "New dependencies" — es una dependencia nueva que requiere confirmación antes de que `delivery-engineer` la instale.
- Para el resto de los casos, define si corresponde nivel unitario, de integración, o ambos, siguiendo los patrones ya usados (tests del backend en `backend/`; Angular con `TestBed` + `HttpTestingController`).
- Cada nueva regla de negocio lleva tests correspondientes cuando sea razonable. Identifica también comportamiento existente que podría romperse (regresión).

### 6. Escribir el documento

Calcula el slug de la tarea (kebab-case corto) y la fecha de hoy. Guarda como `docs/plans/PLAN-<YYYY-MM-DD>-<slug>.md`, versión `v1`. Si `## Plan` en el TASK ya apunta a un documento existente para este mismo task, ver paso 8 (actualización) en vez de crear uno nuevo.

Si el modo es COMPACTO, usa la plantilla corta de la sección *Modo del documento*. Si es COMPLETO, usa esta plantilla (añade `**Modo:** COMPLETO` al encabezado). **Omite cualquier sección que no aplique** (según *Proporcionalidad*); no dejes encabezados vacíos.

```markdown
# PLAN-<fecha>-<slug> (v1)

**Task:** TASK-<slug>
**Modo:** COMPLETO
**DDRs relacionados:** <lista, o "Ninguno">
**ADRs relacionados:** <lista, o "Ninguno">
**Specification readiness:** READY | BLOCKED

## Objective
Objetivo de negocio/técnico en 1-3 frases.

## Context
Resumen de la investigación relevante (referencia TASK-<slug> en vez de copiar todo).

# Specification

## Domain context
**Bounded Context:** <p. ej. Sales>
**Related contexts:** <solo los confirmados por la investigación y docs/architecture/ddd.md>
No inventar contextos.

## Ubiquitous language
| Term | Meaning | Source |
|---|---|---|
| <término> | <significado> | TASK / código / DDR / ADR |

Inconsistencias entre requisito, UI, API o modelo de dominio: declararlas aquí explícitamente. No resolverlas en silencio.

## Current behavior
Cómo funciona hoy, basado en la investigación, con `archivo:línea`.

## Expected behavior
Qué comportamiento debe existir después del cambio. Describe comportamiento, no pasos de implementación.

## Domain rules / invariants
Distingue **existentes** (ya verdaderas, deben seguir siéndolo) de **nuevas** (requeridas por la tarea).
- INV-01: ...
No inventar reglas de negocio. Si una regla necesaria es ambigua: detenerse y preguntar.

## Acceptance criteria
Cada criterio es observable, verificable e independiente de detalles de implementación innecesarios.
- AC-01: Given ... When ... Then ...  (Given/When/Then solo cuando ayude)

## Edge cases
- EDGE-01: ...

## Error cases
Comportamiento ante inputs inválidos, conflictos, recursos inexistentes, permisos insuficientes. Solo si aplican.

## Authorization / permissions
Quién puede ejecutar la acción, quién solo visualiza, qué pasa sin privilegios. Alineado con decisiones existentes del sistema. Solo si aplica.

## API contract
Solo si la tarea afecta API.
- API-01: endpoint, request, response, status codes, compatibilidad hacia atrás, campos nuevos/modificados/eliminados.
No inventar schemas que aún no estén decididos.

## UI behavior
Solo si hay impacto visual. Derivado del DDR si `delivery-design` participó (no rediseñar el DDR).
- UI-01: estados, visibilidad, navegación, loading, empty state, error state, permisos relevantes.

## Non-functional requirements
Solo los que aplican: performance, security, auditability, concurrency, precision, accessibility, backward compatibility.

## Out of scope
Qué NO debe modificar esta tarea.

## Open questions
Solo preguntas que NO bloquean la implementación. Las bloqueantes impiden producir el plan final (ver paso 3).

# Test Specification

## Unit tests
Reglas/unidades a probar; cada nueva regla de negocio con sus tests cuando sea razonable.

## Integration tests
Contratos o interacciones que requieren validación integrada.

## E2E
**¿Corresponde E2E?** SÍ | NO — justificación explícita (ver paso 5).

## Regression tests
Comportamiento existente que el cambio podría romper.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Backend integration test |
| AC-02 | Angular unit test |

Ningún acceptance criterion queda sin estrategia de validación.

# Implementation Plan

## Architecture considerations
Ver paso 4 — o resumen de los ADR aplicables y de las restricciones de `docs/architecture/ddd.md`.

## Proposed solution
La solución técnica elegida (y, si hubo alternativas evaluadas por `delivery-architect`, por qué esta). Debe demostrar cómo satisface la Specification.

## Files/components affected
- Backend
- Frontend
- Database/migrations
- Tests
- Documentation

## Implementation steps
Pasos pequeños, ordenados y verificables; tareas grandes se dividen en fases. Cada paso referencia, cuando tenga sentido, qué parte de la Specification satisface. Ejemplo:
1. Agregar validación en el servicio de aplicación (AC-02, INV-01).
2. Exponer el comportamiento por el endpoint existente (API-01).
3. Actualizar el componente Angular (UI-02).
4. Agregar tests para AC-01, AC-02 y regresión.

Si un paso cambia lógica de negocio sin un test correspondiente en la Test Specification, el documento está incompleto.

## Database / migrations
Si aplica: migración requerida, compatibilidad con datos existentes, consideraciones de rollback, backfill. (Nunca editar una migración ya aplicada: nueva con `makemigrations`.)

## Risks
Riesgos técnicos conocidos y su mitigación. Si no hay mitigación, decirlo explícitamente.

## New dependencies
Si aplica, qué se necesita instalar — requiere confirmación del usuario antes de que `delivery-engineer` lo instale. Omitir si no aplica.

## Changelog
(Solo desde v2; ver paso 8.)
```

Los identificadores (AC-, INV-, EDGE-, UI-, API-) existen para trazar: Specification → Implementation Plan → Tests → Review findings. Úsalos cuando ese objetivo se cumpla; en tareas pequeñas omítelos.

### 7. Abrir el PR único del task

**Solo si `Specification readiness` es `READY`.** Si es `BLOCKED`, no abras PR ni cambies a ENGINEERING (paso 3).

Si `**Pull Request:**` en el TASK ya tiene un enlace, salta al paso 8 — no abras un segundo PR.

1. Revisa el estado del repo (`git status`) y no descartes trabajo sin comitear ajeno.
2. Trae `origin/main` actualizado y crea la rama `task/TASK-<slug>` desde ahí (el nombre del task ya es descriptivo, no le agregues otro slug encima).
3. Comitea únicamente el archivo del documento (y el TASK actualizado si vive en la misma rama de trabajo — normalmente el TASK se mantiene en la rama por defecto del repo si así lo prefiere el equipo; si no es obvio, pregunta). Mensaje de commit corto referenciando el plan.
4. `git push` y abre el PR contra la rama base (normalmente `main`) con este cuerpo inicial:

```markdown
## Summary
<resumen de una línea de la tarea>

## Task
TASK-<slug> (docs/tasks/TASK-<slug>.md)

## Specification / Plan
docs/plans/PLAN-<fecha>-<slug>.md (v1) · Modo: <COMPACTO | COMPLETO>

## DDRs relacionados
- <enlace a cada DDR, o "Ninguno">

## ADRs relacionados
- <enlace a cada ADR, o "Ninguno">

## Changes
_Pendiente de implementación (delivery-engineer)_

## Testing
_Pendiente (delivery-review)_

## Review
_Pendiente (delivery-review)_

## Known limitations
_Ninguna conocida todavía_
```

El título del PR debe referenciar el task: `TASK-<slug>: <título corto>`. Este cuerpo es un contrato entre skills: cada una edita solo su propia sección (`delivery-engineer` → `## Changes`, `delivery-review` → `## Testing` y `## Review`, `delivery-publish` → `## Summary` y `## Known limitations` al cerrar). No pises secciones que no te correspondan.

### 8. Si es una actualización (PLAN_UPDATE_REQUIRED): versionar, no sobrescribir

Cuando te invoquen porque `delivery-engineer` o `delivery-review` reportaron un problema, o porque el usuario resolvió una pregunta bloqueante:
1. Incrementa la versión en el encabezado del documento (`v1` → `v2`, etc.).
2. Clasifica el cambio y comprueba si el modo sigue siendo válido (si no, aplica el *Upgrade COMPACTO → COMPLETO*):
   - **Implementation Plan change** (un paso incorrecto, archivos, estrategia de tests, con la Specification válida): puede ser propuesto por `delivery-engineer` o `delivery-review` y procesarse aquí sin aprobación adicional.
   - **Specification change** (comportamiento esperado, acceptance criteria, reglas de negocio, permisos, contrato funcional): **requiere aprobación explícita del usuario antes de actualizar la Specification.** Ni `delivery-engineer` ni `delivery-review` pueden cambiarla por su cuenta, y tú tampoco la reinterpretas: pregunta, espera la decisión y luego aplícala.
3. Agrega al final una sección `## Changelog` (o una entrada más si ya existe), diferenciando siempre ambos tipos de cambio:

```markdown
## Changelog
- **v2** (<fecha>): [Implementation Plan] <motivo>. Solicitado por <delivery-engineer | delivery-review, referenciando REV-<fecha>-<task-slug>-<seq> si aplica>.
- **v3** (<fecha>): [Implementation Plan] Plan upgraded from COMPACT to FULL after <delivery-engineer | delivery-review> identified <razón>.
- **v4** (<fecha>): [Specification] AC-03 changed after explicit user approval. Solicitado por <quién>.
```

4. Comitea y **empuja a la misma rama** del PR ya abierto — nunca crees un PR nuevo. Actualiza el número de versión en `## Specification / Plan` del PR (`gh pr edit`) si el enlace de versión aparece ahí.

### 9. Actualizar el TASK

Actualiza `## Plan` (enlace + versión vigente + readiness), `**Rama:**`, `**Pull Request:**` (si es la primera vez), agrega la fila al historial (`PLANNING → PLANNING` con motivo si es una actualización, o `ARCHITECTURE/INVESTIGATION → PLANNING` si es la primera vez seguida de `PLANNING → ENGINEERING` cuando corresponda entregarlo), y ajusta `**Etapa actual:**` a `ENGINEERING` solo si la Specification está `READY`. Si está `BLOCKED`, la etapa se mantiene en `PLANNING` y se registran las preguntas abiertas.

### 10. Presentar y detener

Resume la Specification y el plan en el chat (no repitas el archivo completo), incluye el enlace del PR, y pregunta si se puede proceder o si hay que ajustar algo. **No asumas la aprobación como automática ni invoques `delivery-engineer` tú mismo.**

## Relación con delivery-engineer

`delivery-engineer` implementa la solución siguiendo el Implementation Plan, sin violar la Specification. Si durante la implementación:
- un paso del Implementation Plan resulta incorrecto pero la Specification sigue válida → `PLAN_UPDATE_REQUIRED` (este skill versiona el plan);
- se detecta una condición de los tres ejes en un plan COMPACTO → `PLAN_UPDATE_REQUIRED` para el upgrade a COMPLETO; el Engineer no lo realiza ni expande la Specification;
- un acceptance criterion o regla de negocio parece incorrecto o ambiguo → el Engineer **no** lo reinterpreta: escala (se resuelve con el usuario y se actualiza la Specification vía este skill, con aprobación explícita);
- un ADR resulta incompatible → escala a `delivery-architect`.

## Preparación para delivery-review

El documento está estructurado para que `delivery-review` pueda verificar: (1) cumplimiento de la Specification, (2) acceptance criteria, (3) invariantes de dominio, (4) contratos API/UI, (5) edge/error cases, (6) tests planificados, (7) desviaciones del Implementation Plan, (8) cumplimiento de ADR/DDR. Los identificadores (cuando existen) y la tabla *Acceptance criteria mapping* existen para permitir que un hallazgo se clasifique como `SPECIFICATION FAILURE`, `IMPLEMENTATION FAILURE`, `PLAN FAILURE`, `ARCHITECTURE FAILURE` o `DESIGN FAILURE`. Si los AC no llevan ID (los IDs solo se usan con más de 2 criterios), los demás skills los referencian por cita corta del criterio (o su índice como alternativa) y no inventan IDs. `delivery-review` debe leer el `Modo` antes de evaluar completitud.

## Reglas

- Nunca abre un segundo PR para el mismo task — siempre reutiliza el registrado en `**Pull Request:**` del TASK.
- Nunca sobrescribe un documento existente sin versionar y sin changelog; el changelog indica si cambió la Specification o solo el Implementation Plan.
- No implementa código.
- No inventa reglas de negocio ni resuelve ambigüedades de dominio en silencio.
- No reinterpreta DDR ni ADR.
- Toda decisión de testing declara explícitamente si corresponde E2E y por qué.
- Todo acceptance criterion tiene una verificación asignada.
- Todo PLAN declara `**Modo:** COMPACTO | COMPLETO`; el upgrade a COMPLETO es formal (mismo archivo con la versión incrementada, mismo PR, con changelog), nunca por parches incrementales.
- Un cambio de Specification requiere aprobación explícita del usuario; un cambio solo del Implementation Plan no.

## Cuándo detenerse

- Investigación, diseño o arquitectura del task están incompletas para el veredicto emitido.
- `Specification readiness: BLOCKED` (ambigüedad real de negocio, de comportamiento o de contrato API que no se resuelve con lo ya documentado).
- No queda claro si el TASK y el código de trabajo (rama) deben vivir juntos o el usuario tiene una convención distinta.
- Contradicción real con un ADR.

## Cuándo delega a otra skill

Siempre termina delegando a `delivery-engineer` (nunca implementa), salvo que la Specification esté `BLOCKED`. Si durante el análisis descubre que en realidad la tarea necesita una decisión arquitectónica que `delivery-investigate` no detectó, o que un ADR existente contradice la Specification, debe detenerse y sugerir `/delivery-architect TASK-<slug>`, dejando constancia en el TASK de por qué. Si descubre que falta una decisión de UX, sugiere `/delivery-design TASK-<slug>`.
