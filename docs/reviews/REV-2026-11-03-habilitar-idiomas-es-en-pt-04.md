# REV-2026-11-03-habilitar-idiomas-es-en-pt-04: Línea base de pruebas del plan (1 227) no coincide con la real

**Status:** Open
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-03-habilitar-idiomas-es-en-pt.md (v1)
**Spec reference:** Regression tests
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El plan cita 1 227 pruebas existentes; el conteo real es menor.

## Expected behavior
Cifra de línea base exacta para poder detectar pruebas perdidas.

## Actual behavior
`main` tiene 1099 bloques `it(` y HEAD 1125 (+26 netos); Karma ejecuta 1147 en HEAD. Se reescribió `language.service.spec.ts` (4 `it` eliminados, otros nuevos). No se detectó pérdida de cobertura, pero la cifra del plan es incorrecta.

## Evidence
```
Chrome Headless 156.0.0.0 (Windows 10): Executed 1147 of 1147 SUCCESS
git grep "^\s*(it|fit)\(" main -> 1099 ; HEAD -> 1125
```
