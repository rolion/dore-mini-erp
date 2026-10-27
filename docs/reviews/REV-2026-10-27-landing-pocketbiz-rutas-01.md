# REV-2026-10-27-landing-pocketbiz-rutas-01: documentos de diseño siguen citando las rutas antiguas

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-13-landing-pocketbiz-rutas.md (v2)
**Spec reference:** AC-17 ("`CLAUDE.md` y los documentos de diseño citan las rutas nuevas"); plan, paso 9 ("docs de diseño")
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`CLAUDE.md` y el DDR de esta task ya usan `/pocketbiz/...`, pero los documentos de diseño que la landing toma como fuente siguen con las rutas anteriores a `/pocketbiz` como rutas de destino vigentes. Solo `landing-pagina-principal.md:174` y `ux-brief.md:230` anotan la decisión Q7. El resto (CTA, AC-L02, estado con sesión) contradice lo implementado y puede inducir a error a quien lea la spec.

## Expected behavior
AC-17: los documentos de diseño citan las rutas nuevas (`/pocketbiz/signup`, `/pocketbiz/login`, `/pocketbiz/dashboard/main`), o llevan una nota explícita de que están superados por Q7/DDR.

## Actual behavior
Siguen citando rutas antiguas como destino vigente:
- `docs/design/specs/landing-pagina-principal.md:15,16,109,137,143,158` (`/authentication/signup`, `/authentication/signin`, `/dashboard/main`).
- `docs/design/ux-brief.md:22,120,121,122,162,179` (ídem).
- `docs/design/design-system.md:107` (`/dashboard/main`).

## Evidence
```
$ grep -nE "/authentication|/dashboard/main|/#/" docs/design/specs/landing-pagina-principal.md docs/design/ux-brief.md docs/design/design-system.md
docs/design/specs/landing-pagina-principal.md:15:- **Acción principal:** "Empezar gratis" → `/authentication/signup`.
docs/design/specs/landing-pagina-principal.md:16:- **Secundaria:** "Iniciar sesión" → `/authentication/signin`; anclas internas.
docs/design/specs/landing-pagina-principal.md:158:- **AC-L02:** todo CTA primario navega a `/authentication/signup`; "Iniciar sesión" a `/authentication/signin`.
docs/design/ux-brief.md:120:| CTA primario | **Empezar gratis** | `/authentication/signup` |
docs/design/design-system.md:107:... icono de inicio hacia `/dashboard/main` ...
```
Nota: los DDR históricos de tasks anteriores (catálogo, gastos, registro) también las citan; se consideran registro histórico y no se incluyen en este hallazgo.
