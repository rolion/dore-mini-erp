# REV-2026-11-04-proformas-odontologicas-con-pieza-dental-01: La pieza dental acepta números/decimales y separadores de línea Unicode

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-proformas-odontologicas-con-pieza-dental.md (v1)
**Spec reference:** AC-02, INV-04
**Plan mode:** COMPLETO
**Suggested owner:** backend (delivery-build)

## Description
El serializer usa `serializers.CharField` para `dental_piece`. DRF convierte `int`/`float` a texto, por lo que el dominio (que sí rechaza lo que no es `str`) nunca ve el valor no textual. Además, `clean_piece` solo busca `\n` y `\r`; otros separadores de línea (U+2028, `\x0b`, `\x0c`) pasan.

## Expected behavior
AC-02: "que no sea texto da 400 con error en esa línea"; INV-04: "sin saltos de línea".

## Actual behavior
`dental_piece: 18` (número JSON) se guarda como `"18"` y `1.5` como `"1.5"` (201/200, sin error). `"1 2"` también se acepta. Lista/objeto/booleano sí dan 400.

## Evidence
Ejecutado con `ProformaInputSerializer`: `18 True 18`, `1.5 True 1.5`, `'1 2' True`; `['a']`, `{'a':1}`, `True` -> `False` (400). `test_proforma_domain.py` prueba `12` contra el dominio, pero ninguna prueba de API envía un número. Impacto bajo: el dato guardado es texto corto y el frontend siempre envía string.
