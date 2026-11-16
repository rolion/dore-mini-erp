# REV-2026-11-16-periodos-fiscales-por-empresa-09: Sin restricción de exclusión en base de datos

**Status:** Closed (informativo: decisión consciente del ADR)
**Severity:** Low
**Category:** ARCHITECTURE
**Related plan:** docs/plans/PLAN-2026-11-16-periodos-fiscales-por-empresa.md (v1)
**Spec reference:** INV-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La no superposición depende del advisory lock (decisión consciente del ADR); un escritor fuera del repositorio podría violarla.

## Expected behavior
Informativo; revisar si se habilita btree_gist.

## Actual behavior
Ver descripción.

## Evidence
Quality Gate (subagente aislado), ADR decisión 3. Backend 1678 OK; frontend 1430 OK (2 de 3 corridas, ver nota del flake preexistente `screens-i18n.spec.ts:58-65`, ajeno al diff).
