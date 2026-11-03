# REV-2026-11-03-crear-proformas-de-servicios-02: `id` de línea repetido en el PUT provoca un 500

**Status:** Resolved (pendiente de re-verificación con PostgreSQL)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-crear-proformas-de-servicios.md (v1)
**Spec reference:** API-02 (líneas con `id` conservan snapshot); AC-02 (errores por línea, 400)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
En `ProformaService._lines` (`backend/modules/quotations/application/proformas.py`), cada entrada con `id` busca la línea congelada en `existing` y reutiliza su `id`. Si el cuerpo trae dos entradas con el mismo `id` existente, el resultado tiene dos `ProformaLine` con la misma clave primaria. `save()` luego ejecuta `bulk_create` con ese duplicado.

## Expected behavior
Respuesta 400 con error por línea («línea repetida»). El PUT debe tratarse como entrada inválida, no como fallo del servidor.

## Actual behavior
Por lectura de código (la prueba con BD no se pudo ejecutar): `bulk_create` lanza `IntegrityError` por clave primaria duplicada y la respuesta es 500. `transaction.atomic` revierte, así que no queda corrupción de datos. Requiere una petición manipulada. No hay validación de unicidad de `id` en el serializer ni en el dominio.

## Evidence
`proformas.py`: `frozen = existing.get(item.id) if item.id else None` seguido de `result.append(ProformaLine(frozen.id, ...))` sin control de repetidos. `ProformaLineModel.id` es `primary_key=True`. No existe prueba para este caso.
