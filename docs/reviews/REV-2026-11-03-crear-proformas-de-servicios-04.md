# REV-2026-11-03-crear-proformas-de-servicios-04: Un borrador con cliente ahora inactivo se puede seguir editando sin revalidar al cliente

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v1)
**Spec reference:** INV-06 («Cliente activo al crear/editar borrador»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
`ProformaService._customer` devuelve el nombre guardado sin comprobar `active` cuando el `customer_id` no cambia. Así se conserva el borrador de un cliente desactivado, pero INV-06 dice que el cliente debe estar activo al editar.

## Expected behavior
O bien INV-06 se aplica literalmente (editar un borrador de un cliente inactivo da 400), o bien el plan documenta la excepción «mismo cliente conservado».

## Actual behavior
El PUT con el mismo cliente, ya inactivo, se acepta. El snapshot `customer_name` tampoco se refresca aunque el cliente cambie de nombre. Ninguna prueba cubre el caso. Es una desviación pequeña, razonable como producto, pero no está en la Specification.

## Evidence
`proformas.py`: `if current is not None and current.customer_id == customer_id: return current.customer_name` antes de `if not customer.active`.
