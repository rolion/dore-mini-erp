# PLAN-2026-10-31-link-claude-skills-codex (v1)

**Task:** TASK-link-claude-skills-codex ? **Modo:** COMPACTO ? **Specification readiness:** READY
**DDRs / ADRs:** Ninguno

## Objective
Version the existing Codex skill links while keeping Claude skills as the single source.

# Specification
- **Expected behavior:** Each of the eight existing .agents/skills entries is a relative symlink to its matching .claude/skills directory.
- **Acceptance criteria:** All eight entries have Git mode 120000 and target ../../.claude/skills/<name>; each target contains SKILL.md. Existing local junctions and unrelated files remain intact.
- **Edge/error cases:** Do not commit expanded junction contents or absolute machine-specific paths. Windows clones need symlink support; core.symlinks=false creates placeholders.
- **Out of scope:** Skill content, application code, global Git settings, and unrelated files.

# Test Specification
Inspect Git index modes and link blobs, verify all relative targets resolve to SKILL.md, compare local junction targets, and run git diff --cached --check. Review final commit scope. Application tests/lint/build/security scans are not applicable because only links and workflow documentation change.
**E2E: NO** ? No application behavior changes.

# Implementation Plan
- **Files affected:** Eight .agents/skills symlink entries and this task/plan documentation.
- **Steps:** Preserve local junctions; stage portable relative link blobs with mode 120000; verify targets and scope; commit and push one task branch; independently review and open one PR.
- **Risks / New dependencies:** Windows symlink checkout support required; no new dependencies.
