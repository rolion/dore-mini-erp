# REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-05: El frontend valida la longitud del código sin recortar

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-administrar-cuentas-codigo-clasificacion-estado.md (v3)
**Spec reference:** INV-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El formulario aplica `maxLength(20)` al valor con espacios de los bordes, mientras el backend recorta antes de validar.

## Expected behavior
Aceptar en el cliente un código de 20 dígitos aunque lleve espacios en los bordes.

## Actual behavior
`" 12345678901234567890 "` se rechaza en el cliente aunque el backend lo aceptaría. Cosmético: el atributo `maxlength` del campo casi siempre lo evita.

## Evidence
Informe del Quality Gate repetido, hallazgo 2. Observaciones menores sin REV propio: el serializer admite 64 caracteres y el mensaje de longitud sale del dominio; en el PLAN, API-04 está listado antes de API-03.
