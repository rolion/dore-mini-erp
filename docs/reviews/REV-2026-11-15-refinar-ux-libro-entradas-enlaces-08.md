# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-08: Los enlaces `link-primary` no llegan a 4,5:1 en tema oscuro

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md (v2)
**Spec reference:** AC-03 / AC-05 (contraste, tema oscuro)
**Plan mode:** COMPACTO
**Suggested owner:** delivery-build

## Description
Los enlaces `link-primary` no llegan a 4,5:1 en tema oscuro.

## Expected behavior
Enlaces con contraste ≥ 4,5:1 en tema claro y oscuro.

## Actual behavior
Claro: 4,50:1. Oscuro: 3,87:1 (#0d6efd sobre rgb(22,25,42)).

## Evidence
Medido con estilos computados. El tema oscuro se emuló con clases `dark`/`data-bs-theme` manualmente, no con el selector real del tema; confirmar con el selector. Los demás textos pasan (7,98 a 17,4:1).

## Resolution
Parcial `_entry-links.scss` compartido por lista y detalle: en `.dark` se ajusta `--bs-primary-rgb` (el `.link-primary` de Bootstrap usa `!important`) a 110,168,254 y se mantiene ese color en hover/foco (el hover de Bootstrap es un azul oscuro fijo). Medido en navegador (API simulada, `.dark` emulado): oscuro 7,21:1; claro sin cambios 4,50:1. El selector real de tema no se probó.
