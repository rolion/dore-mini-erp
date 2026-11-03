# REV-2026-11-03-agendar-y-gestionar-citas-01: El profesional no se muestra en listado ni detalle de citas

**Status:** Fixed (pendiente de reverificación en el próximo Quality Gate)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** TASK Interfaz («mostrar cliente, servicio, profesional, inicio/fin, estado»); DDR Detalle (dl con profesional)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
La lista y el detalle de una cita no muestran el profesional. La API solo devuelve professional_id (sin nombre) y las plantillas no lo renderizan.

## Expected behavior
Listado, calendario y detalle muestran el profesional de cada cita (el DDR lo exige en el dl del detalle).

## Actual behavior
Tabla del listado: Inicio, Fin, Cliente, Servicio, Estado, Acciones. Detalle: Servicio, Inicio, Fin, Duración, Notas. Con varios profesionales, en el listado general no se sabe de quién es cada cita.

## Evidence
grep de 'rofesional' en appointment-detail.component.html: sin coincidencias. En appointment-list.component.html solo aparece en los filtros y el selector de calendario (lineas 36, 87-102). backend/modules/agenda/appointments_api.py present(): solo 'professional_id'.

## Resolución
La API devuelve `professional_name` (fachada `personnel.services.professional_names`, consulta por lote en el listado). El listado, el detalle y el diálogo de acciones muestran el profesional. Cubierto por `test_appointments.py` (alta y listado) y `appointment-detail.component.spec.ts`.
