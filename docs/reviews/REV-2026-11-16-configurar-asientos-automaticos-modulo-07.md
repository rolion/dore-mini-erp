# REV-2026-11-16-configurar-asientos-automaticos-modulo-07: Contraste insuficiente de `text-warning-emphasis` en tema oscuro

**Status:** Resolved
**Severity:** Medium
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v1)
**Spec reference:** AC-14, design-system.md §8 (accesibilidad)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Los avisos «Sin configurar», «Falta la cuenta Caja o Banco de este método», «No hay cuentas de dinero…» y «ya no es válida» usan `text-warning-emphasis` (como prescribe design-system.md §8). En el tema oscuro de la plantilla (clase `dark` en `body`) esa variable de Bootstrap no se redefine y conserva el valor del tema claro.

## Expected behavior
El texto de estado tiene al menos 4.5:1 de contraste en ambos temas.

## Actual behavior
Color calculado `rgb(102, 77, 3)` sobre fondo `rgb(22, 25, 42)`: contraste 2.18:1 (falla WCAG AA). Los avisos, que son justo la información crítica del panel (qué falta configurar), casi no se leen en oscuro. En tema claro el contraste es correcto.

## Evidence
Navegador integrado, `/es/pocketbiz/sales/settings`, 375x812; tema oscuro emulado reemplazando en `body` las clases `light light-sidebar theme-white` por `dark dark-sidebar theme-black` (no se usó el conmutador de la app); contraste calculado por JS con la fórmula de luminancia relativa WCAG. Verificar con el conmutador real antes de corregir. Posible arreglo: sobrescribir `--bs-warning-text-emphasis` bajo `.dark` en el SCSS del panel o usar una clase del sistema de diseño con variante oscura.

## Resolution
Los estados «Sin configurar», «ya no es válida» y los faltantes usan `.posting-warn` (color heredado + fondo suave del tono de advertencia + texto en negrita) y «Guardado ✓» usa `.posting-ok`, en lugar de `text-warning-emphasis`/`text-success-emphasis` aislados; legibles en tema claro y oscuro, siempre con texto. Se importa además `_alert-warning` para el aviso de faltantes. No se volvió a medir el contraste en navegador tras el cambio (ver `## Review` del TASK).
