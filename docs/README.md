# docs/

Artefactos del flujo `delivery-*`. Los nombres usan slug descriptivo, no números secuenciales (evita colisiones entre sesiones en paralelo).

| Carpeta | Contenido | Skill |
|---|---|---|
| `architecture/` | `ddd.md`: referencia DDD del proyecto | — |
| `tasks/` | `TASK-<slug>.md`: fuente de verdad de cada tarea | delivery-start |
| `design/` | `design-system.md` (lenguaje visual vigente) y `DDR-<task-slug>-<decision-slug>.md` | delivery-start |
| `adr/` | `ADR-<task-slug>-<decision-slug>.md` | delivery-start |
| `plans/` | `PLAN-<YYYY-MM-DD>-<slug>.md` | delivery-start |
| `reviews/` | `REV-<fecha>-<task-slug>-<seq>.md` | delivery-publish |

Flujo: `/delivery-start` (investiga, aclara, diseño y arquitectura si aplican, plan y PR) → `/delivery-build` (implementa) → `/delivery-publish` (code review, pruebas, PASS/FAIL y PR listo para aprobación humana). Cada skill llama a la siguiente sola; solo se detiene ante decisiones de negocio abiertas, dudas del requerimiento, cambios de Specification o cambios sensibles pendientes de aprobación. Flujo UX/UI opcional con Stitch: `delivery-ux-research` → `delivery-design-system` → `delivery-ui-design` → `delivery-frontend` → `delivery-visual-review`.
