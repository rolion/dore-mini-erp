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
