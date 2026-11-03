# El diálogo de turno desborda en móvil

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** AC-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

En la revisión visual local en tema claro, el diálogo Nuevo turno mostró el borde derecho recortado a 390 px y ocupó casi todo el ancho a 1440 px. El foco entró en Día al abrirlo con teclado. La vista semanal mostró el estado vacío esperado.

El diálogo debe ajustarse al ancho disponible en móvil y mantener un ancho legible en escritorio. Quedan pendientes el tema oscuro y el recorrido de guardado y errores con teclado.

Implementación: ambos diálogos se centran y limitan su ancho y altura al espacio disponible. La compilación Angular pasó. Pendiente repetir la comprobación visual en navegador.
