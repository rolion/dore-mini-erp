# REV-2026-10-30-integracion-recepciones-entradas-inventario-03: Detalle documental muestra dos mensajes y la marca de entrada no es badge

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-10-30-integracion-recepciones-entradas-inventario.md (v1)
**Spec reference:** AC-14, UI-01, UI-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build (frontend)

## Description
En reception-detail.component.html, con inventoryMode documental, movements es null y se cae en la rama else que añade «Esta recepción no movió existencias.» además de la alerta «Recepción documental, sin movimiento de inventario». En el resumen del formulario, UI-01 pide un badge «Entrada de stock» y se implementó como texto small text-muted.

## Expected behavior
Un único mensaje en modo documental; badge según UI-01.

## Actual behavior
Mensaje redundante en modo documental; texto atenuado en lugar de badge. Los textos exactos pedidos sí están presentes.

## Evidence
reception-detail.component.html (documental-note + no-movements); reception-form.component.html (data-testid=line-entry). Revisión visual no verificada.
