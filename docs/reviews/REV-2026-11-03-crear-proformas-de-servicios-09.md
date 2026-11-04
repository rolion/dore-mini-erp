# REV-2026-11-03-crear-proformas-de-servicios-09: Un borrador con cliente inactivo se puede presentar sin pasar por el guardado

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v2)
**Spec reference:** INV-03 ("`present()` exige ≥ 1 línea válida y cliente"), INV-06 (cliente activo al crear y cada vez que se guarda)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
INV-06 (v2) exige cliente activo al guardar, pero ni `present` ni `new_version` lo revalidan. «Nueva versión» copia el borrador sin consultar al cliente, por lo que si el cliente se desactiva entre medias, el borrador se puede presentar tal cual (sin guardar), mientras que guardar ese mismo borrador daría 400. Es una asimetría de la regla, no una vulnerabilidad.

## Expected behavior
Decisión explícita en la especificación: o bien «presentar» también exige cliente activo (coherente con INV-06), o bien se documenta que presentar solo exige ≥ 1 línea y el cliente existente.

## Actual behavior
`ProformaService.present` (application/proformas.py) solo llama a `proforma.present()` (estado y ≥ 1 línea); `_customer()` se invoca únicamente en `create` y `update`. No hay prueba que fije el comportamiento.

## Evidence
`backend/modules/quotations/application/proformas.py`: `present()` y `new_version()` no usan `self.customers`. Cliente inactivo + borrador existente: PUT → 400 (`test_editing_a_draft_requires_an_active_customer`), POST present → 200.
