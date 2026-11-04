# REV-2026-11-04-cobrar-servicios-anticipos-pagos-parciales-02: Tras recargar por conflicto, las imputaciones del formulario quedan desalineadas con las líneas cobrables

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-cobrar-servicios-anticipos-pagos-parciales.md (v1)
**Spec reference:** AC-11 (la UI conserva datos ante fallos); UI-03
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`CommitmentDetailComponent` enlaza cada control del FormArray `allocations` con `payableLines[i]` solo por índice. En `confirm()`, ante un 409 se llama a `load()`, que reemplaza `commitment` y por tanto `payableLines` (una línea puede dejar de ser cobrable), pero el FormArray no se reconstruye.

## Expected behavior
Las imputaciones tecleadas siguen ligadas a su tratamiento tras recargar, o se invalida/reconstruye la distribución y se avisa.

## Actual behavior
Si `payableLines` cambia de longitud/orden, el importe de una fila pasa a otro tratamiento al volver a «Revisar»; si el FormArray queda más largo que `payableLines`, `confirm()` evalúa `lines[i].line_id` sobre `undefined` (TypeError) antes de suscribirse y `saving` queda en `true` (botón bloqueado). El servidor nunca sobrepaga (valida saldo por línea) y el resumen muestra las descripciones nuevas, por eso es Low.

## Evidence
commitment-detail.component.ts: `allocations.controls.map((group, i) => ({ line_id: lines[i].line_id, ...}))` dentro de `confirm()` tras `this.saving = true`; `error: ... if (failure.conflict) this.load();` sin llamar a `open()`/reconstruir. Hallazgo por lectura de código; no reproducido (sin backend).
