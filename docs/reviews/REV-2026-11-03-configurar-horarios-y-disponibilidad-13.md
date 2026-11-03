# Botones de enlace ilegibles en tema oscuro

**Status:** Open
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md (v1)
**Spec reference:** AC-04 / design-system §8 (tema oscuro)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Evidence

En tema oscuro, los `btn-link` de Agenda («Editar turno», «Cancelar», «Quitar pausa») tienen color `rgb(37,37,37)` sobre `rgb(22,25,42)` y `rgb(15,17,29)` (contraste aproximado 1,2:1). El borde de los diálogos conserva `rgb(222,226,230)` porque `.border` pisa la regla `:host-context(.dark)`. La alerta «Cambios guardados.» tiene texto gris sobre verde de bajo contraste. Medido con `getComputedStyle` en `/pocketbiz/agenda/configuracion/horarios` con `body.dark` (cuarto Quality Gate, 968d912).

No bloquea el PASS (no es Critical ni High); se registra como limitación conocida.

Corrección implementada (REV-13); pendiente de verificación visual en navegador.

Verificado en navegador tras la corrección (contraste en oscuro y estilo del error).
