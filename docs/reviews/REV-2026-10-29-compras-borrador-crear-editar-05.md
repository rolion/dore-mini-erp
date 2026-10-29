# REV-2026-10-29-compras-borrador-crear-editar-05: errores de forma en `items` salen como objeto indexado, no como lista por línea

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-compras-borrador-crear-editar.md (v1)
**Spec reference:** AC-03 («400 con `items: [{…}]` indexado por línea»), AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Los errores de dominio por línea (cantidad, precio, producto) salen como lista alineada por posición (`{"items": [{}, {"quantity": [...]}]}`), que es lo que interpreta `purchases-api.service.ts` (`Array.isArray(items)`). Pero los errores de forma que detecta `PurchaseItemInputSerializer` (falta `product_id`/`quantity`/`unit_price`, UUID inválido, línea que no es objeto, `items` que no es lista) los serializa DRF como objeto indexado por posición o anidado (`{"items": {"0": {...}}}`, `{"items": {"non_field_errors": [...]}}`). El contrato tiene entonces dos formas para la misma clave `items`. El formulario Angular nunca envía esos casos (valida antes), así que el impacto es para otros clientes de la API; si llegara uno, la pantalla no ubicaría el error y mostraría el mensaje general.

## Expected behavior
Un único formato para `items` en todo 400: lista con un objeto por línea (o lista de textos para errores globales como «máximo 200 líneas»).

## Actual behavior
Dos formatos según el origen del error.

## Evidence
Ejecutado con `APIClient` (SQLite, settings.test), POST `/api/purchases/` con cabecera válida:
```
items=[{}]   -> 400 {"items":{"0":{"product_id":["Este campo es requerido."],"quantity":["Este campo es requerido."],"unit_price":["Este campo es requerido."]}}}
items=[1]    -> 400 {"items":{"0":{"non_field_errors":["Datos inválidos. Se esperaba un diccionario pero es un int."]}}}
items={"a":1}-> 400 {"items":{"non_field_errors":["Se esperaba una lista de elementos en vez del tipo \"dict\"."]}}
cantidad '1'*40 (dominio) -> 400 {"items":[{"quantity":["La cantidad no puede superar 99999999.999."]}]}
```
Corrección sugerida: normalizar los errores del serializer de `items` a la forma de lista antes de responder (o documentar ambas formas en el contrato y que el servicio Angular las lea) y añadir una prueba de API.
