# REV-2026-11-16-configurar-asientos-automaticos-modulo-11: Un selector cuya cuenta guardada ya no es elegible queda en blanco, sin nombrar la cuenta

**Status:** Resolved
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v3)
**Spec reference:** AC-07, AC-12, UI-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Tercera pasada, `/es/pocketbiz/expenses/settings` con Contabilidad habilitada. La categoría «Alquileres» tenía asignada «Gasto luz»; se deshabilitó esa cuenta por la API y se recargó la página.

## Expected behavior
La fila deja ver qué cuenta tiene guardada (p. ej. «610001 · Gasto luz · no válida») o, como mínimo, un valor reconocible, además del aviso.

## Actual behavior
El `select` queda sin opción seleccionada (`selectedIndex = -1`, texto vacío) porque las opciones solo incluyen cuentas activas y el control conserva el id de la cuenta deshabilitada. Debajo sí aparece el aviso «La cuenta «Gasto luz» está deshabilitada; elija otra o actívela en Cuentas.» y el aviso global lista el mismo faltante, y «Guardar» queda deshabilitado hasta elegir otra cuenta, así que la persona puede corregirlo; pero el control en blanco no dice cuál era la cuenta (solo el mensaje lo hace). Mismo comportamiento para roles y métodos (misma ruta de código).

## Evidence
Captura a 1440 px: selector vacío con la etiqueta amarilla bajo él; por JS `selectedIndex` = -1 y `value` = "" en esa fila.

## Resolution
El selector incluye la cuenta guardada que ya no es elegible, marcada «· ya no es válida» (`staleOption`), en vez de quedar en blanco. Prueba añadida.
