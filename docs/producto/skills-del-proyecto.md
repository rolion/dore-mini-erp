# Skills del proyecto: contenido completo de cada SKILL.md

Compilado de `.claude/skills/*/SKILL.md` (y `delivery-start/references/plantillas.md`). La fuente de verdad son los archivos originales.

## Índice

- [delivery-build](#delivery-build)
- [delivery-design-system](#delivery-design-system)
- [delivery-frontend](#delivery-frontend)
- [delivery-publish](#delivery-publish)
- [delivery-start](#delivery-start)
- [delivery-ui-design](#delivery-ui-design)
- [delivery-ux-research](#delivery-ux-research)
- [delivery-visual-review](#delivery-visual-review)

---

<a id="delivery-build"></a>
# Skill: delivery-build/SKILL.md

`````markdown
---
name: delivery-build
description: Segunda etapa del flujo de entrega del monorepo (`backend/` Django/DRF + `frontend/panel_admin/` Angular). Implementa el plan aprobado de un task (docs/tasks/TASK-<slug>.md), o un TRIVIAL_FIX directamente desde la investigación, como ingeniero senior: sigue las convenciones y la arquitectura DDD, escribe las pruebas que corresponden a la Specification y, en cualquier UI, reutiliza el lenguaje visual de docs/design/design-system.md (componentes compartidos, tokens, plantillas de pantalla). Empuja a la rama del PR único. Si el plan, la Specification, el diseño o la arquitectura resultan incorrectos no los cambia en silencio: escala devolviendo el task a delivery-start. Al terminar continúa sola con delivery-publish. Se invoca tras delivery-start o con /delivery-build TASK-<slug>.
argument-hint: "TASK-<slug>"
---

# Delivery Build

Etapa ENGINEERING. Convierte la Specification y el Implementation Plan en código y pruebas, sin ampliar el alcance, sin decidir arquitectura por su cuenta y sin declararse a sí misma lista: la aprobación es de `delivery-publish`.

Plantillas (TASK, PR): `.claude/skills/delivery-start/references/plantillas.md`.

## Flujo

### 1. Leer el TASK y elegir el camino
Lee `docs/tasks/TASK-<slug>.md`.
- `TRIVIAL_FIX`: solo exige `## Investigación`. Ve a 2b.
- `NEEDS_PLAN` / `NEEDS_ARCHITECTURE`: exige `## Plan` completo, `Specification readiness: READY` y un PR registrado. Si falta algo, invoca `delivery-start TASK-<slug>` y detente.

### 2a. Preparar la rama existente
`git status` (no descartes trabajo ajeno), `git fetch` + checkout de la rama de `**Rama:**`, y confirma que es la del PR registrado.

### 2b. TRIVIAL_FIX: abrir el PR tú
Rama `task/TASK-<slug>` desde `origin/main`, PR (puede ser *draft* tras el primer commit) con el cuerpo de plantillas, y registra rama y PR en el TASK. Si al mirar el código resulta que no es trivial (más archivos, lógica de negocio), detente y devuelve el task a `delivery-start` para reclasificarlo.

### 3. Entender antes de tocar código
- Lee el `**Modo:**` del PLAN (COMPACTO o COMPLETO). En COMPACTO no exijas secciones propias de COMPLETO; la Specification sigue siendo el contrato, y los AC son obligatorios.
- Lee Specification, Test Specification, Implementation Plan y los DDR/ADR relacionados. Implementas el plan **sin violar la Specification**.
- Verifica que el plan siga vigente en el código (rutas, firmas). Si no cuadra, ve al paso 6.
- Si un detalle necesario para escribir el código es ambiguo y hay más de una lectura razonable, pregunta antes de decidir.

### 4. Implementar
Sigue los pasos del plan en orden y dentro del alcance. Reglas de `CLAUDE.md`: cambios acotados, dinero en `Decimal`, no editar migraciones aplicadas (crear nueva con `makemigrations`), no tocar `.env` ni credenciales, y **avisar antes de instalar cualquier dependencia** aunque el plan la anticipe.

**Django / DRF** (`docs/architecture/ddd.md`):
- Código en `backend/modules/<contexto>/` con `domain/` (sin imports de Django), `application/`, `infrastructure/`, `api/`. Crea solo las carpetas necesarias.
- Las reglas de negocio viven en el dominio (`order.deliver()`, no `order.status = ...`); las vistas solo traducen HTTP.
- Un módulo no importa modelos ni infraestructura de otro; se comunican por fachadas con `company_id` como primer argumento. Toda consulta de negocio filtra por `company_id` (repositorios `Django…Repository(company_id)`), que sale del usuario autenticado (`shared/tenancy.py`), nunca del cliente. Los módulos de negocio no importan `accounts`.
- Los serializers validan forma y tipos; sin N+1 (`select_related`/`prefetch_related`).
- Nombres: commands con verbo (`CreateOrder`), queries (`GetOrder`), eventos en pasado (`OrderCreated`).

**Angular**:
- Lógica no visual en services inyectables; tipos explícitos, sin `any`; Reactive Forms; `async` pipe o desuscripción explícita.
- Organiza por `src/app/features/<modulo>/` (pages, components, services, models).

**Lenguaje visual (toda UI nueva o modificada)** — fuente: `docs/design/design-system.md`:
1. Antes de escribir una pantalla, lee el sistema de diseño y abre la pantalla de referencia de su tipo (lista: `product-list`, formulario: `product-form`, detalle: `product-detail`, reporte: `features/reporting`). Copia su estructura (breadcrumb, `.card`, bloques y orden).
2. Reutiliza `app-user-avatar`, el pipe `money`, los badges, los botones de tabla (`btn-tbl-*`) y los modelos de `shared/`. Si necesitas lo mismo en un segundo módulo, muévelo a `shared/`, no lo copies.
3. Nada de HEX, fuentes ni tamaños sueltos: usa clases de la plantilla y variables de `_variable.scss`. Los colores de estado siempre con texto.
4. Cubre los estados (cargando, vacío, error, éxito), accesibilidad (labels, `aria-label` en botones de icono) y textos en español.
5. Si el DDR pide un patrón que no existe, impleméntalo como componente reutilizable en `shared/` y anótalo en `design-system.md` (secciones 3 y 5).
6. Si el sistema de diseño y el DDR chocan, gana el DDR, pero deja nota para actualizar el sistema de diseño.

**Clean code / SOLID**: aplícalos de forma consistente con el módulo que tocas. Si algo exige una refactorización fuera del alcance, anótalo como deuda técnica en `## Implementación`, no amplíes el cambio.

### 5. Pruebas
- Implementa exactamente la Test Specification: cada AC y cada regla nueva con su verificación. Niveles: **unit** (lógica aislada), **integración** (endpoint DRF completo con BD real, siguiendo los patrones y helpers existentes en `backend/`; en Angular `TestBed` + `HttpTestingController`), **E2E** solo si el plan lo pidió con justificación.
- `TRIVIAL_FIX`: la mayoría no necesita test nuevo; ajusta uno existente si el cambio toca lo que cubre.
- No escribas tests que no correspondan a ningún caso del plan.
- Puedes correr las pruebas como verificación propia (`python manage.py test` en `backend/`, `npm test` en `frontend/panel_admin/`), pero eso no es el Quality Gate: no declares nada «verificado» en el TASK ni en el PR.

### 6. Si el plan resulta incorrecto: no lo cambies en silencio
- **Detalle de implementación** (firma distinta, caso menor que no cambia alcance ni riesgo): resuélvelo y sigue.
- **Plan COMPACTO insuficiente** (aparece una condición de los tres ejes de `delivery-start`): detén la parte afectada, documenta la condición en `## Implementación`, marca `PLAN_UPDATE_REQUIRED` (upgrade a COMPLETO), etapa `PLANNING`.
- **Problema de la Specification** (AC, invariante o regla incorrecto, ambiguo o contradictorio): no lo reinterpretes ni elijas una lectura. Cita el ID (o el criterio), marca `PLAN_UPDATE_REQUIRED` indicando que afecta a la **Specification**, etapa `PLANNING`. Requiere decisión del usuario.
- **Problema del plan** (un paso no funciona, falta un caso, alcance mal dimensionado, Specification válida): `PLAN_UPDATE_REQUIRED`, etapa `PLANNING`.
- **Problema arquitectónico**: `ARCHITECTURE_REVIEW_REQUIRED`, etapa `ARCHITECTURE`.
- **Problema de diseño** (el DDR no cubre un caso real): `DESIGN_REVIEW_REQUIRED`, etapa `DESIGN`.

En cada caso: documenta el hallazgo con evidencia en `## Implementación`, agrega la fila al historial, actualiza la etapa e **invoca `delivery-start TASK-<slug>`** (paso 6 de esa skill). Puedes seguir con partes independientes que no dependan del punto afectado.

### 7. Commit y push
Revisa `git status`/`git diff`: solo archivos del plan. Commits cortos e imperativos que referencien `TASK-<slug>` y el criterio que satisfacen (ID si el plan lo define; si no, cita corta). `git push` a la rama del PR; nunca `--force` salvo pedido explícito. Actualiza solo `## Changes` del PR (`gh pr edit`).

### 8. Cerrar y continuar
Completa `## Implementación` en el TASK: resumen, qué AC/INV cubre cada parte, **desviaciones respecto al plan con su motivo**, deuda técnica y, si hubo UI, qué pantalla de referencia se siguió y qué componentes compartidos se reutilizaron o crearon. Agrega la fila `ENGINEERING → REVIEW`, etapa `REVIEW`. Resume en el chat y **continúa sin esperar** invocando la skill `delivery-publish` con `TASK-<slug>`.

## Reglas

- Nunca crea un segundo PR.
- No cambia alcance, arquitectura, diseño ni Specification en silencio.
- No se aprueba a sí mismo ni ejecuta el Quality Gate.
- No toca `.env`, credenciales ni secretos.

## Cuándo detenerse

- Falta plan o investigación para el veredicto, o la Specification está `BLOCKED`.
- Dependencia nueva sin confirmar.
- Requerimiento ambiguo tras leerlo con cuidado, o duda real sobre la rama.

`````

---

<a id="delivery-design-system"></a>
# Skill: delivery-design-system/SKILL.md

`````markdown
---
name: delivery-design-system
description: Define o ajusta tokens, temas y reglas de componentes reutilizables, y genera una pantalla de referencia en Google Stitch para mantener coherencia visual.
disable-model-invocation: true
argument-hint: "[marca, producto o cambio de estilos]"
---

Trabaja sobre: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Lee el brief disponible, estilos y componentes existentes, assets de marca y decisiones previas. Conserva el sistema existente cuando sea adecuado. No inventes un HEX oficial del logo ni cambies de biblioteca UI sin motivo.
2. Define tokens semánticos: primary, on-primary, background, surface, text, text-muted, border, success, warning, danger y focus. Incluye valores de light/dark cuando corresponda.
3. Define tipografía, escala de tamaños, espaciados, radios, sombras, densidad y breakpoints. Usa fuentes con licencia adecuada verificada; reutiliza la fuente instalada si es apropiada.
4. Especifica variantes y estados de botones, inputs, selectores, tablas, cards, navegación, diálogos, badges y notificaciones que requiere el producto.
5. Escribe docs/design/design-system.md con tabla de tokens y reglas. Si ya existe, actualízalo conservando su contenido: es la fuente de verdad del lenguaje visual que leen delivery-start, delivery-build y delivery-publish. Incluye un bloque listo para reutilizar en prompts de Stitch con valores explícitos y restricciones.
6. Usa el MCP para generar o actualizar una pantalla de referencia con los componentes principales y los temas requeridos. Aplica los tokens en el prompt; usa capacidades nativas de design system únicamente si están expuestas.
7. Inspecciona el resultado y anota desviaciones respecto a los tokens. Registra los IDs y exportaciones disponibles.

Los tokens del repositorio son la fuente de verdad; no atribuyas a Stitch variables o componentes nativos que no puedas comprobar. No modifiques estilos de producción en esta etapa.

Entrega reglas, referencia visual y discrepancias pendientes. No invoques otra etapa automáticamente.

`````

---

<a id="delivery-frontend"></a>
# Skill: delivery-frontend/SKILL.md

`````markdown
---
name: delivery-frontend
description: Implementa una pantalla o flujo a partir de referencias de Google Stitch en el framework y biblioteca UI existentes, conservando contratos y verificando comportamiento y presentación.
disable-model-invocation: true
argument-hint: "[pantalla o especificación a implementar]"
---

Implementa: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Lee la especificación, tokens, screens.md y las instrucciones de implementación del repositorio. Identifica el framework y versiones reales desde sus archivos; no asumas Angular, React ni Tailwind.
2. Recupera por MCP las pantallas registradas y los assets o código disponibles. Usa exportaciones locales existentes si la conexión está bloqueada y explica su procedencia.
3. Identifica componentes reutilizables y cambios necesarios. Si delivery-start o delivery-build ya gobierna el proyecto, respeta su alcance y artefactos; no dupliques sus reglas ni cambies contratos por iniciativa propia.
4. Adapta el diseño a componentes nativos del proyecto. El HTML exportado es referencia: no copies scripts, dependencias externas, CDN, lógica ficticia o estructuras incompatibles.
5. Implementa responsive, temas requeridos, loading, vacío, error, validación y permisos con datos y servicios existentes. No inventes endpoints. Si falta un contrato, informa y limita mocks al entorno permitido por el proyecto.
6. Reutiliza tokens semánticos. Conserva labels, foco, teclado y semántica accesible. Gestiona assets en las rutas y pipeline del proyecto.
7. Ejecuta build, lint y verificaciones relevantes disponibles. Comprueba el flujo crítico; usa Playwright u otra herramienta del proyecto para revisar presentación en los viewports y temas solicitados.
8. Registra en docs/design/implementation.md archivos cambiados, referencias de Stitch, comprobaciones realizadas, desviaciones justificadas y bloqueos.

No rediseñes en Stitch como efecto secundario de implementar. Si hace falta cambiar sustancialmente la referencia, documenta el motivo y solicita una decisión de diseño. No publiques ni hagas deploy sin encargo.

Entrega implementación y evidencia de validación; distingue lo ejecutado de lo pendiente. No invoques otra etapa automáticamente.

`````

---

<a id="delivery-publish"></a>
# Skill: delivery-publish/SKILL.md

`````markdown
---
name: delivery-publish
description: Tercera y última etapa del flujo de entrega del monorepo (`backend/` Django/DRF + `frontend/panel_admin/` Angular). Actúa como Quality Gate independiente del trabajo de un task: hace el code review contra la Specification y el plan, ejecuta de verdad pruebas, lint, build y chequeos de seguridad, verifica la consistencia visual con docs/design/design-system.md, y emite PASS o FAIL con triage. Con PASS verifica que no haya secretos ni archivos fuera de alcance, completa la descripción del PR (resumen, cambios, evidencia de tests, limitaciones) y lo deja listo para aprobación humana; nunca hace merge. Con FAIL devuelve el task a la etapa que corresponde (delivery-build o delivery-start). Se invoca tras delivery-build o con /delivery-publish TASK-<slug>.
argument-hint: "TASK-<slug>"
---

# Delivery Publish

Etapas REVIEW y PUBLISH. Quien revisa no es quien implementó: el Quality Gate corre en un **subagente con contexto limpio**, y esta skill solo orquesta, actualiza el PR y publica.

Plantillas (TASK, PR): `.claude/skills/delivery-start/references/plantillas.md`.

## Flujo

### 1. Verificar la entrada
Lee `docs/tasks/TASK-<slug>.md`. Debe estar en etapa `REVIEW` (o `PUBLISH` si es una re-publicación tras PASS). Si no, detente y dilo.

### 2. Quality Gate en un subagente aislado
Lanza un agente (Agent tool, `general-purpose`) con un prompt autocontenido que le pida revisar **solo desde artefactos**, sin asumir nada de esta conversación: TASK, PLAN vigente (con su `**Modo:**` y changelog), DDR/ADR relacionados, `docs/design/design-system.md` y el diff real (`git diff origin/main...HEAD`). Dile que **no corrija código** y que devuelva un informe con los resultados y la evidencia literal de cada comando, los hallazgos clasificados y un veredicto. Si el subagente no puede ejecutar algo, debe decirlo; nunca declarar PASS por defecto.

El agente (o, si no hay subagentes disponibles, tú, dejando constancia de que el aislamiento es procedimental) hace lo siguiente.

**a. Verificación funcional (ejecutando, no solo leyendo)**
- Backend: `python manage.py test` desde `backend/` (con `DJANGO_SETTINGS_MODULE=config.settings.test` y PostgreSQL), o acotado al app afectado más la regresión del área.
- Frontend: `npm test -- --watch=false --browsers=ChromeHeadless` desde `frontend/panel_admin/` (con `--code-coverage` para cobertura).
- E2E solo si el plan lo exige; si lo exigía y no está instalado, es un hallazgo.
- Nunca declares «pasa» un nivel que no ejecutaste.

**b. Verificación técnica (evidencia real de cada comando)**
- Lint: `ruff`/`flake8` si están configurados; `npm run lint` en frontend.
- Type checking y build: `npm run build` como mínimo; `mypy` si está configurado.
- Cobertura: en frontend con `--code-coverage`; en backend, si `coverage.py` no está, revisa manualmente que cada rama nueva tenga un test y dilo así (no instales nada).
- Seguridad: `bandit` en `backend/`, `npm audit` en frontend, si están disponibles. Si no hay ninguna, es una verificación no realizada, no un PASS silencioso.
- Límites DDD (`docs/architecture/ddd.md`): `domain/` sin Django; ningún módulo importa infraestructura de otro; Reporting solo lee; sin lógica de negocio en vistas/serializers; toda consulta de negocio filtra por `company_id` (de `shared/tenancy.py`); los módulos de negocio no importan `accounts`.
- Clean code/SOLID: solo en código nuevo o modificado, severidad baja/media salvo riesgo real. No bloquees por deuda preexistente.

**c. Conformidad con la Specification y el plan**
- Lee el `**Modo:**` del plan. En COMPACTO no marques como faltantes secciones exclusivas de COMPLETO. Si el campo falta, es un hallazgo `PLAN`.
- Specification primero: cada acceptance criterion (por ID, o por cita corta si no hay IDs; no inventes IDs), invariantes, contratos `API-`/`UI-`, permisos, edge/error cases y la tabla de mapeo AC → verificación.
- Después el plan: alcance (archivos o módulos fuera del plan = hallazgo de scope creep), cumplimiento de ADR/DDR, tests planificados (incluida la decisión sobre E2E) y desviaciones explicadas en `## Implementación`.
- Si la implementación demuestra que COMPACTO era insuficiente, hallazgo `PLAN` que pide upgrade a COMPLETO.
- Una implementación correcta de una Specification equivocada sigue siendo un fallo (`SPECIFICATION`).

**d. Consistencia visual (solo si el diff toca UI)**
- Recorre la checklist de la sección 8 de `docs/design/design-system.md`: plantilla de pantalla seguida, sin HEX/fuentes propios, componentes compartidos reutilizados en lugar de copias, estados cubiertos, accesibilidad mínima, textos en español.
- Si la app se puede levantar (`npm start` con el backend en `127.0.0.1:8000`), inspecciónala en el navegador integrado en móvil (≈390 px) y escritorio (≈1440 px), tema claro y oscuro, y adjunta evidencia. Si no se puede, marca la revisión visual como «no verificada», nunca como aprobada.
- Una desviación sin justificación en el DDR es un hallazgo `IMPLEMENTATION` (o `DESIGN` si el DDR no cubría el caso). Una desviación visual leve es `Low`.

**e. Triage de cada hallazgo** (una sola categoría)
- `IMPLEMENTATION`: Specification y plan correctos, código mal → `delivery-build`.
- `SPECIFICATION`: el código cumple lo especificado, pero la Specification es incorrecta, ambigua o incompleta → `delivery-start` (cambiarla requiere aprobación del usuario).
- `PLAN`: Specification correcta, plan incompleto o incorrecto → `delivery-start`.
- `ARCHITECTURE`: el plan se siguió bien, la decisión arquitectónica no basta → `delivery-start`.
- `DESIGN`: el DDR no cubre un caso real o el componente no sirve → `delivery-start`.

Un archivo `docs/reviews/REV-<fecha>-<task-slug>-<seq>.md` por hallazgo (seq de 2 dígitos; calcula el siguiente listando solo `REV-<fecha>-<task-slug>-*.md`):

```markdown
# REV-<fecha>-<task-slug>-<seq>: <título corto>

**Status:** Open
**Severity:** <Critical | High | Medium | Low>
**Category:** <IMPLEMENTATION | SPECIFICATION | PLAN | ARCHITECTURE | DESIGN>
**Related plan:** docs/plans/PLAN-<fecha>-<slug>.md (v<N>)
**Spec reference:** <AC-xx / INV-xx / ... o cita corta, o "N/A">
**Plan mode:** <COMPACTO | COMPLETO>
**Suggested owner:** <delivery-build | delivery-start>

## Description
## Expected behavior
## Actual behavior
## Evidence
Salida real del comando, sin resumir de forma que se pierda la traza.
```

**f. Veredicto**
- `FAIL` si hay un hallazgo `Critical` o `High` abierto, o cualquier test fallando sin autorización explícita del usuario en el chat (se registra en `## Review` del PR).
- Nunca `PASS` si hay un problema crítico conocido o una verificación aplicable sin ejecutar.

### 3. Registrar el resultado
Actualiza en el PR (`gh pr edit`) `## Testing` (salida real de cada verificación) y `## Review` (resultado, enlaces a cada REV, evidencia técnica). Actualiza el TASK: `## Review`, historial y etapa.

### 4. FAIL: devolver y reintentar
- Hallazgos `IMPLEMENTATION` → etapa `ENGINEERING`; invoca `delivery-build TASK-<slug>`.
- `SPECIFICATION`, `PLAN`, `ARCHITECTURE` o `DESIGN` → vuelve a la etapa más temprana implicada (diseño > arquitectura > specification/plan); invoca `delivery-start TASK-<slug>`.
- **Límite de ciclos**: si es el tercer FAIL consecutivo del mismo task, o un mismo hallazgo reaparece, detente y presenta el estado al usuario en lugar de seguir en bucle.

### 5. PASS: preparar la publicación
1. **Nada fuera de lugar**: `git status` limpio; el diff corresponde al plan (o a la investigación en `TRIVIAL_FIX`); sin archivos temporales, logs de debug ni artefactos de build; **sin secretos** (`.env`, credenciales, tokens, claves). Si aparece algo que parezca un secreto, detente y avisa: no lo publiques ni lo borres por tu cuenta (puede requerir rotar la credencial).
2. Si hay commits posteriores al código revisado, repite el Quality Gate sobre el estado actual.
3. **Completa la descripción del PR** (`gh pr edit`), respetando las secciones de otras etapas (`## Changes`) y rellenando las tuyas:

```markdown
## Summary
Qué cambia y por qué, para quien apruebe sin leer todo el historial.

## Task
TASK-<slug> (docs/tasks/TASK-<slug>.md)

## Changes
<lo que dejó delivery-build; verifica que siga vigente>

## Testing
<evidencia real del Quality Gate>

## Architecture decisions
<enlaces a ADR con una línea de qué decidieron, o "Ninguna — cambio sin impacto arquitectónico">

## Related specification / plan
docs/plans/PLAN-<fecha>-<slug>.md (v<N>)

## Related ADRs / DDRs
<lista, o "Ninguno">

## Review
<resultado PASS y enlace; consistencia visual verificada o "no verificada">

## Known limitations
Deuda técnica señalada, riesgos sin mitigación completa, Open questions sin resolver, fallas ignoradas con autorización. Si no hay, dilo explícitamente.
```

4. Actualiza el TASK: `## Publicación`, historial y etapa `PUBLISH`.

### 6. Cambios sensibles y merge
- **Nunca mergeas.** El PR queda listo para aprobación humana.
- Si el task involucra arquitectura (tiene ADR), autenticación/autorización, base de datos o infraestructura, señálalo con claridad al usuario (categoría y ADR que lo respalda). Solo un humano aprueba el merge.
- El auto-merge de un `TRIVIAL_FIX` solo aplica si `CLAUDE.md` o una instrucción explícita del usuario en esta conversación lo autorizan para ese task.

### 7. Reportar
Resume en el chat: veredicto, qué se ejecutó (y qué no), hallazgos, estado visual, enlace al PR y qué falta de parte del humano.

## Reglas

- Quien implementó no aprueba su trabajo: el Quality Gate corre aislado.
- No corrige código ni pruebas; solo documenta y hace triage.
- No declara `PASS` sin evidencia ejecutada real de cada verificación aplicable.
- No bloquea por deuda técnica preexistente fuera del alcance.
- Nunca marca como listo un PR con FAIL; nunca crea un PR nuevo; no modifica `## Changes` salvo para verificar que siga vigente.
- No reescribe la Specification: si necesita cambiar, es un hallazgo.

## Cuándo detenerse

- El task no está en `REVIEW`/`PUBLISH`.
- No se puede ejecutar una verificación relevante (p. ej. sin PostgreSQL ni dependencias): repórtala como no realizada.
- Aparece un posible secreto en el diff.
- Tercer FAIL consecutivo.
- Cambio sensible sin aprobación humana explícita: queda en `PUBLISH`.

`````

---

<a id="delivery-start"></a>
# Skill: delivery-start/SKILL.md

`````markdown
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

`````

---

<a id="delivery-ui-design"></a>
# Skill: delivery-ui-design/SKILL.md

`````markdown
---
name: delivery-ui-design
description: Genera y refina pantallas de producto en Google Stitch usando el brief UX, el sistema de diseño y los componentes del proyecto; documenta estados y especificaciones para implementación.
disable-model-invocation: true
argument-hint: "[pantalla o flujo, temas y dispositivos]"
---

Diseña: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Lee ux-brief.md y design-system.md si existen, requisitos y pantallas relacionadas. Si faltan, completa un brief mínimo y registra supuestos; no bloquees un cambio pequeño por documentación opcional.
2. Revisa el frontend: biblioteca de componentes, navegación, tablas y formularios existentes. Diseña dentro de sus capacidades o identifica explícitamente lo que requiere un componente nuevo.
3. Prepara el prompt de Stitch: objetivo, usuario, flujo, jerarquía, textos en el idioma del producto, datos ficticios, componentes, tokens exactos, tema y dispositivo. Define lo que debe conservarse de la pantalla existente.
4. Usa las herramientas expuestas para generar o editar en el proyecto registrado. No sustituyas el uso de Stitch por una descripción textual sin indicar el bloqueo.
5. Inspecciona el resultado visual. Revisa acción principal, legibilidad, densidad, consistencia, responsive y estados. Refina con cambios concretos, manteniendo las partes que funcionan.
6. Genera referencias desktop/mobile y light/dark según el alcance. Describe los estados restantes en la especificación si no necesitan una generación independiente.
7. Actualiza screens.md y exporta lo disponible. Guarda docs/design/specs/<modulo>-<pantalla>.md con layout, componentes, interacciones, validación, permisos, estados y criterios de aceptación.

No modifiques código de producción ni supongas aprobación del usuario. No agregues reglas de negocio a partir de detalles decorativos generados por Stitch.

Entrega las referencias reales, especificación y estado de revisión. No invoques otra etapa automáticamente.

`````

---

<a id="delivery-ux-research"></a>
# Skill: delivery-ux-research/SKILL.md

`````markdown
---
name: delivery-ux-research
description: Define necesidades, flujos, arquitectura de información y criterios UX antes de diseñar pantallas. Usa referencias existentes de Google Stitch cuando estén disponibles.
disable-model-invocation: true
argument-hint: "[producto o módulo y objetivo]"
---

Trabaja sobre: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Revisa los requisitos, pantallas existentes, rutas, roles y restricciones del alcance. Si hay referencias de Stitch, recupéralas mediante lectura para entender el flujo actual.
2. Define usuarios, tarea principal, resultado esperado y problemas que el flujo debe resolver. Etiqueta las hipótesis; no presentes inferencias como investigación de usuarios realizada.
3. Diseña la arquitectura de información: secciones, navegación, entradas y salidas. Define flujo principal, alternativas, errores y restricciones por rol.
4. Para cada pantalla, especifica propósito, datos, acción principal, acciones secundarias, estados y criterios verificables de aceptación.
5. Formula preguntas pendientes y separa cuáles bloquean el diseño. Resuelve detalles menores con supuestos explícitos; pregunta solo cuando una decisión material no puede inferirse.
6. Guarda o actualiza docs/design/ux-brief.md con contexto, evidencia, hipótesis, flujos, pantallas, criterios y preguntas.

No generes pantallas nuevas en esta etapa ni modifiques código. Stitch aporta referencias visuales; no sustituye entrevistas ni valida necesidades de usuarios.

Entrega el brief y el alcance listo para delivery-design-system o delivery-ui-design. No invoques otra etapa automáticamente.

`````

---

<a id="delivery-visual-review"></a>
# Skill: delivery-visual-review/SKILL.md

`````markdown
---
name: delivery-visual-review
description: Compara la aplicación ejecutada con las referencias de Google Stitch y las especificaciones; revisa coherencia, responsive, temas, estados y accesibilidad, y genera hallazgos con evidencia.
disable-model-invocation: true
argument-hint: "[pantalla o flujo; opcionalmente corregir]"
---

Revisa: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Lee alcance, especificación, sistema de diseño y registro de pantallas. Recupera por MCP la referencia vigente o utiliza su exportación local identificada.
2. Ejecuta la aplicación con las instrucciones del repositorio y usa la herramienta de navegador disponible. No declares revisión visual si no puedes inspeccionar imágenes de referencia y aplicación.
3. Compara el mismo viewport, tema, estado y datos equivalentes. Comprueba navegación, jerarquía, alineación, tipografía, espaciado, densidad, colores y componentes. Acepta desviaciones justificadas por accesibilidad o biblioteca existente.
4. Revisa desktop/mobile, light/dark y estados relevantes del alcance. Comprueba teclado, foco, labels, contraste y overflow mediante las herramientas disponibles.
5. Documenta cada hallazgo con severidad, pantalla, condiciones de reproducción, esperado, observado, evidencia y acción propuesta. Distingue fallo funcional, desviación visual y mejora opcional.
6. Guarda docs/design/visual-review.md y evidencia sin secretos en docs/design/reviews/<modulo>/.
7. Por defecto solo revisa. Si el usuario pidió corregir, aplica correcciones dentro del alcance y repite las comprobaciones afectadas. No cambies la referencia de Stitch para ocultar una diferencia.

Entrega cobertura real, hallazgos y limitaciones. Usa no verificado cuando falten evidencia o herramientas. No marques aprobado por el usuario ni publiques automáticamente. No invoques otra etapa automáticamente.

`````

---

# Skill: delivery-start/references/plantillas.md

`````markdown
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

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| <fecha real> | (nuevo) → INVESTIGATION | Task creado | delivery-start |

## Investigación

### Requerimiento
<tal como se recibió, más las aclaraciones del usuario>

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

`````
