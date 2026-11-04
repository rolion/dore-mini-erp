# REV-2026-11-04-proformas-odontologicas-con-pieza-dental-04: Contraste insuficiente en textos de ayuda y badges (tema de la plantilla)

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-04-proformas-odontologicas-con-pieza-dental.md (v1)
**Spec reference:** AC-10 (accesibilidad), `design-system.md` sección 8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start (sistema de diseño)

## Description
Medición con la fórmula WCAG sobre los colores calculados de las pantallas nuevas.

## Expected behavior
Contraste mínimo 4.5:1 para texto normal.

## Actual behavior
- Tema oscuro, formulario: textos de ayuda `text-muted` (p. ej. «Opcional. Número o código del diente…», «No incluyas diagnósticos…») 3.9:1; botón «Guardar borrador» 4.1:1.
- Tema claro, tarjeta de la ficha: badges `col-orange` «Borrador» 2.2:1 y `col-blue` «Presentada» 3.1:1; enlaces y botones primarios 4.1:1; «N proformas» 2.5:1.
Son colores de la plantilla Oreva compartidos por el resto de la aplicación (badges `col-*`, `text-muted`, botón primario); no son específicos de esta funcionalidad.

## Evidence
Navegador integrado, 1440 px y 390 px, tema claro y oscuro (cálculo en página con `getComputedStyle`). Sin cambio en esta rama: corregirlo implica ajustar los tokens del sistema de diseño, fuera del alcance de la tarea.
