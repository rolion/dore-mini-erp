# REV-2026-10-30-delivery-start-url-trello-01: Edge case de tarjeta sin descripción sin texto propio

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-30-delivery-start-url-trello.md (v1)
**Spec reference:** Edge cases del plan
**Plan mode:** COMPACTO
**Suggested owner:** delivery-start

## Description
El plan prevé usar título y checklists si la tarjeta no tiene descripción y preguntar si no alcanza.
## Expected behavior
La skill lo indica explícitamente.
## Actual behavior
Solo lo cubre la regla genérica de contenido insuficiente en SKILL.md (paso 1, punto 4).
## Evidence
Revisión del Quality Gate sobre `git diff origin/main...HEAD` (4 archivos, 116 inserciones, 3 borrados). No bloquea la publicación.
