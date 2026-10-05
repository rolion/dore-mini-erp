---
name: delivery-investigate
description: Investiga y documenta el contexto de una tarea de este monorepo (`backend/` en Django/DRF + `frontend/panel_admin/` en Angular) antes de que nadie decida una solución. Analiza el requerimiento, explora el código relevante, identifica módulos y dependencias afectadas, busca implementaciones similares existentes, describe cómo funciona el sistema hoy, identifica restricciones y riesgos, y separa explícitamente hechos verificados de hipótesis. Emite un veredicto de complejidad (TRIVIAL_FIX, NEEDS_PLAN o NEEDS_ARCHITECTURE) y, por separado, si hace falta una decisión de diseño/UX (Diseño requerido: SI/NO), con su justificación. Crea o actualiza el artefacto de seguimiento docs/tasks/TASK-<slug>.md (nombrado con un slug descriptivo de la tarea, no un número secuencial, para evitar colisiones entre sesiones en paralelo) con el reporte embebido, listo para que delivery-design, delivery-architect o delivery-plan lo consuman. No propone soluciones ni modifica código. Se invoca explícitamente con /delivery-investigate <descripción de la tarea> para abrir un task nuevo, o /delivery-investigate TASK-<slug> para continuar uno existente; no debe activarse solo porque el usuario mencione "investigar" o "revisar" en una frase suelta.
---

# Delivery Investigate

## Por qué existe este skill

Es la primera etapa del flujo `delivery-*`: TASK → INVESTIGATION → DESIGN (si aplica) → ARCHITECTURE (si aplica) → PLANNING → ENGINEERING → REVIEW → PUBLISH. Su único trabajo es entender y documentar, no decidir. Separar la investigación de la planificación evita el sesgo de "investigar hacia la solución que ya se me ocurrió": este skill reúne hechos sobre el problema y el código tal como están hoy, sin proponer nada. `delivery-design`, `delivery-architect` y `delivery-plan` construyen sobre ese reporte.

DESIGN y ARCHITECTURE son ejes independientes, no alternativos: una tarea puede necesitar ambos (ej. una pantalla nueva con un modelo de permisos nuevo), solo uno, o ninguno. Cuando aplican los dos, DESIGN va primero — la decisión de qué componentes/flujo de UI se necesitan es insumo de la decisión de arquitectura (ej. cómo pagina una tabla condiciona el contrato del endpoint), no al revés.

## Cuándo usarlo

Solo cuando el usuario invoque `/delivery-investigate` explícitamente. No lo dispares por tu cuenta al detectar "investigar", "revisar" o "entender" en una conversación normal.

## Inputs

- Una descripción de la tarea en lenguaje natural (abre un task nuevo), o
- Un identificador `TASK-<slug>` existente (re-investigar o completar un task cuya investigación quedó incompleta).

## Outputs

- `docs/tasks/TASK-<slug>.md` creado (si es nuevo) o actualizado, con la sección `## Investigación` completa y un veredicto de complejidad justificado.
- Ninguna modificación de código.

## Flujo

### 1. Ubicar o crear el TASK

- Si el usuario pasó un `TASK-<slug>`, lee `docs/tasks/TASK-<slug>.md`. Si no existe, dilo y detente.
- Si pasó una descripción de tarea nueva, **no uses numeración secuencial** — con varias sesiones corriendo en paralelo, dos sesiones calculan el mismo "próximo número" antes de que la otra escriba su archivo y se pisan. En su lugar:
  1. Deriva un slug descriptivo del requerimiento: kebab-case, minúsculas, sin tildes ni caracteres especiales, 3-6 palabras que capturen el tema real (no genérico) — ej. "mejorar módulo de usuario: listar, editar y ver según privilegios" → `modulo-usuario-privilegios`.
  2. Verifica con Glob/Read si ya existe `docs/tasks/TASK-<slug>.md`.
     - No existe → ese es el nombre final, crea el archivo.
     - Existe y su `## Investigación` describe el mismo requerimiento → trátalo como continuar ese task existente, no crees uno nuevo (avisa al usuario que ya existía).
     - Existe pero es un requerimiento distinto (colisión real de nombre) → agrega un sufijo numérico corto al slug (`-2`, `-3`, ...) hasta encontrar uno libre, y dilo explícitamente en el chat para que quede claro que fue una colisión, no el id "oficial".
- Si `docs/tasks/` no existe todavía, créala al escribir el primer archivo.

### 2. Entender el requerimiento

Lee la tarea con ojo crítico: qué problema de negocio resuelve, qué comportamiento nuevo se espera, quién lo pidió si se sabe. Si la descripción es genuinamente ambigua al punto de no poder investigar nada concreto (por ejemplo, no se entiende qué módulo del sistema está involucrado), pregunta antes de seguir. Si es lo bastante clara para empezar a investigar aunque falten detalles de solución, no preguntes por preguntar — esos detalles son trabajo de `delivery-plan`, no tuyo.

### 3. Investigar el código como se hace hoy, no como debería ser

El proyecto es nuevo y el código aún está en construcción, así que no asumas nada por el nombre de un archivo ni que exista una estructura que no verificaste. Usa Grep/Glob activamente y cita siempre `archivo:línea` real, nunca ubicaciones inventadas:

- **Módulos y dependencias relacionadas**: en el backend (`backend/`, apps Django), identifica qué apps y capas toca (models, serializers, views/viewsets, services, urls, permisos). En el frontend (`frontend/panel_admin/src/`), qué componentes/servicios están involucrados.
- **Implementaciones similares existentes**: busca si ya existe un patrón parecido en el código (otro endpoint similar, otro componente con la misma necesidad) que la solución debería seguir en vez de inventar uno nuevo.
- **Comportamiento actual**: describe cómo funciona el sistema hoy en el área afectada, con evidencia concreta (qué hace la vista, qué devuelve el serializer, qué pinta el componente).
- **Restricciones**: reglas de `CLAUDE.md` (si existe) que apliquen, y cualquier documentación del proyecto en `docs/` relevante al área.
- **Migraciones**: si la tarea roza modelos, revisa las carpetas `migrations/` de la app afectada en `backend/` para saber cuál es la última.
- **Riesgos observables**: lo que se ve a simple vista que podría complicar una solución (acoplamiento, falta de tests en el área, contrato de API frágil) — sin proponer cómo mitigarlo, eso es trabajo de `delivery-architect`/`delivery-plan`.

### 4. Separar hechos de hipótesis

En el reporte, usa siempre dos categorías distintas:
- **Hechos encontrados**: verificado leyendo el código, con `archivo:línea`.
- **Hipótesis / supuestos no confirmados**: cosas que parecen ciertas pero no se verificaron (p. ej. "probablemente ningún otro cliente consume este endpoint, pero no se confirmó").

Nunca mezcles ambas categorías ni presentes una hipótesis como un hecho.

### 5. Emitir el veredicto de complejidad

Elige uno y justifícalo explícitamente con 1-3 frases:

- **TRIVIAL_FIX**: typo, cambio de una línea, ajuste cosmético (texto, estilo, constante) sin riesgo — no toca lógica de negocio, contrato de API, modelos, permisos ni múltiples archivos relacionados.
- **NEEDS_PLAN**: la mayoría de las tareas. Cambio acotado que no requiere una decisión arquitectónica nueva; puede ir directo a `delivery-plan`.
- **NEEDS_ARCHITECTURE**: detectas alguno de estos indicadores (los mismos que usa `delivery-architect` para decidir si interviene): cambio estructural, nuevo módulo o bounded context, nueva integración externa, cambios importantes de base de datos, cambios de autenticación/autorización, cambios de infraestructura, impacto en múltiples módulos, problemas con la arquitectura existente, o una decisión que puede generar deuda técnica importante.

Si dudas entre NEEDS_PLAN y NEEDS_ARCHITECTURE, prefiere NEEDS_ARCHITECTURE — es más barato que `delivery-architect` confirme "no hace falta nada especial" a que `delivery-plan` descubra a mitad de camino que sí.

### 5b. Evaluar si hace falta una decisión de diseño

Independiente del veredicto de complejidad, decide **Diseño requerido: SI** cuando la tarea agrega o cambia superficie de UI de forma no trivial: pantallas nuevas, flujos con varios pasos, adopción de componentes de la plantilla `frontend/panel_admin/` (documentada en `frontend/panel_admin_doc/`), o cambios que dejan una pantalla visualmente inconsistente con el resto si no se piensan con criterio. **Diseño requerido: NO** para cambios puramente de backend, fixes de lógica sin impacto visual, o ajustes cosméticos menores que no ameritan comparar alternativas (esos son `TRIVIAL_FIX` y ni siquiera pasan por acá). Igual que con arquitectura, ante la duda preferí SI — es más barato que `delivery-design` confirme que no hacía falta nada especial.

### 6. Escribir/actualizar el TASK

Usa esta plantilla para un TASK nuevo (consérvala tal cual la usan las demás skills `delivery-*`, que solo agregan filas al historial y llenan sus propias secciones):

```markdown
# TASK-<slug>: <título corto de la tarea>

**Etapa actual:** INVESTIGATION
**Veredicto de complejidad:** <TRIVIAL_FIX | NEEDS_PLAN | NEEDS_ARCHITECTURE>
**Diseño requerido:** <SI | NO>
**Rama:** _sin asignar todavía_
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| <fecha real> | (nuevo) → INVESTIGATION | Task creado | delivery-investigate |

## Investigación

### Requerimiento
<descripción de la tarea tal como se recibió>

### Hechos encontrados
- `archivo:línea` — ...

### Hipótesis / supuestos no confirmados
- ...

### Módulos y dependencias relacionadas
...

### Implementaciones similares existentes
...

### Comportamiento actual
...

### Restricciones
...

### Riesgos identificados
...

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

Obtén la fecha real del sistema para el historial (no la inventes). Si estás actualizando un TASK existente, no reescribas secciones de etapas posteriores que ya tengan contenido — solo actualiza `## Investigación` y agrega la fila correspondiente al historial.

### 7. Reportar y detener

Resume en el chat el veredicto de complejidad, el de diseño, y su justificación. Sugiere el siguiente comando combinando ambos ejes (DESIGN siempre antes que ARCHITECTURE cuando los dos aplican):
- `TRIVIAL_FIX` → sugiere `/delivery-engineer TASK-<slug>` directamente (salta diseño, arquitectura y plan; si genuinamente hay un cambio visual en un `TRIVIAL_FIX`, reconsidera el veredicto de complejidad, no lo combines con diseño).
- `NEEDS_PLAN` + Diseño NO → sugiere `/delivery-plan TASK-<slug>`.
- `NEEDS_PLAN` + Diseño SI → sugiere `/delivery-design TASK-<slug>`.
- `NEEDS_ARCHITECTURE` + Diseño NO → sugiere `/delivery-architect TASK-<slug>`.
- `NEEDS_ARCHITECTURE` + Diseño SI → sugiere `/delivery-design TASK-<slug>` (y aclara que después de eso corresponde `/delivery-architect TASK-<slug>`).

No invoques tú mismo la siguiente skill ni asumas que el usuario ya aprobó seguir.

## Reglas

- No modifica código bajo ninguna circunstancia.
- No propone soluciones, pasos de implementación ni arquitectura.
- Toda afirmación sobre el código cita `archivo:línea` real.
- No inventa información: si algo no se pudo verificar, se declara como hipótesis o como pregunta abierta.

## Cuándo detenerse

- El requerimiento es tan ambiguo que no se puede investigar nada concreto todavía.
- El `TASK-<slug>` pasado como argumento no existe.

## Cuándo delega a otra skill

Siempre termina delegando (nunca implementa ni planifica): a `delivery-engineer` si el veredicto es `TRIVIAL_FIX`; a `delivery-design` si Diseño requerido es `SI` (sin importar el veredicto de complejidad); si no, a `delivery-architect` si es `NEEDS_ARCHITECTURE`, o a `delivery-plan` si es `NEEDS_PLAN`. La transición es una sugerencia explícita al usuario, no una invocación automática.
