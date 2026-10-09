# REV-2026-10-09-gastos-reporting-mvp-01: El monto acepta notación científica (`1e3`) y los errores de monto ocultan los del dominio

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-09-gastos-reporting-mvp.md (v1)
**Spec reference:** EDGE-01, AC-04, INV-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
`POST/PATCH /api/expenses/` acepta el monto `"1e3"` (y `"1E3"`, `"1_000"`) y lo guarda como `1000.00`. La conversión la hace `serializers.DecimalField` (DRF) antes de llegar al dominio, y `shared.domain.money.parse_money` tampoco rechaza la notación científica (`Decimal('1e3')` es válido). Además, como el serializer falla primero, un monto no numérico junto a otros campos inválidos devuelve solo el error de `amount` y no acumula los del dominio.

## Expected behavior
EDGE-01: "Gasto con monto `0.001`, `1e3`, `"abc"`, `true` o `10000000000.00` → 400 en `amount`." AC-04: "los errores se acumulan por campo".

## Actual behavior
- `amount: "1e3"` → 201, `amount: "1000.00"`. `"1_000"` → 201.
- `{amount: "abc", description: ""}` (sin fecha) → 400 solo con `amount`; al corregir el monto aparecen `description` y `expense_date`.
- Los tests `test_api.py:136` y `test_domain.py:37` (marcados EDGE-01) no incluyen `1e3`, por eso la suite pasa.

## Evidence
Sondeo temporal con `APIClient` (archivo ya eliminado, sin cambios en el árbol):
```
PROBE amount '1e3' 201 b'{"id":"09a50c3d-...","description":"x","amount":"1000.00",...'
PROBE amount '1E3' 201 b'{"id":"8b0f2413-...","amount":"1000.00",...'
PROBE amount '1_000' 201 b'{"id":"4f65bdd4-...","amount":"1000.00",...'
PROBE amount '0.001' 400 {"amount":["Asegúrese de que no haya más de 2 decimales."]}
PROBE amount True 400 {"amount":["Se requiere un número válido."]}
PROBE mixed 400 b'{"amount":["Se requiere un número válido."]}'   # envió amount="abc", description="" y sin fecha
```
Impacto acotado (el frontend valida el monto y el importe resultante es correcto), de ahí Medium. Acción: rechazar en `parse_money` o en el serializer (p. ej. `CharField` + `parse_money`) los textos con exponente o `_`, y añadir `1e3` a los casos de EDGE-01.
