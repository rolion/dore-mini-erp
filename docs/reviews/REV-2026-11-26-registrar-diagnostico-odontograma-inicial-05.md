# REV-2026-11-26-registrar-diagnostico-odontograma-inicial-05: UI-04 incompleto (sin foco al primer campo inválido, aria-invalid solo en la fecha)

**Status:** Resuelto en delivery-build (pendiente de re-revisión)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md (v1)
**Spec reference:** UI-04 («`aria-invalid`/`role="alert"` en errores, foco al primer campo inválido…»); design-system.md sección 7 y 8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
- `odontogram.component.ts` no contiene ninguna llamada a `focus()`; al fallar `addFinding()` / `addGeneral()` / `saveDraft()` solo se rellenan listas de mensajes con `role="alert"` (`odontogram.component.html:191,252`), sin mover el foco al campo inválido.
- `aria-invalid` solo se aplica a la fecha clínica (`html:83`); condición, superficies, nota obligatoria («Otro»), diagnóstico general y motivo de enmienda no lo llevan, y los errores no se asocian a su campo con `aria-describedby`.
- Los botones de pestaña Gráfico/Tabla usan `role="tab"` pero no implementan navegación con flechas ni `tabindex` itinerante (patrón WAI-ARIA de tabs).

## Expected behavior
Al fallar la validación el foco va al primer campo inválido, que lleva `aria-invalid="true"` y `aria-describedby` hacia su mensaje; los roles ARIA usados se comportan según su patrón.

## Actual behavior
Ver arriba. El gráfico sí tiene navegación por flechas (prueba `odontogram-chart.component.spec.ts:62`), así que el hueco está en formularios y pestañas.

## Evidence
`grep -n "focus" odontogram.component.ts` → sin resultados; revisión de `odontogram.component.html` líneas 83, 121-126, 191, 252.
