# REV-2026-11-26-registrar-diagnostico-odontograma-inicial-08: En tema oscuro los contornos de las piezas «Sin evaluar» y el borde de «Implante» son casi invisibles

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md (v1)
**Spec reference:** AC-11 / UI-02 (gráfico con leyenda y distinción visual de «Sin evaluar»); docs/design/design-system.md sección 8 (tema claro y oscuro)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`odontogram-chart.component.scss` dibuja los polígonos de cada pieza con `stroke: var(--bs-body-color)` y el swatch de la leyenda con `border: 1px solid var(--bs-body-color)`. En la plantilla Oreva el tema oscuro se activa con la clase `dark` en `body` y `--bs-body-color` sigue valiendo `#212529`, de modo que el trazo oscuro queda sobre la tarjeta oscura.

## Expected behavior
En tema oscuro todas las piezas (también las «Sin evaluar») muestran un contorno legible y los swatches de la leyenda (p. ej. IMP) se distinguen del fondo.

## Actual behavior
En tema oscuro (escritorio 1440 px y móvil 390 px) las piezas sin hallazgos aparecen como un cuadro casi vacío y el color «Implante» (`fill-dark`) no se distingue. La información no se pierde (cada pieza lleva su número, T/P y la abreviatura «S/E»/«CAR+», y la tabla es equivalente), por eso es Low; en tema claro todo se ve bien.

## Evidence
Revisión visual en navegador con el tema oscuro del panel de ajustes. Estilos computados de `.odo-tooth.unevaluated polygon`: `stroke: rgb(33, 37, 41)` sobre fondo de tarjeta `rgb(22, 25, 42)` (contraste ≈ 1.1:1). `getComputedStyle(body).color` = `rgb(0, 0, 0)` y `--bs-body-color` = `#212529` aun con `body.dark`.
