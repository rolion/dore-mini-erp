# REV-2026-11-24-crm-prospectos-oportunidades-01: Kanban ilegible en tema oscuro (columnas claras y etiquetas invisibles)

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-crm-prospectos-oportunidades.md (v1)
**Spec reference:** AC-10, UI-02; design-system §8 («Se ve bien … en tema claro y oscuro»), §7 (accesibilidad mínima)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En el tema oscuro de la app (clases `dark theme-black` en `body`, sin `data-bs-theme`), el tablero Kanban `crm-opportunity-board`:
1. Pinta las columnas con `background-color: var(--bs-tertiary-bg)` (`crm-opportunity-board.component.scss:26`), que en este skin sigue siendo `rgb(248, 249, 250)`: columnas blancas rodeando tarjetas oscuras.
2. Pinta las etiquetas `dt` de la tarjeta (Contacto, Importe, Siguiente acción, Responsable, Cerrada el, Motivo, Pedido) con `color: var(--bs-secondary-color)` (`:74`), que queda `rgba(33, 37, 41, 0.75)` sobre el fondo de tarjeta `rgb(22, 25, 42)`: contraste ≈1,1:1, las etiquetas son invisibles.

La lista de prospectos (`crm-lead-list.component.scss:97`, variante compacta bajo `lg`) tiene el mismo problema con las etiquetas Teléfono/Correo/Estado. Ahí repite un patrón que ya existe en otras listas (`crm-customer-list`, `customer-list`, `expense-list`), así que en esa pantalla es deuda heredada; en el Kanban la columna clara es nueva.

## Expected behavior
Columnas y etiquetas legibles en tema claro y oscuro, con contraste de texto ≥ 4.5:1 (§7), usando tokens/clases que el skin oscuro redefine (p. ej. los de `assets/scss/_dark-tokens.scss` / `skins/_dark.scss`, o clases existentes como `text-muted`), sin HEX nuevos.

## Actual behavior
En oscuro, a 1440 px y a 390 px: columnas con fondo claro y etiquetas de la tarjeta sin contraste. En claro se ve bien.

## Evidence
Revisión en el navegador integrado (backend `manage.py testserver` con base aislada `test_crm004_visual`, frontend `npm start`), tema oscuro elegido en el panel de ajustes de la app. Estilos calculados de la primera tarjeta en `/es/pocketbiz/crm/opportunities`:

```
{
  "bsTheme": null,
  "cardBg": "rgb(22, 25, 42)",
  "colBg": "rgb(248, 249, 250)",
  "colBorder": "rgb(222, 226, 230)",
  "ddColor": "rgb(150, 162, 180)",
  "dtColor": "rgba(33, 37, 41, 0.75)",
  "dtText": "Contacto",
  "header": "rgb(100, 120, 154)"
}
```

Capturas (1440 px y 390 px, oscuro): las tarjetas solo muestran los valores a la derecha; las etiquetas no se ven y la columna se ve blanca. En 390 px oscuro, `/es/pocketbiz/crm/leads` muestra igual las etiquetas «Teléfono», «Correo», «Estado» casi invisibles.

## Resolution
Corregido en `crm-opportunity-board.component.scss` y `crm-lead-list.component.scss` con `:host-context(.dark)` (fondo/borde de columnas y color de las etiquetas `dt` con `$color-font` #96a2b4, ~7:1 sobre el fondo oscuro). `npm run build` y `npm run lint` pasan; el CSS compilado contiene las reglas `.dark`. Sin recaptura visual en navegador.
