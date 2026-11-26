# REV-2026-11-26-registrar-produccion-refrigeracion-02: Cobertura de pruebas incompleta de INV-02, EDGE-03..05 y rama sin costo de AC-05

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-produccion-refrigeracion.md
**Spec reference:** INV-02, EDGE-03, EDGE-04, EDGE-05, AC-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
No hay prueba de: cantidad fraccionaria en consumo/elaborada para unidad entera (INV-02), concurrencia real de dos envios (EDGE-03; solo hay doble llamada secuencial), almacen desactivado (EDGE-04), ingrediente que no controla stock (EDGE-05), ni Costeo habilitado pero sin promedio de algun ingrediente (CostUnavailable -> costo vacio). Ademas la fraccion la rechaza Inventario como non_field_errors, no como error por linea.

## Expected
Pruebas que respalden cada AC/INV/EDGE del plan (seccion Test Specification).

## Actual
Los tests de refrigeracion en test_order_api.py no cubren esos casos (test_refrigerate_validates_input no incluye fracciones).

## Evidence
grep allows_fractions en modules/production/tests: solo test_api.py:84 (recetas).

## Resolución
Pruebas agregadas en `test_order_api.py`: fracciones en unidad entera (salida y consumo, con error por línea), ingrediente sin control de stock por línea (EDGE-05), almacén desactivado (EDGE-04: Inventario lo rechaza sin cambios; supuesto S5 y EDGE-04 del plan ajustados), Costeo habilitado sin promedio (costo vacío) y concurrencia real de dos envíos (EDGE-03, `OrderRefrigerateConcurrencyTests`). El adaptador `InventoryStock._check_lines` devuelve ahora esos errores por línea en lugar de `non_field_errors`.
