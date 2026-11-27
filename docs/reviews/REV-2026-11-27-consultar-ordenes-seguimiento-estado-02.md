# REV-02: AC-07 sin prueba directa para "Listo para empacar" y una asercion tautologica en EDGE-02

- **Status:** Open
- **Severity:** Low
- **Category:** IMPLEMENTATION
- **Related plan:** PLAN-2026-11-27-consultar-ordenes-seguimiento-estado (Test Specification, AC-07)
- **Spec reference:** AC-07, EDGE-02
- **Plan mode:** COMPLETO
- **Suggested owner:** delivery-build

## Description
El plan mapea AC-07 a "spec detalle por estado". Hay pruebas para Borrador, En preparacion y En refrigeracion, pero el estado "Listo para empacar" solo se comprueba tras liberar (que `release` desaparezca), sin una prueba de detalle que verifique que no hay ninguna accion de produccion (editar, iniciar, registrar, liberar).

En `test_missing_lot_does_not_break_the_list` (backend) la comparacion `(lot['code'], lot['status'], lot['available_quantity'])` contra `(lot['code'], None, None)` compara el codigo consigo mismo; no verifica que se conserve el codigo del lote.

## Expected
Una prueba por estado para AC-07, y aserciones que puedan fallar.

## Actual
Cobertura parcial; el comportamiento real es correcto segun la plantilla (inspeccion de codigo), solo la prueba es debil.

## Evidence
`frontend/panel_admin/src/app/features/production/pages/order-pages.spec.ts` (lineas ~282-296); `backend/modules/production/tests/test_order_api.py` (`test_missing_lot_does_not_break_the_list`).
