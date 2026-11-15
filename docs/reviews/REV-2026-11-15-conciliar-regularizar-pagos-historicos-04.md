# REV-2026-11-15-conciliar-regularizar-pagos-historicos-04: DDR y design-system no reflejan el alcance del resumen, la columna «Qué pasa» ni la alerta tenue

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md (v2)
**Spec reference:** UI-03; design-system.md §5/§8 (la referencia visual debe reflejar lo construido); DDR-conciliar-regularizar-pagos-historicos-pantalla-regularizacion
**Plan mode:** COMPLETO
**Suggested owner:** delivery-ui-design / delivery-frontend

## Description
Tras los ajustes de UX y la corrección de REV-2026-11-15-01, la pantalla tiene: titular de resultado, columna «Qué pasa» con `app-status-badge`, lista de alcance (`data-testid="scope"`: periodo, reglas aplicadas, métodos sin regla) y alertas tenues (`alert alert-info bg-info-subtle text-info-emphasis border-info-subtle`) en el resumen y en el diálogo. La documentación de diseño solo recoge parte de eso.

## Expected behavior
`design-system.md` (variante «de operación con previsualización obligatoria») y el DDR describen el diseño final: alcance bajo el titular, columna «Qué pasa», y la alerta tenue (clase no usada en ningún otro sitio del producto) como patrón admitido, para que otras pantallas lo repliquen o no lo reinventen.

## Actual behavior
- `design-system.md` menciona el titular y la columna «Qué pasa», pero no la lista de alcance ni la alerta tenue (`grep -n "bg-info-subtle\|tenue" docs/design/design-system.md` → sin coincidencias).
- El DDR sigue en `Estado: Propuesto`, describe el resumen como `alert alert-info` fijo y «tabla con filas Faltantes, Existentes, …» (sin titular, sin columna «Qué pasa», sin alcance) y dice «Sin deuda visual aceptada».
- `bg-info-subtle` solo aparece en `regularization.component.html`, `regularization-confirm-dialog.component.html` y `shared/components/status-badge`.

## Evidence
- `grep -rln "bg-info-subtle" frontend/panel_admin/src/app` → los tres archivos anteriores.
- `docs/design/DDR-conciliar-regularizar-pagos-historicos-pantalla-regularizacion.md`: líneas «Estado: Propuesto» y paso 2 «Resumen» sin mención de titular/«Qué pasa»/alcance.
- Impacto: documental; no afecta al comportamiento ni a los datos.
