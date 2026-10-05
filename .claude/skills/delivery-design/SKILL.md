---
name: delivery-design
description: Toma la investigación de un task (docs/tasks/TASK-<slug>.md, producida por delivery-investigate) cuando esta marcó "Diseño requerido: SI", y decide qué componentes/patrones de la plantilla `panel_admin/` (docs/frontend/panel_admin/reference.md) usar para las pantallas y flujos involucrados, y cómo deben comportarse (estados, visibilidad según privilegios, navegación). Interviene cuando la tarea agrega o cambia superficie de UI significativa: pantallas nuevas, flujos con varios pasos, adopción de componentes de la plantilla, o inconsistencia visual entre lo existente y lo nuevo. No decide cómo se aplican permisos en el backend (eso es delivery-architect) ni implementa código. Registra la decisión como DDR en docs/design/DDR-<task-slug>-<decision-slug>.md y actualiza el TASK. Se invoca explícitamente con /delivery-design TASK-<slug>; no debe activarse solo porque el usuario mencione "diseño" o "UI" en una frase suelta.
---

# Delivery Design

## Por qué existe este skill

`delivery-architect` decide si algo se sostiene técnicamente; este skill decide qué necesita ver y hacer la persona que usa la pantalla, y con qué pieza de la plantilla `panel_admin/` se resuelve. Son preguntas distintas: "¿qué endpoint expone esto?" no es la misma decisión que "¿esto es una tabla con `ngx-datatable` o un listado simple? ¿el botón de editar se oculta o se deshabilita para quien no tiene privilegio?". Mezclar ambas en una sola etapa hace que la decisión de UX se tome de pasada, sin comparar alternativas, y que la decisión técnica herede una elección visual no cuestionada. Igual que `delivery-architect` con los ADR, este skill deja la decisión de diseño trazable en un documento propio (DDR — Design Decision Record), independiente del plan que la ejecuta.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-design TASK-<slug>` explícitamente — típicamente porque `delivery-investigate` marcó `**Diseño requerido:** SI`, o porque `delivery-review`/`delivery-engineer` reabrieron el task con `DESIGN_REVIEW_REQUIRED` (ej. lo implementado no sigue el DDR, o el DDR no contempló un caso real). No lo dispares por tu cuenta.

## Inputs

- `TASK-<slug>` con la sección `## Investigación` completa.
- `docs/frontend/panel_admin/reference.md` (qué trae la plantilla, y sus límites — leerlo siempre, no asumir qué componentes existen).
- `docs/frontend-audit.md` (deuda técnica y patrones ya identificados en `proforma/`, para no repetir un problema conocido con la cara nueva de la plantilla).
- ADRs previos en `docs/adr/` y DDRs previos en `docs/design/` que puedan haber tocado la misma pantalla o componente.

## Outputs

- Uno o más DDR en `docs/design/DDR-<task-slug>-<decision-slug>.md`.
- `docs/tasks/TASK-<slug>.md` actualizado: sección `## Diseño` enlazando el/los DDR, transición de etapa, fila en el historial.

## Flujo

### 1. Leer el TASK y la referencia de la plantilla

Lee `docs/tasks/TASK-<slug>.md` completo. Si `## Investigación` está vacía o dice "Pendiente", detente y pide correr `/delivery-investigate TASK-<slug>` primero. Lee `docs/frontend/panel_admin/reference.md` completo — no asumas de memoria qué componentes trae `panel_admin/` ni qué tan resuelto viene algo (ej. el módulo de auth de la plantilla es un demo sin roles, ver esa referencia).

### 2. Identificar pantallas y flujos afectados

A partir del requerimiento, lista explícitamente qué pantallas/vistas cambian o se crean, y qué acción hace la persona en cada una (listar, ver detalle, editar, crear). No inventes pantallas que el requerimiento no pidió.

### 3. Elegir componentes/patrones de la plantilla y justificar

Para cada pantalla, decide qué pieza de la plantilla `panel_admin/` se usa (tabla, formulario, layout) citando la sección correspondiente de `docs/frontend/panel_admin/reference.md`. Si hay más de una opción razonable (ej. `ngx-datatable` vs. mantener `angular-datatables` que ya usa `proforma/`), compáralas explícitamente: consistencia con lo existente vs. beneficio del componente nuevo, esfuerzo de migración, qué se rompe si se mezclan ambos patrones en la misma app. Evita sobreingeniería — adoptar toda la plantilla de una vez no es gratis; prioriza lo que la tarea necesita hoy.

### 4. Definir comportamiento por estado/privilegio — y marcar el límite con arquitectura

Si la pantalla cambia según el rol/privilegio de quien la usa, define el comportamiento visual (¿oculto, deshabilitado con tooltip, redirect?) pero deja explícito que esto es una decisión de UX, no de seguridad: la aplicación real del permiso (qué puede hacer de verdad, no solo qué ve) es responsabilidad de `delivery-architect`/el backend. Escribe en el DDR una nota tipo "Requiere que arquitectura defina cómo se verifica `<privilegio>` del lado servidor — el frontend no debe ser la única barrera."

### 5. Crear o actualizar el DDR

Slug de la decisión: kebab-case corto, 2-4 palabras (ej. `listado-edicion-usuarios`). Nombra el archivo `docs/design/DDR-<task-slug>-<decision-slug>.md`. Antes de escribir, verifica que no exista ya un archivo con ese nombre exacto describiendo algo distinto (ver regla de nombres en `delivery-investigate`); si existe y es la misma decisión, actualízalo en vez de duplicar.

```markdown
# DDR-<task-slug>-<decision-slug>: <título de la decisión>

**Estado:** Propuesto
**Task relacionado:** TASK-<task-slug>
**Fecha:** <fecha real>

## Contexto
Qué llevó a esta decisión (resume lo relevante de la investigación del task).

## Pantallas/flujos afectados
Lista de vistas y qué hace la persona en cada una.

## Componentes/patrones elegidos
Por pantalla: qué pieza de la plantilla `panel_admin/` (o de lo ya existente en `proforma/`) se usa, citando `docs/frontend/panel_admin/reference.md`.

## Alternativas consideradas
Cada alternativa evaluada con su trade-off principal. Si solo hubo una opción razonable, dilo y por qué.

## Comportamiento por privilegio/estado
Qué ve y qué puede hacer cada perfil. Nota explícita de qué queda pendiente de aplicar en el backend (ver `delivery-architect`).

## Consecuencias
Qué queda más simple, qué deuda visual/de consistencia se acepta conscientemente (si alguna), y qué otras pantallas quedarían inconsistentes si no se actualizan después.
```

Si esta invocación **actualiza** una decisión ya tomada (por ejemplo, `delivery-review` encontró que el DDR no contemplaba un caso real), no borres el DDR anterior: cambia su `**Estado:**` a `Reemplazado por DDR-<nuevo>` y crea uno nuevo que lo referencie en `## Contexto`.

### 6. Actualizar el TASK y reportar

Completa `## Diseño` en `docs/tasks/TASK-<slug>.md` enlazando el/los DDR, agrega la fila al historial (`DESIGN → ARCHITECTURE` o `DESIGN → PLANNING` según corresponda, motivo, `delivery-design`), y actualiza `**Etapa actual:**`:
- Si el veredicto de complejidad del task es `NEEDS_ARCHITECTURE`: etapa `ARCHITECTURE`, sugiere `/delivery-architect TASK-<slug>`.
- Si es `NEEDS_PLAN`: etapa `PLANNING`, sugiere `/delivery-plan TASK-<slug>` directamente.

Resume la decisión en el chat. No invoques tú mismo la siguiente skill.

## Reglas

- No decide arquitectura técnica (modelo de datos, cómo se verifica un permiso en el servidor, contrato de API) — eso es `delivery-architect`.
- No implementa código ni toca `proforma/src/`.
- Toda elección de componente cita la sección correspondiente de `docs/frontend/panel_admin/reference.md`, nunca una suposición sobre qué trae la plantilla.
- Si una pantalla necesita comportamiento por privilegio, siempre deja constancia explícita de que el frontend no es la barrera de seguridad real.

## Cuándo detenerse

- `## Investigación` del TASK está vacía o incompleta.
- El requerimiento no deja claro qué pantallas están involucradas, al punto de no poder proponer nada concreto.

## Cuándo delega a otra skill

Siempre termina delegando: a `delivery-architect` si el veredicto del task es `NEEDS_ARCHITECTURE`, o a `delivery-plan` si es `NEEDS_PLAN`. Nunca implementa ni planifica pasos de ejecución.
