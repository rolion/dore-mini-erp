# REV-2026-11-26-registrar-diagnostico-odontograma-inicial-06: Desviaciones menores del checklist de design-system (formato de fecha, presupuesto de estilos, tabla apilada)

**Status:** Closed
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md (v1)
**Spec reference:** docs/design/design-system.md sección 8 (formato `dd/MM/yyyy HH:mm`, bloques de plantilla, móvil ≈390 px); DDR de la pantalla de odontograma
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
- Fechas: la pantalla usa `date: 'short'` (`odontogram.component.html:96,99`, dependiente del locale) y el selector de versión muestra `clinical_date` en ISO `yyyy-MM-dd` (`optionLabel`, `odontogram.component.ts:149-153`), no `dd/MM/yyyy HH:mm` exigido por la checklist.
- `ng build` emite una advertencia de presupuesto: «src/app/features/dentistry/components/odontogram-chart.component.scss exceeded maximum budget. Budget 2.00 kB was not met by 657 bytes with a total of 2.66 kB.» (el build termina con exit 0).
- La tabla equivalente usa `table-responsive` y no la variante apilada < `lg` del DDR (ya declarada como desviación en `## Implementación` del TASK).
- La cabecera usa un texto «Migas › Paciente» (`html:12`) en lugar de un breadcrumb semántico de la plantilla.

## Expected behavior
Fechas en el formato del sistema de diseño, sin advertencias nuevas de build, y tabla/cabecera según el DDR y la plantilla de detalle.

## Actual behavior
Ver arriba. No se verificó visualmente (móvil/escritorio, claro/oscuro): revisión visual NO VERIFICADA.

## Evidence
Salida de `npm run build` (exit 0) con la advertencia de presupuesto citada; revisión de plantillas y TS.


## Verificación Quality Gate #2
Cerrado. Fechas dd/MM/yyyy (HH:mm donde aplica); `npm run build` ya no avisa del presupuesto de odontogram-chart.component.scss (solo avisos previos de customer-list y stock-list); tabla apilada < lg verificada en móvil 390 px; migas semánticas (nav/ol.breadcrumb). Queda un matiz de tema oscuro, registrado aparte como REV-08.
