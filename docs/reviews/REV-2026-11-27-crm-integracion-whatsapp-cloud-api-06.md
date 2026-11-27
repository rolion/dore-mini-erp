# REV-2026-11-27-crm-integracion-whatsapp-cloud-api-06: PLAN, DDR, TASK y ADR no reflejan el prefijo de secretos por empresa ni `secret_ref_prefix`

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md (v1)
**Spec reference:** API-03, INV-05, UI-01; DDR pantalla de integración WhatsApp
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
La corrección de REV-01 añade la regla «`secret_ref`/`app_secret_ref` deben empezar con `WHATSAPP_<12 hex del company_id>_`» y el campo `secret_ref_prefix` en GET/PUT de la conexión, pero los artefactos contractuales quedaron sin actualizar o contradictorios: PLAN API-03 lista los campos sin `secret_ref_prefix` ni la regla; el DDR describe los campos de nombre de variable sin prefijo ni ayuda; `docs/tasks/...` (Desviaciones) sigue diciendo «`secret_ref` solo admite nombres `WHATSAPP_*`» (la corrección está en un párrafo aparte); el ADR punto 9 afirma que «los serializers no exponen los refs completos de vuelta», pero la API sí devuelve `secret_ref` y `app_secret_ref` (TASK lo reconoce).

## Expected behavior
PLAN (API-03/INV-05) y DDR documentan la regla del prefijo y el campo; TASK y ADR sin afirmaciones contradictorias.

## Actual behavior
Ver Description; el PLAN v1 es el contrato contra el que se revisa y no incluye el comportamiento nuevo.

## Evidence
`grep -n -i "secret_ref\|prefijo" docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md` → solo líneas 25, 38, 53, 66 (sin prefijo). `grep -n -i "prefijo\|secret" docs/design/DDR-crm-integracion-whatsapp-cloud-api-pantalla-de-integracion-whatsapp.md` → línea 16 (sin prefijo). `backend/modules/messaging/api/serializers.py::connection_data` devuelve `secret_ref` y `app_secret_ref`.
