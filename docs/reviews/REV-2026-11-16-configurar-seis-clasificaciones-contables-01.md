# REV-2026-11-16-configurar-seis-clasificaciones-contables-01: Una cuenta clasificada no puede volver a «sin clasificación»

**Status:** Open
**Severity:** Medium
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-seis-clasificaciones-contables.md (v1)
**Spec reference:** UI-02, API-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start (decidir en CONT-09; no bloquea este PR)

## Description
En el diálogo de cuenta, elegir «Sin clasificación» en una cuenta que ya tiene clasificación omite `accountClass` del cuerpo; además el API trata `account_class: null` como «sin cambio» (`if account_class is not None`).

## Expected behavior
O la opción vacía no se ofrece al editar una cuenta ya clasificada, o limpiar es una operación explícita.

## Actual behavior
La persona ve el selector vacío, guarda con éxito y la clasificación sigue puesta.

## Evidence
`account-dialog.component.ts` (`value.accountClass ? {...input, accountClass} : input`) y `application/use_cases.py` (`_classify` solo si `account_class is not None`). Sin prueba de PATCH con `null`. La Specification no exige poder limpiarla; CONT-09 hará la clasificación obligatoria, lo que resuelve el caso.
