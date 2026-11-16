# REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-01: El tipo de dinero no se puede quitar y bloquea reclasificar cuentas anteriores

**Status:** Closed
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-administrar-cuentas-codigo-clasificacion-estado.md (v1)
**Spec reference:** INV-04, UI-02, EDGE «Cambiar la clasificación de Activo a otra con `kind` presente: 400»
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`UpdateAccount` trata `kind: null` como «sin cambio», y el diálogo no envía `kind` cuando se elige una clasificación distinta de Activo (o «No es cuenta de dinero»). Una cuenta que ya tiene `kind` no puede reclasificarse a otra clase ni dejar de ser de dinero.

## Expected behavior
Poder quitar el tipo de dinero (o, al menos, ver el motivo del rechazo junto al campo que lo causa).

## Actual behavior
El servidor responde 400 en `kind`. Como el selector de tipo está oculto fuera de Activo, el error no se muestra en ningún sitio y la persona no ve explicación. Afecta a las cuentas anteriores, que tenían `kind` obligatorio: completarlas con Activo funciona; con otra clasificación queda bloqueado.

## Evidence
`application/use_cases.py` (`if kind is not None`), `account-dialog.component.ts` (spread condicionado de `kind`), y la prueba `test_change_class_without_entries_and_kind_consistency`, que documenta el 400. Informe del Quality Gate, hallazgo 1.

## Resolution
Corregido en el commit `6b47154`: `kind: null` explícito en PATCH quita el tipo (sentinela `UNSET` en `UpdateAccount`, `Account.clear_kind`); el diálogo envía `kind: null` cuando la cuenta pierde su tipo y muestra el error de `kind` junto a la clasificación. Re-revisión independiente: PASS (backend 1795 OK, frontend 1471 OK).

## Suggested fix
Aceptar `kind: null` explícito en PATCH como «quitar el tipo» (distinguiendo ausente de nulo en el serializer), o mostrar el error de `kind` junto al selector de clasificación.
