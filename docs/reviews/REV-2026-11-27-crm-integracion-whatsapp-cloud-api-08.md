# REV-2026-11-27-crm-integracion-whatsapp-cloud-api-08: Pestañas ARIA sin navegación por teclado y copiado sin manejo de error ni anuncio

**Status:** Closed
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md (v1)
**Spec reference:** UI-01, UI-03; design-system sección 8 (accesibilidad)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La pantalla usa `role="tablist"/"tab"/"tabpanel"` (corrección de REV-04) pero sin el patrón de teclado de WAI-ARIA: todas las pestañas son tabulables (sin `tabindex` itinerante) y no responden a flechas/Inicio/Fin. Además `copy()` encadena `.then` sin `.catch` (rechazo del portapapeles no manejado, sin mensaje al usuario) y el cambio «Copiar»→«Copiado» no está en una región `aria-live`.

## Expected behavior
Pestañas con `tabindex` itinerante y flechas, o usar los roles nativos de botones/enlaces sin `role=tab`; copiado con feedback de error y anuncio accesible.

## Actual behavior
Ver Description. Verificación visual a 390/1440 px NO realizada (no se levantó la app para no tocar la BD compartida): estos puntos salen de leer plantilla/componente.

## Evidence
`whatsapp-integration.component.html` (botones `role="tab"` con `(click)` solo); `whatsapp-integration.component.ts::copy`: `void navigator.clipboard?.writeText(value).then(() => (this.copied = key));`.

## Resolución
`onTabKeydown` implementa flechas, Inicio y Fin con `tabindex` itinerante y foco al activar; `copy()` maneja el rechazo/ausencia del portapapeles (`copyError` con aviso) y hay una región `aria-live="polite"` para «Copiado». Pruebas nuevas en el spec; i18n es/en/pt (`COPIADO_AVISO`, `COPIAR_ERROR`). Verificación visual a 390/1440 px sigue sin realizarse.
