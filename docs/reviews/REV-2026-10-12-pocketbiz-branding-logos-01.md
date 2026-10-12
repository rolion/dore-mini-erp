# REV-2026-10-12-pocketbiz-branding-logos-01: Restos violáceos del primario antiguo (halo `#acb5f6` y muestra "purple")

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-12-pocketbiz-branding-logos.md (v3)
**Spec reference:** AC-06 (intención: sin zonas del primario antiguo), EDGE-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
El reemplazo de `#6777ef` dejó dos restos del primario antiguo / mal mapeados:
1. `override/_button.scss:158` — `.btn-edit-custom` tiene ahora fondo `#1677FF` pero conserva `box-shadow: 0 2px 6px #acb5f6` (tinte claro del `#6777ef`), por lo que el botón lleva un halo violeta.
2. `components/_settingSidebar.scss:76-80` — la muestra `ul.choose-theme li div.purple` pasó de `#6777ef` a `#1677ff`, pero el skin `purple` sigue usando `#5864bd` (`skins/_purple.scss`). La muestra "purple" del right-sidebar ya no representa el skin que activa (EDGE-04: los skins alternativos conservan sus colores).

## Expected behavior
AC-06: "ningún archivo conserva `#6777ef`…" cumple en forma literal, pero la Specification busca que no queden zonas con el primario antiguo; EDGE-04 pide que los skins alternativos conserven sus colores propios.

## Actual behavior
Halo `#acb5f6` junto a un botón azul `#1677FF`; muestra "purple" con el azul de marca en lugar del violeta del skin.

## Evidence
```
$ grep -rniE "rgba?\(\s*103\s*,\s*119\s*,\s*239|6777ef|acb5f6" src
src/assets/scss/override/_button.scss:158:  box-shadow: 0 2px 6px #acb5f6 !important;
src/assets/scss/_helpers.scss:7:  indigo: #6777ef,          (excepción permitida por AC-06)
```
`_settingSidebar.scss` (diff del PR): `-    background: #6777ef;` / `+    background: #1677ff;` en `ul.choose-theme li div.purple`; `_purple.scss:3`: `$color-primary: #5864bd;`.
Cosmético; no afecta pantallas del MVP (`btn-edit-custom` solo se usa en `widget/data-widget`).
