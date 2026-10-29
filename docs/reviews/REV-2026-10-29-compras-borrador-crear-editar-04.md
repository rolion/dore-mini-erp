# REV-2026-10-29-compras-borrador-crear-editar-04: detalles menores del formulario y detalle de compra (NG8102, fracciones al editar, falso «sin proveedores», redirección ante cualquier error)

**Status:** Fixed en parte: se corrigió el aviso NG8102; el resto queda como limitación conocida (Low)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-29-compras-borrador-crear-editar.md (v1)
**Spec reference:** AC-14, AC-15, AC-17, AC-18
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
1. `ng build` emite NG8102 en `PurchaseFormComponent`: `[items]="lineOptions[i] ?? []"` (el tipo `LineProduct[][]` no admite `undefined`).
2. En modo edición, `fill()` crea cada línea con `allowsFractions: true`; la validación local «cantidad entera si la unidad no admite fracciones» (AC-15) no aplica a las líneas precargadas hasta cambiar de producto. El servidor sí la exige (el error llega por línea), pero la UI no lo anticipa.
3. `searchSuppliers` convierte cualquier error de red en lista vacía y `watchSuppliers` marca `noSuppliers = true`: ante una caída del servidor se muestra «No hay proveedores activos.».
4. En `PurchaseDetailComponent`, cualquier error (incluida una caída de red) redirige a la lista; AC-17 lo pide solo para «inexistente».

## Expected behavior
Sin advertencias de compilación nuevas; validación coherente con la unidad también al editar; el aviso de «sin proveedores» solo cuando la API responde una lista vacía; redirección solo en 404.

## Actual behavior
Ver Description.

## Evidence
`npx ng build`: `NG8102: The left side of this nullish coalescing operation does not include 'null' or 'undefined' in its type... Warning occurs in the template of component PurchaseFormComponent.` Código: `purchase-form.component.ts` (`fill`: `allowsFractions: true`; `searchSuppliers`: `catchError(() => of([]))` + `noSuppliers = options.length === 0`), `purchase-detail.component.ts` (rama `error`).
