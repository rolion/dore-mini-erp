# TASK-link-claude-skills-codex: Share Claude skills with Codex

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Dise?o requerido:** NO
**Rama:** task/TASK-link-claude-skills-codex
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/43

## Historial de transiciones
| Fecha (UTC) | Transici?n | Motivo | Origen |
|---|---|---|---|
| 2026-10-31 | (nuevo) ? INVESTIGATION | Submit existing skill junctions | delivery-start |
| 2026-10-31 | INVESTIGATION ? PLANNING | Eight related links; compact plan | delivery-start |
| 2026-10-31 | PLANNING ? ENGINEERING | Specification READY | delivery-start |
| 2026-10-31 | ENGINEERING ? REVIEW | Relative Git symlinks staged | delivery-build |
| 2026-10-31 | REVIEW ? PUBLISH | Independent gate PASS; local junction limitation documented | delivery-publish |

## Investigaci?n
### Requerimiento
Submit the existing .agents skill links so Codex can reuse Claude skills.
### Hechos encontrados
- `CLAUDE.md:11` identifies `.claude/skills/` as the delivery skill source.
- `.claude/skills/delivery-start/SKILL.md:2` defines the existing delivery-start skill.
- Filesystem inspection found eight Windows junctions under `.agents/skills`, all targeting matching `.claude/skills` directories.
- Git reports junction contents as untracked files; staging directories normally would duplicate skill content. Local core.symlinks is false.
### Hip?tesis / supuestos no confirmados
- No domain assumptions required.
### M?dulos y dependencias relacionadas
Agent discovery configuration only; no runtime dependencies.
### Comportamiento actual
Local junctions expose the skills, but are not yet versioned as links.
### Restricciones
Preserve existing junctions and unrelated untracked files. No product code changes.
### Riesgos identificados
Windows checkouts require symlink support to materialize Git symlinks; core.symlinks=false produces text placeholders.
### Veredicto de complejidad
**NEEDS_PLAN** ? Eight related configuration entries; no architecture or business change.
### Dise?o requerido
**NO** ? No UI.

## Dise?o
No aplica.
## Arquitectura
No architectural decision required.
## Plan
`docs/plans/PLAN-2026-10-31-link-claude-skills-codex.md` (v1), COMPACTO, READY.
## Implementaci?n
Recorded eight relative symlinks with Git mode 120000, each targeting ../../.claude/skills/<name>. Preserved local Windows junctions. No dependencies or product code changed.
## Review
PASS ? independent quality gate confirmed all eight index modes are 120000, exact relative link targets, existing target SKILL.md files, preserved local junctions, expected ten-file scope, and git diff --cached --check exit 0. Product tests, lint, build and security scans are not applicable to links and docs only.
## Publicaci?n
Ready for human review; no merge. Local working tree is not clean: preserved Windows junctions produce AD/type differences against Git symlinks with core.symlinks=false. Unrelated untracked design exports and package-lock remain excluded.
