# Brechas en la Test Specification

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** AC-01, AC-02, AC-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

Faltan pruebas de no administrador (403), turno ajeno (404), pausas inválidas, vigencias adyacentes/coincidentes y contiguidad por API, y ausencias de varios días o superpuestas (incluido 09:00–12:00 con ausencia 10:00–11:00 por API). `tests/test_api.py` tiene 3 pruebas.

Origen: tercer Quality Gate independiente sobre `7d521eb`.

Corrección implementada tras el tercer gate; pendiente de verificación en el siguiente Quality Gate.
