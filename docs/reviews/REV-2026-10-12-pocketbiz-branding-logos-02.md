# REV-2026-10-12-pocketbiz-branding-logos-02: AC-10 resalta dos ítems de submenú a la vez (coincidencia por prefijo)

**Status:** Resolved (PLAN v4: AC-10 exige ítem único; delivery-engineer implementó `linkActiveOptions`, 2026-10-12). Pendiente de re-review.
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-10-12-pocketbiz-branding-logos.md (v3)
**Spec reference:** AC-10 ("el ítem activo/seleccionado (principal y submenú) tiene fondo `#125AC4`")
**Plan mode:** COMPLETO
**Suggested owner:** delivery-plan

## Description
El estilo `#125AC4` de AC-10 se aplica a `li.active` de `routerLinkActive`, que en `sidebar.component.html:49/59/70` no usa `routerLinkActiveOptions={exact:true}`. Con la ruta `/expenses/categories` quedan "activos" a la vez "Gastos" (`/expenses`, prefijo) y "Categorías". Es un comportamiento preexistente de la plantilla (solo cambiaba el color del texto), pero con AC-10 ahora se ve como dos bloques azules macizos. La Specification no define si debe haber un único ítem seleccionado, por lo que no hay criterio contra el cual declarar el código defectuoso.

## Expected behavior
"El ítem activo/seleccionado" (singular) con fondo `#125AC4`.

## Actual behavior
En `/expenses/categories`, dos ítems de submenú con fondo `rgb(18, 90, 196)` y texto blanco.

## Evidence
Verificado en navegador (build de este PR servido estáticamente, sesión simulada, ruta `#/expenses/categories`):
```
.ml-menu li  -> [ {li:"", bg:"rgba(0,0,0,0)", color:"rgb(0,0,0)"},
                  {li:"active", bg:"rgb(18, 90, 196)", color:"rgb(255,255,255)"},   // Gastos (/expenses)
                  {li:"active", bg:"rgb(18, 90, 196)", color:"rgb(255,255,255)"} ]  // Categorías
```
Acción requerida: decidir en la Specification si AC-10 exige un único ítem (→ `routerLinkActiveOptions` exact en `sidebar.component.html`, archivo hoy fuera del alcance del plan para esa parte) o se acepta el comportamiento actual.
