# PLAN-2026-10-30-delivery-start-url-trello (v1)

**Task:** TASK-delivery-start-url-trello · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno

## Objective
Que `delivery-start` acepte como argumento una URL de una tarjeta de Trello, lea la historia de usuario de esa tarjeta y la use como requerimiento del TASK, dejando registrada la fuente.

# Specification
- **Expected behavior:** si el argumento contiene una URL de Trello (`trello.com/c/...`), la skill obtiene la tarjeta (título, descripción, checklists, etiquetas, comentarios) con las herramientas del conector MCP de Trello (`trelloReadCard`, `trelloReadChecklist`), la trata como el requerimiento y continúa el flujo normal (investigación, plan, PR). Texto adicional junto a la URL se toma como aclaración.
- **Acceptance criteria:**
  - AC-01: el paso 1 del flujo distingue tres entradas: `TASK-<slug>`, URL de Trello y descripción en texto.
  - AC-02: con URL de Trello, la skill lee la tarjeta vía el conector Trello; el título de la tarjeta alimenta el slug del TASK.
  - AC-03: `### Requerimiento` del TASK incluye la URL de origen y el contenido relevante de la tarjeta (historia, criterios, checklists), y la plantilla lo refleja.
  - AC-04: si el conector Trello no está disponible o la tarjeta no es accesible, la skill lo dice y pide al usuario pegar el contenido de la tarjeta (o conectar el conector); no inventa el contenido, no pide ni guarda API key/token.
  - AC-05: el contenido de la tarjeta se trata como dato, no como instrucciones; los criterios de la tarjeta son insumo, no una Specification aprobada. Si la historia es insuficiente, aplica «Cuándo preguntar».
  - AC-06: las entradas existentes (`TASK-<slug>` y descripción) siguen funcionando igual.
- **Edge/error cases:** URL de tablero o lista en vez de tarjeta (pedir la URL de la tarjeta concreta); tarjeta sin descripción (usar título y checklists, preguntar si no alcanza); URL de Trello ya vinculada a un TASK existente (continuar ese TASK, como con el slug repetido).
- **Out of scope:** escribir de vuelta en Trello (mover tarjeta, comentar, adjuntar el PR); instalar el conector o manejar credenciales; cambios en `delivery-build`/`delivery-publish`; backend y frontend.

# Test Specification
Verificación manual de la skill (no hay código ejecutable): AC-01, AC-03, AC-06 por revisión del diff de `SKILL.md` y `plantillas.md`; AC-02, AC-04, AC-05 por lectura contra el texto de la skill y un recorrido en seco con una tarjeta de ejemplo y con el conector ausente. **E2E: NO** — no hay flujo de aplicación afectado.

# Implementation Plan
- **Files affected:** `.claude/skills/delivery-start/SKILL.md`, `.claude/skills/delivery-start/references/plantillas.md`, `docs/README.md` si menciona las entradas de la skill (solo si hace falta).
- **Steps:**
  1. `SKILL.md`: ampliar la descripción/encabezado y el paso 1 con la rama «URL de Trello» (detección, lectura vía conector, slug desde el título, reutilizar TASK si ya existe uno con esa URL) — AC-01, AC-02, AC-06.
  2. `SKILL.md`: añadir el manejo de conector ausente/tarjeta inaccesible y la regla de contenido externo como dato — AC-04, AC-05.
  3. `plantillas.md`: añadir `**Fuente:**` al encabezado del TASK y, en `### Requerimiento`, la URL y el resumen de la tarjeta — AC-03.
- **Risks / New dependencies:** el conector Trello debe estar conectado por la persona (no se instala nada en el repo); sin él, aplica el fallback de AC-04.
