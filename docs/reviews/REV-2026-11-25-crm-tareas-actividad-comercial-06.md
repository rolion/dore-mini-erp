# REV-2026-11-25-crm-tareas-actividad-comercial-06: Insignias de estado no siguen el mapa del sistema de diseno ni el DDR

**Status:** Resolved (corregido tras el Quality Gate)
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-25-crm-tareas-actividad-comercial.md (v1)
**Spec reference:** UI-01, DDR (Componentes/patrones elegidos), design-system.md seccion 3 Badges de estado
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El badge «Cancelada» usa col-blue y las insignias de resultado del historial usan siempre col-green.

## Expected behavior
DDR: Pendiente = advertencia, Vencida = peligro, Hecha = exito, Cancelada = secundario. design-system §3: Cancelado = col-red, Pedido nuevo = col-blue; el verde indica estado positivo.

## Actual behavior
Cancelada se pinta azul (color de «nuevo»); en el historial, resultados negativos («No interesado», «Sin respuesta») salen en verde, y el canal en azul. El texto acompana siempre, por lo que no es solo-color.

## Evidence
crm-task-list.component.html: [class.col-orange]="row.status === 'pending'" [class.col-green]="row.status === 'done'" [class.col-blue]="row.status === 'cancelled'"; activity-dialog.component.html: <span class="badge-outline col-green"> para cualquier item.outcome.
