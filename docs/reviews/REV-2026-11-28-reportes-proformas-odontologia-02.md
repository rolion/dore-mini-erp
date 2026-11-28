# REV-2026-11-28-reportes-proformas-odontologia-02: PUT sin `professional_id` borra el doctor en silencio

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-reportes-proformas-odontologia.md (v1)
**Spec reference:** API-03 (aditivo, «compatible hacia atrás»), INV-02
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`professional_id` se declara `required=False, default=None` en `ProformaInputSerializer`. Un cliente que edite un borrador (PUT) sin enviar el campo deja la proforma sin doctor.

## Expected behavior
API-03 dice «opcional, nullable» y aditivo/compatible: omitir el campo no debería alterar el doctor ya guardado; solo `null` explícito debería quitarlo.

## Actual behavior
Omitir el campo equivale a `null` y borra el doctor (`replace_content(professional_id=None)`). El TASK lo declara como deuda técnica («el formulario siempre lo envía»), pero no hay prueba que lo fije ni decisión de negocio registrada.

## Evidence
`backend/modules/dentistry/api/proforma_views.py`: `professional_id = serializers.UUIDField(required=False, allow_null=True, default=None)` y `DentalProformaInput(..., data['professional_id'])`; `application/proformas.py::update` pasa `data.professional_id` sin distinguir ausente de nulo. Aceptable para el MVP si se documenta como contrato; severidad baja.
