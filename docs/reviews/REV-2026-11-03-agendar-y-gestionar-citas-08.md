# REV-2026-11-03-agendar-y-gestionar-citas-08: Listado e historial no se apilan en móvil (columnas clave fuera de pantalla)

**Status:** Verified
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

## Resolución
El listado y el historial usan `inventory-table` (apilado a <768 px, con `data-label` por celda; se importa el parcial de Inventario) y los botones de la cabecera son `text-nowrap` con `flex-wrap`. Falta reverificarlo visualmente a 390 px en el navegador.

## Verificación (Quality Gate 3)
Verificado en gate 3 en el navegador integrado (backend con base temporal `test_doredb`, ya eliminada; frontend `npm start`). A 390 px el listado y el historial se apilan: `td` computa `display: block`, `thead` queda `position: absolute` (oculto solo visualmente), `td::before` muestra la etiqueta (`"Inicio: "`), `scrollWidth` = `clientWidth` = 390 (sin scroll horizontal) y las tablas miden 280 px. Cada celda lleva `data-label`; las tablas llevan `inventory-table` y los dos SCSS hacen `@use '../../inventory/components/inventory-table'`. El encapsulamiento de Angular no afecta: las tablas están en la plantilla del propio componente, así que los selectores reciben el atributo `_ngcontent`. Botones de cabecera: 30 px de alto, una línea (82/105/117 px de ancho), sin deformarse; en detalle Confirmar/Reprogramar/Cancelar/Volver a 36 px. A 1440 px `td` = `table-cell`, `thead` estático, sin etiquetas, tabla normal de 1076 px. Tema oscuro correcto a 390 px en listado y detalle (historial con Autor, Motivo y Horario anterior visibles).
