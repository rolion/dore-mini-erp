# PLAN-2026-11-15-refinar-ux-libro-entradas-enlaces (v2)

**Task:** TASK-refinar-ux-libro-entradas-enlaces · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-refinar-ux-libro-entradas-enlaces-lista-y-detalle / Ninguno

## Objective
Hacer navegable el origen de cada entrada (el código `CB-…` enlaza al cobro) y mejorar la legibilidad de la lista y el detalle de Contabilidad › Entradas, sin tocar backend ni contrato.

# Specification
- **Expected behavior:** desde la lista y el detalle, la persona llega con un clic al cobro (servicios) o al pedido (productos) cuando el servidor lo declara disponible, y los enlaces, avisos y textos auxiliares son legibles.
- **Acceptance criteria:**
  - ~~AC-01~~ **Diferido (v2, aprobado por la persona):** En la lista, `Comprobante` es un enlace a `/pocketbiz/receivables/<kind>/<number>` cuando hay `receiptNumber`, `sourceAvailable` y `documentRef` con forma `kind/number`; en otro caso texto o «—» (sin enlace).
  - **AC-02 (v2):** En el detalle, `Comprobante` queda como texto (enlace diferido, ver AC-01) y el botón «Ver pedido» aparece solo para productos con origen disponible. ~~Versión v1:~~  `Comprobante` es enlace en las mismas condiciones y hay un botón «Ver cobro» (servicios) / «Ver pedido» (productos) junto a «Volver» solo si `sourceLink` existe.
  - AC-03 Los enlaces de Documento y Comprobante se ven como enlaces (color primario, subrayado en hover y foco) y tienen `aria-label` traducido.
  - AC-04 El aviso de contexto usa el estilo de alerta tenue del sistema.
  - AC-05 Textos auxiliares (periodo, cobertura, pie, nota, ID de origen) con contraste ≥ 4,5:1.
  - AC-06 La cabecera «Monto» queda alineada a la derecha con sus cifras (si se confirma el defecto).
  - AC-07 Claves nuevas en es/en/pt con las mismas claves; sin texto hardcodeado.
- **Edge/error cases:** módulo de origen deshabilitado → texto con «(módulo deshabilitado)»; productos sin `CB` → «—»; `documentRef` mal formado → sin enlace.
- **Out of scope:** backend, ruta por pago en `receivables`, anclaje al pago dentro del cobro, fila clicable, exportar CSV, formato decimal, ojo táctil de 44 px.

# Test Specification
Pruebas de componente (Karma, `provideTestTranslations()`) y unidad del modelo. **E2E: NO** (cambio de presentación sin flujo crítico nuevo).
| AC | Verificación |
|---|---|
| AC-01 (diferido) | unidad `sourceLink`/nuevo `receiptLink` (servicio con/sin `CB`, no disponible, mal formado, producto) + componente lista (`receipt-link`) |
| AC-02 | componente detalle: enlace y botón presentes/ausentes según el caso |
| AC-03 | componente: enlaces con `aria-label`; revisión visual en navegador (color/subrayado) |
| AC-04 | componente: `context-note` con clases `bg-info-subtle text-info-emphasis` |
| AC-05 | medición de contraste con estilos computados en el navegador (registrar valores en Implementación) |
| AC-06 | revisión visual en navegador |
| AC-07 | prueba de paridad de claves y `npm run i18n:check` |

# Implementation Plan
- **Files affected:** frontend únicamente: `features/accounting/models/entry.ts` (+ `receiptLink`), `entry-list.component.{html,ts,scss,spec.ts}`, `entry-detail.component.{html,ts,spec.ts}`, `assets/i18n/{es,en,pt}.json`; docs: `design-system.md` §10 si el estilo de enlace resulta global.
- **Steps:**
  1. Medir en el navegador el color de enlaces, el contraste de `text-muted`/ID y la alineación de «Monto» (confirma o descarta AC-03/05/06).
  2. Añadir `receiptLink(entry)` en `entry.ts` reutilizando la lógica de `sourceLink` y probarlo (AC-01).
  3. Lista: Comprobante como enlace con `data-testid="receipt-link"`; estilo de enlace; aviso tenue; contraste; alineación (AC-01, 03-06).
  4. Detalle: Comprobante como enlace, botón «Ver cobro»/«Ver pedido», contraste del ID y de la nota (AC-02, 03, 05).
  5. Claves i18n es/en/pt y pruebas (AC-07).
  6. `npm run lint`, `npm test`, `npm run i18n:check`, `npm run build`; revisión visual (claro y oscuro).
- **Risks / New dependencies:** sin dependencias. Riesgo: el estilo de enlace puede ser global del tema; limitar el cambio a esta pantalla y documentarlo.

## Changelog
- **v2** (2026-11-15): [Specification] AC-01 (Comprobante `CB-…` enlaza al cobro) diferido y AC-02 reducido (sin «Ver cobro»; «Ver pedido» solo productos), por instrucción explícita de la persona («de momento omite la liga hacia el cobro»). Motivo: REV-06, el backend guarda el número de la proforma sin `kind`, por lo que el enlace no se genera con datos reales. Se retiró `receiptLink` y las claves `VER_COBRO`/`VER_COBRO_N`.
