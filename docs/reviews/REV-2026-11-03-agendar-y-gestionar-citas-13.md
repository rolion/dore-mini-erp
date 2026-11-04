# REV-2026-11-03-agendar-y-gestionar-citas-13: Los mensajes de error del servidor de Citas salen siempre en español, también con la interfaz en inglés o portugués

**Status:** Verified
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-03-agendar-y-gestionar-citas.md (v1)
**Spec reference:** CLAUDE.md «Sin texto visible hardcodeado» e idiomas es/en/pt (posterior al plan v1); AC-09
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Las pantallas de Citas ya traducen todo su texto propio (128 claves `AGENDA.CITAS.*`), pero dos rutas muestran texto del servidor tal cual: el `detail` de un 409 (conflicto o transición inválida) y los mensajes por campo de un 400 (`toFailure` en `appointments-api.service.ts` usa `firstMessage(body[...])`). Esos mensajes se definen en español en el dominio y la aplicación de Agenda (`AppointmentRuleError('El motivo es obligatorio.', ...)`, `'Selecciona un cliente activo de tu empresa.'`, etc.).

## Expected behavior
Con la interfaz en inglés o portugués, el usuario no ve frases en español en los avisos de error o, si se decide que los mensajes del servidor quedan en español por ahora, la decisión consta (en el plan, el ADR o CLAUDE.md) como excepción conocida.

## Actual behavior
Por revisión de código: con `/en` o `/pt`, un conflicto de horario, un motivo vacío o un cliente inválido muestran el texto en español del servidor. El único texto traducible es el de respaldo (`ERR_HORARIO`, `ERR_REVISA`), que solo se usa si el servidor no envía mensaje. No se reprodujo en el navegador (no se forzó un error de validación del servidor en la revisión visual). El plan v1 es anterior a los idiomas, por lo que no es un incumplimiento del plan; tampoco hay una regla escrita sobre el idioma de los mensajes del servidor.

## Evidence
`frontend/panel_admin/src/app/features/agenda/services/appointments-api.service.ts`, `toFailure` (409: `firstMessage(body['detail']) || tr('AGENDA.CITAS.ERR_HORARIO')`; 400: `fields[key] = firstMessage(value)`). `backend/modules/agenda/domain/appointment.py:32,34,79` y `backend/modules/agenda/application/appointments.py:84-121` (mensajes en español). Opciones: códigos de error estables en la API con clave de traducción en el frontend, o documentar la excepción.

## Resolución
Los errores del servidor llevan códigos estables (`code` en los 409 y `codes` por campo en los 400) y el cliente los traduce al idioma activo (`AGENDA.CITAS.VAL_*`, es/en/pt); un código desconocido conserva el mensaje del servidor. Pruebas: `test_errors_carry_stable_codes_for_translation` y `appointments-api.service.spec.ts` (es, en, pt).

## Verificación (quinto Quality Gate)
Verificado: `test_errors_carry_stable_codes_for_translation` y la suite completa (1384 pruebas OK); 17 claves `AGENDA.CITAS.VAL_*` presentes en es/en/pt, `i18n:check` (1486 claves, 0 faltantes) y catalogs.spec en verde; `appointments-api.service.spec.ts` cubre es/en/pt y código desconocido. En el navegador (backend temporal): fuera de turno con `/en` mostró «The time is outside the professional's shift…» (formulario y diálogo de reprogramar) y un conflicto con `/pt` mostró «O profissional já tem um agendamento nesse horário.». La clave `codes` no se muestra como campo; 404/403/errores de red ya usaban `tr()`.
