# REV-2026-10-28-registrar-existencias-iniciales-08: Existencias se lista ordenada por UUID del producto, no por nombre
**Status:** Open (aceptado como limitación conocida; no bloquea)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-27-registrar-existencias-iniciales.md (v2)
**Spec reference:** API-02 («orden por producto»), UI-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`DjangoStockMovementRepository.list_balances` ordena por `warehouse__name, product_id`. `product_id` es un UUID aleatorio, así que dentro de cada almacén los productos salen en un orden sin significado para la persona (ni alfabético ni por antigüedad), y la paginación (20 por página) no ayuda a ubicarlos: la pantalla no tiene búsqueda (fuera de alcance). El nombre vive en `catalog`, por eso no se ordena en SQL, pero eso no se declaró como desviación en el TASK v2 («Desviaciones nuevas: ninguna conocida»; la desviación 1 de v1 hablaba de «almacén y última actualización», que tampoco es lo implementado).

## Expected behavior
Orden estable y legible por producto (nombre) dentro de cada almacén, o, si no es viable sin cruzar módulos, una desviación declarada en el PLAN/TASK con una alternativa significativa (p. ej. orden por última fecha de movimiento) y su test.

## Actual behavior
Con productos creados en el orden Zeta, Alfa, Medio, Beta y aperturas de Alfa, Medio y Beta en el mismo almacén, `GET /api/stock/` devuelve Beta, Alfa, Medio. El orden depende del UUID. Ningún test fija el orden.

## Evidence
Sonda temporal (borrada) con `StockApiTestCase`:
```
ORDER ['Beta', 'Alfa', 'Medio']
ORDER2 [('Almacén principal', 'Beta'), ('Almacén principal', 'Alfa'), ('Almacén principal', 'Medio'), ('Sucursal', 'Zeta')]
```
Código: backend/modules/inventory/infrastructure/django/movement_repository.py:185-186 (`.order_by('warehouse__name', 'product_id')`).

## Decisión
Se acepta: ordenar por nombre exige unir datos de Catálogo en la consulta agrupada del libro (acoplamiento entre módulos). Existencias ordena por almacén y producto (UUID); se documenta en el ADR (Consecuencias) y en `## Known limitations` del PR. Una historia de consulta de existencias puede resolverlo con una búsqueda por nombre vía fachada.
