# REV-2026-10-08-clientes-mvp-01: AC-03 contradice la regla de normalización; `591 76543210` se guarda como `+59159176543210`

**Status:** Closed (verificado en re-review sobre 58e1784)
**Severity:** High
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-08-clientes-mvp.md (v1)
**Spec reference:** AC-03, EDGE-02, INV-03, regla de normalización (`normalize_phone`); REQ-CUS-006
**Plan mode:** COMPLETO
**Suggested owner:** delivery-plan

## Description
El AC-03 afirma que `(591) 76543210` se normaliza a `+59176543210`, pero la regla de normalización del mismo plan (y de `ADR-clientes-mvp-modelo-dominio`) dice que un número "solo de dígitos" recibe `+` y el código de país por defecto. `(591) 76543210` queda, tras quitar separadores, como `59176543210` (solo dígitos), por lo que la regla produce `+59159176543210`. El AC es inconsistente con la regla y con el comportamiento implementado; el implementador lo detectó y lo registró como desviación, pero la Specification sigue marcada READY con el ejemplo erróneo.

Además hay un impacto de negocio: el formato "código de país sin `+`" (`591 7xxxxxxx`, muy cercano al placeholder `+591 7xxxxxxx` del propio formulario) es una entrada plausible; con la regla actual se guarda un número corrupto (`+59159176543210`) y no se detecta como duplicado de `76543210` / `+59176543210` (EDGE-02, REQ-CUS-006). Decidir si ese caso debe tratarse como ya prefijado (p. ej. dígitos que empiezan con el código de país y cuya longitud total sea válida) es una decisión de comportamiento de negocio, no de código.

## Expected behavior
AC-03: `(591) 76543210` y `00591 76543210` → `+59176543210`. EDGE-02: `76543210` y `+591 76543210` se detectan como duplicados.

## Actual behavior
`00591 76543210` → `+59176543210` (correcto). `(591) 76543210` → `+59159176543210` (incumple el AC tal como está escrito). La implementación sigue la regla escrita, no el ejemplo.

## Evidence
Humo contra PostgreSQL (servidor `runserver` real, base desechable):
```
POST /api/customers/ {"name":"  Ana  ","phone":"(591) 76543210"}
-> 201 {"name":"Ana","phone":"+59159176543210", ...}
POST /api/customers/ {"name":"Beto","phone":"76543210"}
-> 201 {"phone":"+59176543210", ...}   (no hubo 409: no se detectó como duplicado de Ana)
POST /api/customers/ {"name":"Caro","phone":"00591 76543211"}
-> 201 {"phone":"+59176543211", ...}
```
`TASK-clientes-mvp.md` § Implementación, "Desviaciones respecto al plan", ya reconoce el desajuste y que los tests usan `+(591) 76543210`.

## Required action
`delivery-plan` (v2): (1) corregir el texto de AC-03 y/o (2) decidir con el usuario si los dígitos que ya empiezan con el código de país (sin `+`) se tratan como prefijados; si cambia la regla, actualizar `ADR-clientes-mvp-modelo-dominio` (vía `delivery-architect` si corresponde), `normalize_phone`, su tabla de tests y EDGE-02. Aprobación explícita del usuario porque cambia comportamiento de negocio.
