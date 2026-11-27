# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-09: Prueba dependiente de la hora del día tras el fix de REV-08

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v3)
**Spec reference:** AC-03 (precarga de fecha clínica)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tras corregir REV-08, `clinical_date()` devuelve el día de La Paz (`America/La_Paz`). La prueba existente `test_odontogram_from_encounter_preloads_context_and_is_unique` sigue comparando contra `timezone.localdate()` (día en `settings.TIME_ZONE`), que no es la misma zona.

## Expected behavior
La prueba debe ser determinista a cualquier hora y con cualquier `TIME_ZONE`, comparando contra el día de La Paz (p. ej. `timezone.now().astimezone(ZoneInfo('America/La_Paz')).date()`), igual que hace la prueba nueva de REV-08.

## Actual behavior
Con `TIME_ZONE=UTC` (valor de `.env.example`) la prueba falla cada día entre las 00:00 y las 04:00 UTC (20:00-24:00 en La Paz), porque el día UTC ya es D+1 y la API devuelve D. Reproducido con `TIME_ZONE=Asia/Tokyo`: `AssertionError: '2026-11-27' != '2026-11-28'`. Pasa en la suite completa (2630 OK) solo porque la ejecución cayó fuera de esa ventana; es un falso rojo intermitente en CI. No es un defecto del código de producción.

## Evidence
- `backend/modules/dentistry/tests/test_encounter_api.py:231` (`timezone.localdate()`).
- `backend/modules/dentistry/application/encounters.py:27-29` (`clinical_date` en `ZONE`).
- Reproducción: `TIME_ZONE=Asia/Tokyo manage.py test modules.dentistry.tests.test_encounter_api.EncounterApiTests.test_odontogram_from_encounter_preloads_context_and_is_unique` falla; con `UTC` y `America/La_Paz` pasa en el horario de la revisión.
- Otros usos de `timezone.localdate()` en tests de dentistry (líneas 94, 344 y `test_odontogram_api.py:36,261`) no dependen de `clinical_date()` de la atención, salvo revisar la línea 94 (listado «hoy» en zona de Agenda).
