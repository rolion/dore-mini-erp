# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-06: El diálogo de pago no cumple parte del DDR (botón con faltantes conocidos, enlace en la vista previa, estado de error) y deja código muerto

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v2)
**Spec reference:** UI-04, DDR dialogo-de-pago-asiento-previsto-y-vinculo (Pantallas 1 y «Comportamiento por privilegio/estado»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1. El DDR dice que Registrar «sigue habilitado solo si no hay faltantes que el servidor ya conoce»; `canSubmit` solo mira monto/método/fecha y no considera `preview.issues`. Se puede enviar con faltantes ya mostrados (el servidor igual rechaza con 409, así que no hay riesgo de datos).
2. Los `issues` de la vista previa se listan sin el enlace a Compras › Asientos automáticos (solo la alerta del 409 de alta lo tiene).
3. Estado de error de la vista previa: `catchError(() => of(null))` hace que un fallo de red/500/400 deje el bloque vacío, sin mensaje (el DDR lista cargando/éxito/error). `preview-loading` no usa `role="status"`/`aria-live`, por lo que la actualización no se anuncia.
4. `readonly sideLabels = { DEBIT: () => tr(...), CREDIT: () => tr(...) }` en `payment-dialog.component.ts` no se usa en ningún lugar (código muerto).

## Expected behavior
Comportamiento del DDR, estado de error visible y accesible, sin código sin uso.

## Actual behavior
Ver Description.

## Evidence
```
$ grep -rn "sideLabels" frontend/panel_admin/src/app
payment-dialog.component.ts:38:  readonly sideLabels = { DEBIT: () => tr('ACCOUNTING.POSTING.DEBIT'), CREDIT: () => tr('ACCOUNTING.POSTING.CREDIT') };
$ payment-dialog.component.html:  [disabled]="submitting || (touched && !canSubmit)"   (sin referencia a preview.issues)
$ payment-dialog.component.ts:  .pipe(catchError(() => of(null)))
```

## Resolution
Resuelto: Registrar se deshabilita con faltantes ya conocidos de la vista previa; los avisos de la vista previa llevan el enlace a Compras › Asientos automáticos; un fallo de la vista previa muestra un mensaje (no impide pagar); el aviso de carga usa `role="status"` y `aria-live`; se eliminó `sideLabels`. Pruebas nuevas en el spec del diálogo.
