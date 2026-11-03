# REV-2026-11-02-perfil-odontologico-pacientes-01: Regresión del menú y traducciones incompletas

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-02-perfil-odontologico-pacientes.md (v1)
**Spec reference:** AC-07; paso 4 del plan (navegación)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La incorporación de Odontología en routes.json rompe dos pruebas existentes de integración del menú. Las expectativas de estructura siguen describiendo el menú anterior y faltan las traducciones en/de de las dos claves nuevas. Es consecuencia directa del cambio, no deuda ajena.

## Expected behavior
El contrato del menú debe incorporar Odontología y sus traducciones en los diccionarios que soporta la aplicación, conservando verdes las pruebas del sidebar.

## Actual behavior
El suite completo termina con dos fallos en sidebar-menu.spec.ts; el resto de 1081 pruebas pasa.

## Evidence
Código revisado: b0086a9. Ejecución real por el orquestador, salida leída directamente por Quality Gate en `C:/Users/Lion/AppData/Local/Temp/pb-odo-001-gate-frontend.log`.

Comando: `node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless --code-coverage --preserve-symlinks`.

```text
Sidebar menu (routes.json) has a translation in en, es and de for every menu title (AC-09) FAILED
Expected 27 to be 25.
at UserContext.<anonymous> (src/app/layout/sidebar/sidebar-menu.spec.ts:77:27)
en: MENUITEMS.DENTISTRY.TEXT: Expected 'undefined' to be 'string'.
en: MENUITEMS.DENTISTRY.PATIENTS: Expected 'undefined' to be 'string'.
Sidebar menu (routes.json) has the business menu, Purchases, Inventory and Settings > Modules (AC-09, AC-20, AC-22, UI-01) FAILED
Expected 10 to be 9.
at UserContext.<anonymous> (src/app/layout/sidebar/sidebar-menu.spec.ts:16:27)
Expected $[3] = 'dentistry' to equal 'sales'.
Expected $[4] = 'sales' to equal 'expenses'.
Expected $[5] = 'expenses' to equal 'reporting'.
TOTAL: 2 FAILED, 1081 SUCCESS
```

Los IDs AC-09/20/22 de estos nombres de test pertenecen a regresiones previas; la referencia de Specification de este hallazgo es AC-07 del plan vigente. La skill delivery-publish exige FAIL ante cualquier test fallando sin autorización explícita, incluso con severidad Medium.
