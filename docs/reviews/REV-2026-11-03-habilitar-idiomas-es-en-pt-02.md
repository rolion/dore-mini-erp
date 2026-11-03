# REV-2026-11-03-habilitar-idiomas-es-en-pt-02: Faltan pruebas por feature en en/pt, autenticación y casos de borde previstos

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-habilitar-idiomas-es-en-pt.md (v1)
**Spec reference:** Test Specification (Integration tests); AC-03, AC-07, AC-08, AC-11, EDGE-03, EDGE-04, EDGE-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige una prueba por feature en `en` y `pt` (par de textos clave), specs de autenticación con textos y selector, prueba de respaldo a español (EDGE-04), prueba del aviso por fallo de catálogo (EDGE-03), redirect de 401 conservando el prefijo y URLs legacy (`/#/…`, `/authentication/signin`) dentro del router con prefijo.

## Expected behavior
Verificación automatizada de AC-03/AC-07/AC-08 en en/pt por feature y de los bordes citados.

## Actual behavior
Solo hay specs en en/pt para landing, selector, sidebar, serializer, language.service, catálogos y language-routing. Ningún spec de feature ni de signin/signup/forgot/reset usa `provideTestTranslations('en'|'pt')`. No hay prueba de EDGE-04, EDGE-03 ni del interceptor 401 con prefijo; las URLs legacy solo se prueban sin idioma.

## Evidence
```
specs que usan 'en'/'pt': core/i18n/catalogs.spec.ts, language-url.serializer.spec.ts, language.service.spec.ts,
  features/landing/pages/landing/landing.component.i18n.spec.ts, layout/sidebar/sidebar-menu.spec.ts,
  shared/components/language-selector/language-selector.component.spec.ts
Legacy: core/routing/app-routes.spec.ts:110-116, core/routing/legacy-hash-redirect.spec.ts (sin prefijo de idioma)
Cobertura global: Statements 86.4% | Branches 77.83% | Functions 81.47% | Lines 87.49%
```
