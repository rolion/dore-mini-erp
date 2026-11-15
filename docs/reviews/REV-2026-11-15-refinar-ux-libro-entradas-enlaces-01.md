# REV-2026-11-15-refinar-ux-libro-entradas-enlaces-01: Enlaces de Documento sin aria-label

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md (v1)
**Spec reference:** AC-03
**Plan mode:** COMPACTO
**Suggested owner:** delivery-build

## Description
Enlaces de Documento sin aria-label.

## Expected behavior
Documento (lista y detalle) lleva aria-label traducido como Comprobante.

## Actual behavior
Solo Comprobante (receipt-link) tiene [attr.aria-label]; source-link no, y ninguna prueba lo verifica.

## Evidence
entry-list.component.html y entry-detail.component.html: `source-link` sin `[attr.aria-label]`. El texto visible ya es legible, por eso Low.

## Resolution
Corregido: `aria-label` `VER_DOCUMENTO_N` en lista y detalle, con prueba.
