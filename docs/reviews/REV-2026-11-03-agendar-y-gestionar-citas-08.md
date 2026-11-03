# REV-2026-11-03-agendar-y-gestionar-citas-08: Listado e historial no se apilan en móvil (columnas clave fuera de pantalla)

**Status:** Open
**Severity:** Medium
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** DDR Detalle («Historial (tabla apilada ...)»); design-system.md §5 (tabla apilada en móvil) y §8 («Se ve bien en móvil ≈390 px»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El listado de citas y la tabla de historial del detalle usan `table-responsive` (scroll horizontal) en lugar de la tabla apilada de `_inventory-table.scss` que exige el sistema de diseño. Además, en la cabecera de la tarjeta los botones «Listado», «Calendario» y «+ Nueva cita» se deforman (píldoras altas con el texto partido en tres líneas) a 390 px.

## Expected behavior
A ≈390 px cada cita/evento se ve completo (cliente, servicio, profesional, estado; autor, motivo y horario anterior) sin scroll horizontal, como en el resto de listados del producto.

## Actual behavior
A 390 px, en el listado solo se ven Inicio, Fin y parte de Cliente; Servicio, Profesional y Estado quedan fuera de pantalla. En el historial solo se ven Evento y Fecha; Autor, Motivo y Horario anterior (datos centrales de AC-05) requieren scroll horizontal. En escritorio (1440 px) y tema oscuro el aspecto es correcto.

## Evidence
Revisión visual en el navegador integrado (backend con base temporal `test_doredb`, ya eliminada): capturas de /pocketbiz/agenda/citas y /pocketbiz/agenda/citas/:id a 390 px. appointment-list.component.html y appointment-detail.component.html: `<div class="table-responsive">` sin `_inventory-table`.
