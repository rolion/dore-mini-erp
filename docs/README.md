# docs/

Artefactos del flujo `delivery-*`. Los nombres usan slug descriptivo, no números secuenciales (evita colisiones entre sesiones en paralelo).

| Carpeta | Contenido | Skill |
|---|---|---|
| `architecture/` | `ddd.md`: referencia DDD del proyecto | — |
| `tasks/` | `TASK-<slug>.md`: fuente de verdad de cada tarea | delivery-investigate |
| `design/` | `DDR-<task-slug>-<decision-slug>.md` | delivery-design |
| `adr/` | `ADR-<task-slug>-<decision-slug>.md` | delivery-architect |
| `plans/` | `PLAN-<YYYY-MM-DD>-<slug>.md` | delivery-plan |
| `reviews/` | `REV-<fecha>-<task-slug>-<seq>.md` | delivery-review |

Flujo: `/delivery-investigate` → `/delivery-design` (si aplica) → `/delivery-architect` (si aplica) → `/delivery-plan` → `/delivery-engineer` → `/delivery-review` → `/delivery-publish`.
