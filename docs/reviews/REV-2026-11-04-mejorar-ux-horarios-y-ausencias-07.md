# REV-2026-11-04-mejorar-ux-horarios-y-ausencias-07: Detalles visuales menores en diálogos y tarjeta (revisión en navegador)

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-ux-horarios-y-ausencias.md (v1)
**Spec reference:** DDR-mejorar-ux-horarios-y-ausencias-dialogos-y-semana; design-system.md §7 (accesibilidad mínima)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Observaciones de la revisión visual en el navegador (escritorio 1440 px, oscuro, móvil 390 px). Los puntos 1 y 2 de «Actual behavior» ya se corrigieron en el mismo commit; quedan los 3 restantes, todos de severidad baja y sin bloquear el uso.

## Expected behavior
Objetivos táctiles cómodos en móvil, tarjetas alineadas y etiquetas con espacio suficiente.

## Actual behavior
1. (Corregido) El diálogo de confirmación de borrado se titulaba «Editar ausencia»; ahora «Eliminar ausencia».
2. (Corregido) El enlace «Cerrar» del aviso verde era azul sobre verde, con poco contraste; ahora hereda el color del texto.
3. Los chips de día y los atajos miden unos 28–32 px de alto en móvil (menos de 44 px).
4. En móvil, «Copiar a otros días» baja a su propia línea con sangría respecto a «Editar turno».
5. La etiqueta «Todo el día» queda pegada al interruptor.

## Evidence
Capturas del navegador integrado (escritorio claro y oscuro, móvil) con la rama en `localhost:4201`. Funcionalmente se verificó: alta múltiple (con error de solape que nombra el día y conserva lo escrito), edición de ausencia de día completo, eliminación con confirmación y recuperación de la disponibilidad. Sin desbordamiento horizontal a 390 px (`scrollWidth` = `innerWidth` = 390).
