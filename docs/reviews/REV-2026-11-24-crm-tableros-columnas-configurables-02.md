# REV-2026-11-24-crm-tableros-columnas-configurables-02: La tabla de etapas desborda en móvil y deja «Acciones» fuera de pantalla

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-crm-tableros-columnas-configurables.md (v1)
**Spec reference:** UI-02, UI-05; DDR «Editor de etapas» (tabla apilada en móvil, accesible por teclado y en móvil); design-system.md §5 «Configuración con listados» (tabla apilada, botones de 44 px bajo `lg`)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Revisión visual en el navegador integrado (backend en 127.0.0.1:8100 con BD de pruebas, frontend en `ng serve`, usuario de prueba) a 375×812.

## Expected behavior
Bajo 768 px cada etapa se apila como bloque y Renombrar/Archivar quedan visibles sin scroll horizontal, con botones táctiles de ≥44 px, como en `inventory-table` (`features/inventory/components/_inventory-table.scss`).

## Actual behavior
`crm-board.component.html` usa un `<table class="table">` normal dentro de `.table-responsive`: el contenedor mide 265 px y el contenido 800 px, así que «Nombre» se corta y «Acciones» (Renombrar en x=690, Archivar en x=777) solo se alcanza con scroll horizontal. Los botones miden 27–29 px de alto. En escritorio (1440) y en tema oscuro la pantalla se ve correcta y todas las acciones funcionan (reordenar con recarga, agregar, duplicado, archivar).

## Evidence
`document.querySelector('.table-responsive')` → `{client: 265, scroll: 800}`; botones `move-up` 27×29, `edit-stage` 83×29 con `left: 690`, `archive-stage` 68×29 con `left: 777`. Captura a 375 px: columna «Nombre» truncada («Contact», «Propues»), sin acciones visibles.

## Resolution
Tabla apilada bajo 768 px (`crm-board.component.scss`, `data-label` en cada celda, `<caption>` accesible) y botones de 44 px. Verificado en navegador a 375 px: `{client: 265, scroll: 265}`, «Renombrar» y «Archivar» visibles dentro del contenedor, botones de 44 px de alto.
