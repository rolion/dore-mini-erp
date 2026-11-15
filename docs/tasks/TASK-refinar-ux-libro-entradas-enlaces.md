# TASK-refinar-ux-libro-entradas-enlaces: Refinar UX del libro de Entradas (enlace al cobro y legibilidad)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-refinar-ux-libro-entradas-enlaces
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-15 | (nuevo) → INVESTIGATION | Task creado a partir de la crítica de diseño de Contabilidad › Entradas; `main` al día (6b4f7d1) | delivery-start |
| 2026-11-15 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN: solo frontend del módulo `accounting`, sin contrato API ni reglas de dominio nuevas | delivery-start |
| 2026-11-15 | PLANNING → ENGINEERING | Specification READY; el alcance se acotó con criterio propio (ver plan) | delivery-start |

## Investigación

### Requerimiento
La persona, en etapa de refinamiento de UI del módulo Contabilidad, pide: en la tabla de Entradas (ingresos), «el código del cobro podría ser un link al cobro (módulo Cobros)». Desde ahí se abre el detalle con el botón del ojo. Insumo adicional: la crítica de diseño previa de la sesión (enlaces poco visibles, aviso azul dominante, textos auxiliares de bajo contraste, detalle sin salida hacia el origen). **No es una Specification aprobada.**

### Hechos encontrados
- `frontend/panel_admin/src/app/features/accounting/pages/entry-list/entry-list.component.html:150-158` — la columna **Documento** ya es enlace (`sourceLink(row)`, `data-testid="source-link"`); la columna **Comprobante** (`CB-NNNNNN`) es texto plano (`:159-161`).
- `.../accounting/models/entry.ts:122-131` — `sourceLink`: productos → `/pocketbiz/sales/orders/<documentRef>`; servicios → `/pocketbiz/receivables/<kind>/<number>` (parsea `documentRef = kind/number`); `null` si `!sourceAvailable` o no hay `documentRef`.
- `.../accounting/models/entry.ts:92` — `receiptNumber` viene de `source.receipt_number`; solo los cobros de servicios tienen `CB-NNNNNN` (en productos queda vacío → «—»). Ver `TASK-libro-entradas-filtros-totales.md` (Hechos, pago de servicios).
- `frontend/panel_admin/src/app/app.routes.ts:86-95` — Cobros = módulo `receivables`: lista `receivables` y detalle `receivables/:kind/:number`. **No existe una ruta propia por pago**: el comprobante CB aparece solo en la tabla «Pagos» de `receivables/features/pages/commitment-detail.component.html:75-93` (`payment.receipt_number`, `payment.id`).
- `.../entry-detail/entry-detail.component.html:40-55` — el detalle muestra Documento (enlace), Comprobante (texto) y «ID del pago de origen» (UUID crudo en `small.text-muted`); no hay acción hacia el origen salvo el enlace de Documento.
- `.../entry-list/entry-list.component.ts:129,149,153` — los filtros ya viven en la URL (query params) y «Volver» los conserva (DDR vigente). La crítica previa decía lo contrario: **era incorrecto**, no se hace nada.
- `docs/design/design-system.md:193` — el `alert-info` de la plantilla (texto blanco sobre azul claro, ~2,2:1) no cumple AA; el sistema pide migrar al estilo tenue `alert alert-info bg-info-subtle text-info-emphasis border-info-subtle` cuando se toque la pantalla. `entry-list.component.html:23` aún usa `alert-info` plano.
- `docs/design/DDR-libro-entradas-filtros-totales-pantallas-entradas.md:22` — el DDR vigente ya define el enlace al origen solo con `source.available`.
- Pruebas existentes: `entry-list.component.spec.ts:51,111-112` (`context-note`, `source-link`, `source-text`), `entry-detail.component.spec.ts:30-43`.

### Hipótesis / supuestos no confirmados
- «Código del cobro» = `CB-NNNNNN` (columna Comprobante). Podría referirse a `ODO-…` (número de proforma), que ya enlaza; se cubren ambos sin ambigüedad práctica (ver plan).
- Los enlaces se ven negros en la captura: puede ser estilo de `ngx-datatable` sobre `<a>`; **verificar en el navegador** antes de decidir el estilo (la regla del sistema dice que los enlaces van en `primary`).
- El gris de `text-muted` en textos auxiliares y el UUID podrían no llegar a 4,5:1; medir con estilos computados antes de cambiar.
- La cabecera «Monto» parece desalineada respecto de las cifras; confirmar si es defecto real o efecto de la captura.

### Módulos y dependencias relacionadas
`accounting` (frontend) → enlaza a `receivables` y `sales` solo por URL; sin importaciones entre features.

### Implementaciones similares existentes
Enlaces de documento en `features/inventory/pages/movement-list` (referencia de la plantilla) y botones de acción en detalle de `purchase-detail`.

### Comportamiento actual
Ver hechos: Documento enlaza, Comprobante no; el detalle no ofrece un botón claro hacia el cobro.

### Restricciones
Sin texto hardcodeado (claves en es/en/pt); `tr()` solo dentro de funciones; sin HEX; sin dependencias nuevas; la visibilidad del enlace la decide el servidor (`source.available`), el frontend no es la barrera.

### Riesgos identificados
- Enlace a `receivables/:kind/:number` exige módulo `receivables` habilitado: cubierto por `source.available`.
- Dos enlaces (Documento y Comprobante) al mismo destino en servicios pueden parecer redundantes: aceptado (ver DDR).

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado de presentación en dos pantallas y un modelo auxiliar, sin decisión arquitectónica, contrato ni dominio nuevos.

### Diseño requerido
**SI** — cambios visibles en lista y detalle de una pantalla con DDR vigente; hay que fijar estilo de enlace, aviso y botón de acción.

## Diseño
Ver `docs/design/DDR-refinar-ux-libro-entradas-enlaces-lista-y-detalle.md`.

## Arquitectura
No aplica según veredicto.

## Plan
Ver `docs/plans/PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces.md` (v1, COMPACTO).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
