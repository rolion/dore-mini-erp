---
name: delivery-plan
description: Convierte la investigación y (si existen) las decisiones arquitectónicas de un task en un plan de implementación concreto y ejecutable para este monorepo (praxsa_manager en Django/DRF + proforma en Angular). Lee docs/tasks/TASK-<slug>.md, incorpora los ADR relevantes de docs/adr/, define cambios backend/frontend/base de datos, estrategia de testing (incluyendo el criterio explícito de si corresponde E2E con Playwright), acceptance criteria, edge cases, riesgos y fuera de alcance. Guarda el plan versionado en docs/plans/PLAN-<fecha>-<slug>.md y abre el único Pull Request del task (con el plan como primer contenido, sin código todavía), dejando el enlace registrado en el TASK. Si se le pide una actualización del plan (PLAN_UPDATE_REQUIRED), no sobrescribe en silencio: versiona e incluye un changelog. Respeta las reglas de docs/CLAUDE.md. Se invoca explícitamente con /delivery-plan TASK-<slug>; no debe activarse solo porque el usuario mencione "plan" o "implementar" en una frase suelta.
---

# Delivery Plan

## Por qué existe este skill

`docs/CLAUDE.md` pide: "Antes de cambios que afecten varios archivos, proponer un plan y esperar confirmación." Este skill es esa práctica hecha repetible, y además el punto donde nace el único Pull Request de un task: abre el PR con el plan como contenido inicial, para que un humano pueda revisarlo y aprobarlo antes de que exista una sola línea de código de implementación. `delivery-engineer` seguirá empujando commits a esa misma rama/PR — este skill nunca abre un segundo PR para el mismo task.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-plan TASK-<slug>` explícitamente. No lo dispares por tu cuenta al detectar "plan" o "implementar" en una conversación normal.

## Inputs

- `TASK-<slug>` con `## Investigación` completa (y `## Arquitectura` completa si el veredicto fue `NEEDS_ARCHITECTURE`).

## Outputs

- `docs/plans/PLAN-<fecha>-<slug>.md`, versionado (`v1`, `v2`, ...).
- El Pull Request único del task, abierto (primera vez) o actualizado con un nuevo commit (actualizaciones posteriores).
- `docs/tasks/TASK-<slug>.md` actualizado: sección `## Plan`, rama, enlace al PR, historial.

## Flujo

### 1. Leer el TASK y verificar que está listo para planificar

Lee `docs/tasks/TASK-<slug>.md`. Reglas de entrada:
- Si `## Investigación` está vacía o dice "Pendiente": detente, pide correr `/delivery-investigate TASK-<slug>` primero.
- Si el veredicto de complejidad es `TRIVIAL_FIX`: este skill no aplica — ese camino va directo a `delivery-engineer`. Dilo y detente.
- Si `**Diseño requerido:**` es `SI` y `## Diseño` sigue "Pendiente": detente, pide correr `/delivery-design TASK-<slug>` primero.
- Si el veredicto es `NEEDS_ARCHITECTURE` y `## Arquitectura` sigue "Pendiente": detente, pide correr `/delivery-architect TASK-<slug>` primero.

### 2. Analizar la tarea con criterio de arquitecto/planner senior

Parte de la investigación y los ADR ya existentes — no repitas la exploración de código desde cero. Sí verifica que lo citado siga vigente: el código pudo cambiar entre la investigación y ahora (¿el archivo sigue en esa ruta? ¿la función sigue con esa firma?). Si algo no cuadra, dilo en el plan como una nota, no lo ignores en silencio.

Si algo queda genuinamente ambiguo para poder planificar (más de una interpretación razonable, un caso borde que cambiaría la solución, falta un dato de negocio que no está ni en la investigación ni en los ADR), pregunta antes de seguir.

### 3. Evaluar consideraciones de arquitectura propias del plan

Aunque el veredicto haya sido `NEEDS_PLAN` (sin `delivery-architect` de por medio), todo plan incluye una sección de arquitectura — a este nivel, más liviana. Revisa activamente:
- **Contrato API**: ¿rompe algo que Angular ya consume? ¿hay que coordinar despliegue backend/frontend?
- **Datos existentes**: ¿una migración puede fallar o dejar datos inconsistentes?
- **Dinero y precisión**: todo cálculo de precios/pagos en `Decimal`, nunca `float`.
- **Rendimiento**: consultas N+1, cálculos en loop sobre inventario/proformas.
- **Seguridad y permisos**: vistas de admin o endpoints que deberían estar restringidos.
- **Acoplamiento**: dada la deuda técnica conocida, ¿tocar este archivo tiene efectos secundarios en otra parte?
- **Consistencia visual**: si el task sí pasó por `delivery-design`, los componentes/patrones ya están decididos en el DDR — no los reinventes acá, solo tradúcelos a pasos de implementación.

Si el task sí pasó por `delivery-architect`, esta sección resume las decisiones de los ADR relevantes en vez de re-derivarlas.

### 4. Definir la estrategia de testing con criterio explícito de E2E

No agregues E2E con Playwright por reflejo. Justifica explícitamente sí o no:
- **Sí corresponde E2E** cuando el cambio afecta un flujo crítico de usuario de punta a punta (ej. login → elegir sucursal → generar proforma → pago), cambia navegación o un formulario multi-paso, o depende de la integración real entre frontend y backend de una forma que un test de integración aislado no puede validar.
- **No corresponde E2E** en el resto de los casos — dilo explícitamente con el motivo, no lo omitas.
- Este proyecto no tiene Playwright instalado en `proforma/package.json` todavía. Si el plan concluye que sí hace falta E2E, marca la instalación de Playwright en "Dependencias nuevas" — es una dependencia nueva que requiere confirmación antes de que `delivery-engineer` la instale.
- Para el resto de los casos, define si corresponde nivel unitario, de integración, o ambos, siguiendo los patrones ya usados (`praxsa_manager/product/tests/` con `helpers.py`; Angular con `TestBed` + `HttpTestingController`).

### 5. Escribir el plan

Calcula el slug de la tarea (kebab-case corto) y la fecha de hoy. Guarda como `docs/plans/PLAN-<YYYY-MM-DD>-<slug>.md`, versión `v1`. Si `## Plan` en el TASK ya apunta a un plan existente para este mismo task, ver paso 7 (actualización) en vez de crear uno nuevo.

```markdown
# PLAN-<fecha>-<slug> (v1)

**Task:** TASK-<slug>
**DDRs relacionados:** <lista, o "Ninguno">
**ADRs relacionados:** <lista, o "Ninguno">

## Objective
Qué se quiere lograr y por qué, en 1-3 frases.

## Context
Resumen de la investigación relevante (referencia TASK-<slug> en vez de copiar todo).

## Current behavior
Cómo funciona hoy, con `archivo:línea`.

## Expected behavior
Qué debería pasar después del cambio.

## Architecture considerations
Ver paso 3 — o resumen de los ADR aplicables.

## Proposed solution
La solución concreta elegida (y, si hubo alternativas evaluadas por `delivery-architect`, por qué esta).

## Files/components affected
Lista de archivos/módulos identificados, backend y frontend por separado.

## Implementation steps
Lista ordenada y pequeña, cada paso verificable. Tareas grandes se dividen en fases.

## Test strategy
Casos concretos por nivel (unit/integración/E2E), con la justificación explícita de E2E sí/no del paso 4. Si un paso de implementación cambia lógica de negocio sin un caso de prueba correspondiente aquí, el plan está incompleto.

## Acceptance criteria
Lista verificable de condiciones que deben cumplirse para considerar la tarea terminada.

## Risks
Riesgos identificados y su mitigación si la tiene. Si no la tiene, decirlo explícitamente.

## Out of scope
Qué queda deliberadamente fuera, y preguntas abiertas para el usuario.

## Dependencias nuevas
Si aplica, qué se necesita instalar — requiere confirmación antes de que `delivery-engineer` lo instale. Omitir la sección si no aplica.
```

### 6. Abrir el PR único del task

Si `**Pull Request:**` en el TASK ya tiene un enlace, salta al paso 7 — no abras un segundo PR.

1. Revisa el estado del repo (`git status`) y no descartes trabajo sin comitear ajeno.
2. Trae `origin/master` actualizado y crea la rama `task/TASK-<slug>` desde ahí (el nombre del task ya es descriptivo, no le agregues otro slug encima).
3. Comitea únicamente el archivo del plan (y el TASK actualizado si vive en la misma rama de trabajo — normalmente el TASK se mantiene en la rama por defecto del repo si así lo prefiere el equipo; si no es obvio, pregunta). Mensaje de commit corto referenciando el plan.
4. `git push` y abre el PR contra la rama base (normalmente `master`) con este cuerpo inicial:

```markdown
## Summary
<resumen de una línea de la tarea>

## Task
TASK-<slug> (docs/tasks/TASK-<slug>.md)

## Plan
docs/plans/PLAN-<fecha>-<slug>.md (v1)

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

### 7. Si es una actualización (PLAN_UPDATE_REQUIRED): versionar, no sobrescribir

Cuando te invoquen porque `delivery-engineer` o `delivery-review` reportaron un problema de plan:
1. Incrementa la versión en el encabezado del documento (`v1` → `v2`, etc.).
2. Aplica los cambios necesarios al cuerpo del plan.
3. Agrega al final una sección `## Changelog` (o una entrada más si ya existe):

```markdown
## Changelog
- **v2** (<fecha>): <motivo del cambio>. Solicitado por <delivery-engineer | delivery-review, referenciando REV-<fecha>-<task-slug>-<seq> si aplica>.
```

4. Comitea y **empuja a la misma rama** del PR ya abierto — nunca crees un PR nuevo. Actualiza el número de versión en `## Plan` del PR (`gh pr edit`) si el enlace de versión aparece ahí.

### 8. Actualizar el TASK

Actualiza `## Plan` (enlace + versión vigente), `**Rama:**`, `**Pull Request:**` (si es la primera vez), agrega la fila al historial (`PLANNING → PLANNING` con motivo si es una actualización, o `ARCHITECTURE/INVESTIGATION → PLANNING` si es la primera vez seguida de `PLANNING → ENGINEERING` cuando corresponda entregarlo), y ajusta `**Etapa actual:**` a `ENGINEERING` una vez el plan está listo para implementarse.

### 9. Presentar y detener

Resume el plan en el chat (no repitas el archivo completo), incluye el enlace del PR, y pregunta si se puede proceder o si hay que ajustar algo. **No asumas la aprobación del plan como automática ni invoques `delivery-engineer` tú mismo.**

## Reglas

- Nunca abre un segundo PR para el mismo task — siempre reutiliza el registrado en `**Pull Request:**` del TASK.
- Nunca sobrescribe un plan existente sin versionar y sin changelog.
- No implementa código.
- Toda decisión de testing declara explícitamente si corresponde E2E y por qué.

## Cuándo detenerse

- Investigación o arquitectura del task están incompletas para el veredicto emitido.
- Ambigüedad real de negocio que no se resuelve con lo ya documentado.
- No queda claro si el TASK y el código de trabajo (rama) deben vivir juntos o el usuario tiene una convención distinta.

## Cuándo delega a otra skill

Siempre termina delegando a `delivery-engineer` (nunca implementa). Si durante el análisis descubre que en realidad la tarea necesita una decisión arquitectónica que `delivery-investigate` no detectó, debe detenerse y sugerir `/delivery-architect TASK-<slug>` en su lugar, dejando constancia en el TASK de por qué.
