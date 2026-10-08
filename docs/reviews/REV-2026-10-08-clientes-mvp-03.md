# REV-2026-10-08-clientes-mvp-03: AC-08 promete 404 `{detail}` para ids que no son UUID, pero responde la página 404 de Django

**Status:** Closed (verificado en re-review sobre 58e1784)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-08-clientes-mvp.md (v1)
**Spec reference:** AC-08 ("id inexistente o que no es UUID → 404 `{detail}`"), "Error cases" (404 `{detail: "Cliente no encontrado."}`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-plan

## Description
Las rutas usan el convertidor `<uuid:customer_id>` (mismo patrón que `catalog`, ADR-contrato-api). Una URL con un id mal formado no llega a la vista: Django responde su 404 genérico (HTML), no el JSON `{detail}` descrito en el AC. El status 404 sí coincide y el test existente solo verifica el status. Es un desajuste de redacción de la Specification respecto de un patrón ya aceptado en el proyecto, no un defecto de la implementación.

## Expected behavior
AC-08: 404 con cuerpo `{detail}` también para ids que no son UUID.

## Actual behavior
404 con la página HTML de Django (con `DEBUG=False`, el 404 estándar de Django), sin `{detail}`.

## Evidence
```
GET /api/customers/not-a-uuid/  (Authorization: Token ...)
-> [404] <!DOCTYPE html> ... Page not found ...
```
`test_unknown_and_malformed_ids_return_404` pasa porque solo comprueba `status_code == 404`.

## Required action
`delivery-plan` (v2, junto con REV-01): acotar el texto de AC-08 a "404" para ids mal formados (el cuerpo `{detail}` aplica solo a UUID válidos inexistentes), o decidir con el usuario si se quiere JSON en todo 404 de la API (cambio transversal, fuera de este task).
