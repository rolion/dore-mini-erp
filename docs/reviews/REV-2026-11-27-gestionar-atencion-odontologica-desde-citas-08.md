# REV-2026-11-27-gestionar-atencion-odontologica-desde-citas-08: La fecha clínica del odontograma precargado usa TIME_ZONE y el resto de la atención usa America/La_Paz

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-27-gestionar-atencion-odontologica-desde-citas.md (v3)
**Spec reference:** AC-03 (precarga de fecha), fix de zona horaria (horas en la zona de Agenda)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tras el fix de zona horaria, `local()` y el «hoy» del listado usan `ZoneInfo('America/La_Paz')` (zona de Agenda), pero `clinical_date()` (fecha precargada del odontograma creado desde la atención) usa `timezone.localtime(...)`, es decir `settings.TIME_ZONE` (por defecto y en `.env.example`: `UTC`). Además `EvaluationCommands._today()` valida con `timezone.localdate()` (también `TIME_ZONE`).

## Expected behavior
La fecha clínica precargada coincide con el día que el usuario ve en la atención («Inicio real»), es decir el día local de La Paz.

## Actual behavior
Con `TIME_ZONE=UTC`, una atención iniciada entre las 20:00 y las 24:00 (hora de La Paz) muestra «Inicio real» el día D pero el odontograma se precarga con fecha clínica D+1 (futura para el usuario). No hay pérdida de datos ni error de validación (la validación usa la misma zona UTC), pero la fecha mostrada en el odontograma no coincide con la de la atención. Con `TIME_ZONE=America/La_Paz` no ocurre. Sin prueba que cubra la zona.

## Evidence
- `backend/modules/dentistry/application/encounters.py:20,23-28` (`ZONE` para `local()`, `timezone.localtime` en `clinical_date`).
- `backend/modules/dentistry/application/evaluations.py:17-18` (`_today` con `timezone.localdate()`).
- `backend/.env.example:7` (`TIME_ZONE=UTC`); `backend/config/settings/base.py:79`.
- `backend/modules/dentistry/tests/test_encounter_api.py:98` (solo prueba la zona de las horas devueltas, no la fecha clínica).

## Resolución
`clinical_date()` convierte `started_at` a America/La_Paz (misma zona que Agenda). Prueba `test_odontogram_clinical_date_uses_the_agenda_time_zone` (falla sin el cambio con `TIME_ZONE=UTC`, pasa con él). Resuelto por el autor; pendiente de confirmación en una nueva pasada del Quality Gate.

Confirmado en la 3.ª pasada (HEAD 45b2afe8): `clinical_date()` convierte a America/La_Paz; la prueba nueva pasa con `TIME_ZONE=UTC` y con `TIME_ZONE=America/La_Paz`. `EvaluationCommands._today()` (`timezone.localdate()`, TIME_ZONE) sigue siendo >= al día de La Paz mientras TIME_ZONE sea UTC o más al este, por lo que la validación «no futura» no rechaza la fecha precargada.
