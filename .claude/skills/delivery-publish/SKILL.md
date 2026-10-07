---
name: delivery-publish
description: Publica únicamente el trabajo de un task (docs/tasks/TASK-<slug>.md) que haya pasado el Quality Gate de delivery-review con veredicto PASS en este monorepo (`backend/` en Django/DRF + `frontend/panel_admin/` en Angular). No crea un PR nuevo: actualiza la descripción del PR único del task (Summary, Changes, Testing con evidencia real, Architecture decisions, Related plan/ADRs, Known limitations) y lo deja listo para aprobación humana final. Verifica que no haya cambios accidentales, archivos temporales, secretos ni cambios fuera de scope. Nunca marca como listo para merge un PR cuyo review terminó en FAIL, y nunca mergea automáticamente cambios de arquitectura, autenticación/autorización, base de datos o infraestructura sin aprobación humana explícita — el auto-merge para veredictos TRIVIAL_FIX de bajo riesgo es una decisión explícita y configurable del equipo, no un comportamiento implícito. Se invoca explícitamente con /delivery-publish TASK-<slug>; no debe activarse solo porque el usuario mencione "publicar" o "subir" en una frase suelta.
---

# Delivery Publish

## Por qué existe este skill

Es la última etapa del flujo: el punto donde se confirma que todo lo acumulado en el PR único del task —plan, ADRs, implementación, review— está completo, coherente y listo para que un humano apruebe el merge. No repite el Quality Gate (eso ya lo hizo `delivery-review`); verifica que su resultado sea `PASS` y que la descripción del PR refleje fielmente la trazabilidad completa del task.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-publish TASK-<slug>` explícitamente.

## Inputs

- `TASK-<slug>` en etapa `PUBLISH` (es decir, `delivery-review` ya emitió `PASS`).

## Outputs

- Descripción del PR único del task actualizada y completa.
- `docs/tasks/TASK-<slug>.md` actualizado: sección `## Publicación`, historial.
- El PR queda señalado como listo para aprobación humana final (nunca mergeado automáticamente, salvo la excepción configurable descrita abajo).

## Flujo

### 1. Verificar que el Quality Gate esté realmente en PASS

Lee `docs/tasks/TASK-<slug>.md`. Si `**Etapa actual:**` no es `PUBLISH`, o `## Review` no muestra `PASS` explícito, detente — no continúes "a ver si igual está bien". Este skill nunca re-decide un `FAIL` de `delivery-review` por su cuenta.

### 2. Verificar que no hay nada fuera de lugar

Sobre la rama del PR:
- `git status` limpio (nada sin comitear que debiera ir en este cambio).
- El diff (`git diff origin/main...HEAD`) corresponde al plan (o a la investigación, en `TRIVIAL_FIX`) — sin archivos que no tengan relación con el task.
- Sin archivos temporales (`.tmp`, logs de debug, artefactos de build que no deberían versionarse).
- Sin secretos: revisa que no se haya comiteado nada de `.env`, credenciales, tokens o claves — si algo así aparece en el diff, detente y avisa, no lo publiques ni lo remuevas tú mismo sin confirmar con el usuario cómo manejarlo (puede requerir rotar la credencial expuesta, no solo borrarla del commit).
- Sin cambios fuera de scope que `delivery-review` no haya evaluado ya (si el review es de un commit anterior y hay commits nuevos sin revisar, detente y pide una nueva pasada de `delivery-review`).

### 3. Completar la descripción del PR

Actualiza (`gh pr edit`) el PR único del task para dejarlo con la trazabilidad completa. Respeta las secciones que ya llenaron otras skills (`## Changes` de `delivery-engineer`, `## Testing` y `## Review` de `delivery-review`) y completa las que te corresponden a ti:

```markdown
## Summary
Resumen claro de qué cambia y por qué, para quien apruebe el merge sin tener que leer todo el historial.

## Task
TASK-<slug> (docs/tasks/TASK-<slug>.md)

## Changes
<lo que dejó delivery-engineer — no lo reescribas, solo verifica que siga vigente>

## Testing
<evidencia real que dejó delivery-review>

## Architecture decisions
<enlaces a ADRs relevantes con una línea de qué decidieron, o "Ninguna — cambio sin impacto arquitectónico">

## Related specification / plan
docs/plans/PLAN-<fecha>-<slug>.md (v<N> — versión vigente; Specification + Implementation Plan)

## Related ADRs
<lista, o "Ninguno">

## Review
<resultado y enlace a delivery-review — no lo reescribas>

## Known limitations
Cualquier limitación conocida que quede consciente después de todo el proceso (deuda técnica señalada por delivery-engineer, riesgos del plan sin mitigación completa, `Open questions` de la Specification que quedaron sin resolver, fallas ignoradas explícitamente con autorización). Si no hay ninguna, dilo explícitamente.
```

### 4. Cambios sensibles: aprobación humana explícita, siempre

Si el task involucra arquitectura (tiene ADRs), autenticación/autorización, base de datos, o infraestructura, **nunca lo marques como listo para merge sin que un humano lo apruebe explícitamente en el chat**, sin importar que `delivery-review` haya dado `PASS`. Señálalo con claridad al usuario: qué categoría sensible aplica y qué ADR/decisión respalda el cambio, y espera confirmación antes de considerar el PR cerrado por tu parte.

### 5. Merge

Este skill **no mergea por defecto**. Deja el PR listo, con su descripción completa, y se lo comunica al usuario para que apruebe el merge manualmente.

La única excepción es un veredicto `TRIVIAL_FIX` de bajo riesgo, y solo si el equipo lo decidió explícitamente como aceptable (por ejemplo, una regla ya escrita en `CLAUDE.md`, o una instrucción explícita del usuario en esta misma conversación pidiendo auto-merge para este task puntual). Sin esa autorización explícita —general o puntual—, trátalo igual que cualquier otro cambio: lo dejas listo, no lo mergeas.

### 6. Actualizar el TASK y detener

Completa `## Publicación` en `docs/tasks/TASK-<slug>.md` (enlace al PR, estado: "Listo para aprobación humana" o "Mergeado" si el usuario ya aprobó y se ejecutó el merge en esta misma invocación), agrega la fila final al historial de transiciones, y actualiza `**Etapa actual:**` a `PUBLISHED` (o déjala en `PUBLISH` si sigue pendiente de aprobación humana).

## Reglas

- Nunca marca como listo para merge un PR cuyo `delivery-review` haya terminado en `FAIL`.
- Nunca crea un PR nuevo — siempre actualiza el único PR del task.
- Nunca mergea cambios sensibles (arquitectura/auth/DB/infraestructura) sin aprobación humana explícita en el chat.
- El auto-merge de `TRIVIAL_FIX` es opt-in explícito, nunca el comportamiento por defecto.
- No modifica las secciones del PR que pertenecen a otra etapa (`## Changes`, `## Testing`, `## Review`) salvo para verificar que sigan vigentes.

## Cuándo detenerse

- `delivery-review` no llegó a `PASS`, o no hay un review registrado todavía.
- Hay commits en la rama posteriores al último `delivery-review` — pide una nueva pasada de review antes de publicar.
- Aparece algo que huela a secreto o credencial en el diff.
- El cambio es sensible y no hay aprobación humana explícita todavía.

## Cuándo delega a otra skill

Si en el paso 2 encuentra que el diff no corresponde al plan o hay commits sin revisar, delega de vuelta a `delivery-review` (nueva pasada) en vez de decidir por su cuenta si igual se puede publicar.
