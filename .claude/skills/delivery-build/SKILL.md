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
