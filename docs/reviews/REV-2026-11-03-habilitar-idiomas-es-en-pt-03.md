# REV-2026-11-03-habilitar-idiomas-es-en-pt-03: Fallo de carga de catálogo al cambiar de idioma no muestra aviso

**Status:** Resolved (corregido en delivery-build; verificación de la corrección sin Quality Gate aislado nuevo)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-habilitar-idiomas-es-en-pt.md (v1)
**Spec reference:** EDGE-03, UI-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Si falla la carga del catálogo al elegir idioma, `setLanguage` retorna en silencio.

## Expected behavior
Se mantiene el idioma anterior y se muestra un aviso breve; el selector sigue operativo.

## Actual behavior
Se mantiene el idioma anterior pero la persona no recibe ningún aviso.

## Evidence
```
core/service/language.service.ts:77-80
    } catch {
      // Catálogo no disponible (EDGE-03): se mantiene el idioma anterior.
      return;
    }
```
