# REV-2026-10-27-habilitar-modulos-por-empresa-03: Destino post-login e icono de inicio siguen apuntando a `/dashboard/main` (oculto si Reportes está deshabilitado)

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-27-habilitar-modulos-por-empresa.md (v1)
**Spec reference:** EDGE-04; TASK «Hipótesis» (destino post-login = primer ítem visible)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
La TASK indica que, con Reportes deshabilitado, el destino tras login pasa a ser el primer ítem visible. La implementación no cambia `DEFAULT_ROUTE_AFTER_LOGIN`/`DEFAULT_ROUTE_AFTER_SIGNUP` (`/dashboard/main`) ni los enlaces de inicio del breadcrumb y «Volver al panel»; el resultado correcto lo da `moduleGuard`, que redirige a `/catalog/products`. Funciona (EDGE-04 se cumple), pero con un salto extra de redirección y la desviación no está documentada (el plan/EDGE-04 solo exige la redirección por URL). Además el diálogo usa la etiqueta «Afectados» en lugar de «Se verán afectados» del DDR (cosmético).

## Expected behavior
Destino coherente sin depender de una ruta oculta, o desviación documentada.

## Actual behavior
Redirección vía guard; ningún texto del Plan/TASK describe la decisión.

## Evidence
`frontend/panel_admin/src/app/authentication/signin/signin.component.ts:10` (`DEFAULT_ROUTE_AFTER_LOGIN = '/dashboard/main'`), `core/guard/module.guard.ts` (`MODULE_DISABLED_REDIRECT = '/catalog/products'`), `features/settings/pages/module-list/module-list.component.html` y `coming-soon.component.ts` (`routerLink="/dashboard/main"`), `module-confirm-dialog.component.html` (`<dt>Afectados</dt>`). No verificado en navegador.
