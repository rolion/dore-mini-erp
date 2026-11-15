# TASK-refinar-ux-libro-entradas-enlaces: Refinar UX del libro de Entradas (legibilidad; enlace al cobro diferido)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-refinar-ux-libro-entradas-enlaces
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/73

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-15 | (nuevo) → INVESTIGATION | Task creado a partir de la crítica de diseño de Contabilidad › Entradas; `main` al día (6b4f7d1) | delivery-start |
| 2026-11-15 | INVESTIGATION → DESIGN → PLANNING | NEEDS_PLAN: solo frontend del módulo `accounting`, sin contrato API ni reglas de dominio nuevas | delivery-start |
| 2026-11-15 | PLANNING → ENGINEERING | Specification READY; el alcance se acotó con criterio propio (ver plan) | delivery-start |
| 2026-11-15 | ENGINEERING → REVIEW | Implementación según plan v1 | delivery-build |
| 2026-11-15 | REVIEW → PUBLISH | Quality Gate PASS con reservas (1 Medium y 4 Low abiertos; revisión visual y contraste no verificados); a la espera de aprobación humana | delivery-publish |

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
Solo frontend de `accounting`; pantallas de referencia: lista de solo lectura con filtros y detalle (sin cambios de estructura).
- **AC-01/02:** `receiptLink()` en `models/entry.ts` (solo servicios con comprobante, reutiliza `sourceLink`); Comprobante enlazado en lista (`receipt-link`) y detalle; botón primario «Ver cobro»/«Ver pedido» junto a «Volver» en el detalle.
- **AC-03:** enlaces con `link-primary` y `aria-label` traducido (`VER_COBRO_N`).
- **AC-04:** aviso de contexto con `bg-info-subtle text-info-emphasis border-info-subtle`.
- **AC-05:** textos auxiliares (periodo, cobertura, ID de origen, nota del detalle) pasan de `text-muted` a `text-body-secondary`. **No se midió el contraste real en el navegador.**
- **AC-07:** claves `VER_COBRO`, `VER_PEDIDO`, `VER_COBRO_N` en es/en/pt; `npm run i18n:check` sin faltantes.
- **Pruebas:** `entry.spec.ts` (receiptLink), lista (enlace CB y aviso tenue), detalle (enlace, botón, origen no disponible); se ajustó la prueba existente que prohibía `.btn-primary` en el detalle. Resultado local: lint OK; Karma, 83 pruebas de `accounting` y `core/i18n` OK.
- **Desviaciones:** (1) AC-06 (alineación de «Monto») **no se tocó**: la cabecera ya tiene `headerClass="text-end"`, el defecto no está confirmado y requiere revisión visual. (2) Medición previa del paso 1 del plan no realizada (no se levantó la app con backend). (3) `npm run build` no se ejecutó en la implementación (el Quality Gate lo ejecutó y pasa). (4) Para correr pruebas se creó una junction `node_modules` hacia el checkout principal (no versionada, sin dependencias nuevas).
- **Deuda:** no existe ruta por pago en `receivables`; el enlace lleva al detalle del cobro.

## Review
**PASS con reservas.** Suite completa 1413/1413, lint, i18n:check y build OK; `npm audit`: 2 moderate preexistentes (hono), ajenos al diff. Sin Critical/High. Revisión visual, contraste (AC-05) y AC-06 no verificados.
- docs/reviews/REV-2026-11-15-refinar-ux-libro-entradas-enlaces-01.md (Low, IMPLEMENTATION)
- docs/reviews/REV-2026-11-15-refinar-ux-libro-entradas-enlaces-02.md (Medium, PLAN)
- docs/reviews/REV-2026-11-15-refinar-ux-libro-entradas-enlaces-03.md (Low, PLAN)
- docs/reviews/REV-2026-11-15-refinar-ux-libro-entradas-enlaces-04.md (Low, IMPLEMENTATION)
- docs/reviews/REV-2026-11-15-refinar-ux-libro-entradas-enlaces-05.md (Low, SPECIFICATION)

## Publicación
PR listo para aprobación humana (no se mergea). Decisión pendiente: aceptar REV-02 (contraste sin medir) o exigir medición en navegador antes del merge.

### Corrección posterior al Quality Gate (2026-11-15)
REV-01, 04 y 05 resueltos; REV-02 con contraste calculado (no medido en navegador) y último `text-muted` migrado; REV-03 sigue abierto (requiere navegador). Suite completa 1413/1413 (una prueba ajena de `core/i18n/screens-i18n.spec.ts` es intermitente por orden aleatorio: falló en 3 de 6 ejecuciones y pasó en las demás; preexistente, fuera de alcance).

### Verificación visual (2026-11-15)
App real (`npm start`) contra un servidor API simulado local con datos de prueba (no hay backend ni credenciales). Resultado: enlaces azules con subrayado al pasar el cursor, aviso tenue, textos auxiliares ≥ 4,59:1 en tema claro, botón «Ver cobro» en el detalle. Se corrigió la alineación de «Monto» (REV-03) y se añadió subrayado en hover/focus (scss). **Hallazgo nuevo REV-06 (High, SPECIFICATION):** con datos reales de servicios el backend guarda solo el número (`ODO-000002`) y `sourceLink` necesita `kind/number`, por lo que el enlace al cobro no se genera. Requiere decisión de contrato/datos. Tema oscuro y móvil no verificados.

### Alcance reducido (2026-11-15)
Por instrucción explícita de la persona («de momento omite la liga hacia el cobro») se retiró el enlace de Comprobante y el botón «Ver cobro» (PLAN v2; REV-06 queda *Deferred*). Se conservan: botón «Ver pedido» (productos), `aria-label` en Documento, aviso tenue, textos secundarios, alineación de «Monto» y subrayado en hover/foco. Lint OK, i18n:check OK, suite completa 1410/1410 (la prueba intermitente de `core/i18n` falló en una ejecución y pasó en la siguiente). Revisión visual posterior a este recorte: no repetida.

### Segunda pasada del Quality Gate y revisión visual (2026-11-15)
- Quality Gate (subagente aislado) tras el recorte: **PASS con reservas**. Lint, i18n:check (1949/0) y build OK; `npm audit`: 2 moderate preexistentes (hono); sin restos del enlace al cobro; sin scope creep. Suite: 1410 pruebas, con la prueba ajena intermitente fallando 3 de 4 ejecuciones (REV-09).
- Revisión visual en la app real contra API simulada: escritorio claro OK (contrastes 4,59 a 7,65:1, «Monto» alineado, `CB-…` como texto); detalle en móvil OK; **hallazgos:** REV-07 (High, preexistente: en móvil la lista no deja llegar al botón del detalle), REV-08 (Medium: enlaces 3,87:1 en tema oscuro), REV-09 (Low, prueba intermitente ajena).
- Pendiente de decisión: REV-07 (fuera del alcance) y REV-08.

### Corrección REV-08 (2026-11-15)
Parcial de estilos `accounting/styles/_entry-links.scss` (subrayado hover/foco + color de enlace en tema oscuro, 7,21:1 medido). Lint OK, build OK, pruebas de `accounting` 61/61. REV-08 Resolved. Siguen abiertos REV-07 (móvil, fuera del alcance) y REV-09 (prueba ajena intermitente); REV-06 diferido.
