# PLAN-2026-11-04-refinar-ux-pedidos-ventas (v1)

**Task:** TASK-refinar-ux-pedidos-ventas · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-refinar-ux-pedidos-ventas-lista-y-detalle · Sin ADR

## Objective
Hacer que el detalle de un pedido ponga productos, total y saldo antes que los datos de auditoría, acerque «Registrar pago» al saldo y deje de mostrar «Sin saldo» en pedidos vacíos; y compactar la lista de pedidos. Solo presentación en `features/sales`.

# Specification
- **Expected behavior:** el comportamiento de negocio no cambia; cambian orden, jerarquía y affordances según el DDR.
- **Acceptance criteria:**
  - AC-01 El detalle muestra, en este orden: Entrega/Cobro, Productos, Importes, Pagos, Salida de inventario (si existe) y Datos del pedido; «Creado/Última actualización» van en una línea `text-muted` al pie de Datos del pedido.
  - AC-02 Con `canRegisterPayment`, la tarjeta Cobro tiene «Registrar pago»; al pulsarlo se abre el formulario de pago y se desplaza hasta él.
  - AC-03 Con pedido sin líneas, Cobro muestra «Sin productos» en tono atenuado, sin «Sin saldo» verde y sin «Registrar pago». Con total > 0 y saldo 0 sigue «Sin saldo» en verde.
  - AC-04 «Editar datos», «Aplicar» y «Agregar» son `btn-outline-primary`; la acción de estado sigue `btn-primary`.
  - AC-05 La fecha de cada pago se muestra `dd/MM/yyyy`.
  - AC-06 Quitar una línea pide confirmación; cancelar el diálogo no llama a la API.
  - AC-07 Pedido editable sin líneas: el buscador de producto recibe foco al cargar el detalle.
  - AC-08 Lista: la columna Pedido muestra el código como enlace principal y la fecha debajo; clic en la fila navega al detalle.
  - AC-09 Lista: Canal, Fecha de, Desde y Hasta están bajo «Más filtros» (colapsado por defecto, abierto si hay alguno activo; `aria-expanded`); atajos, Entrega, Pago y Cliente siguen visibles; los filtros siguen funcionando igual.
  - AC-10 Textos nuevos en `es`/`en`/`pt` con las mismas claves.
- **Edge/error cases:** pedido cancelado (sin Registrar pago, `canRegisterPayment` falso); pedido entregado con saldo (aviso conservado y Registrar pago visible); módulo Clientes deshabilitado (el filtro Cliente sigue oculto, `customersDisabled`).
- **Out of scope:** alta con líneas en el mismo formulario (requiere backend); buscador de texto en la lista (la API no lo soporta); cambiar qué estados permiten editar líneas (regla de negocio del servidor); tema/skin, tipografía global y fondo de inputs; modal de entrega; Compras u otros módulos.

# Test Specification
Pruebas de componentes Karma con `provideTestTranslations()` y las fixtures de `testing/order-fixtures.ts`; sin pruebas de backend (no cambia).
- AC-01, AC-03, AC-05, AC-07: `order-detail`, `order-items`, `order-payments` specs (orden de tarjetas por `data-testid`, texto «Sin productos», formato de fecha, foco).
- AC-02: `order-detail.spec` (clic en el botón de Cobro abre el formulario de Pagos).
- AC-04: specs de `order-summary`/`order-items` (clases).
- AC-06: `order-items.spec` o `order-detail.spec` (con diálogo cancelado no se emite `itemRemove`/no se llama a la API).
- AC-08, AC-09: `order-list.component.spec.ts` y `order-list-filters.spec.ts` (activación de fila, estado del colapsable, apertura por filtro activo).
- AC-10: prueba existente de claves i18n + `npm run i18n:check`.
**E2E: NO** — cambios de presentación cubiertos por pruebas de componente; no hay flujo crítico nuevo.

# Implementation Plan
- **Files affected:** frontend: `features/sales/pages/order-detail/*`, `components/order-items/*`, `components/order-summary/*`, `components/order-payments/*`, `pages/order-list/*` (+ specs), `src/assets/i18n/{es,en,pt}.json`. Backend: ninguno. Docs: TASK y `design-system.md` solo si se confirma un patrón nuevo.
- **Steps:**
  1. Reordenar el template del detalle y compactar Datos del pedido (AC-01).
  2. Estado «Sin productos» en Cobro y botón «Registrar pago» en Cobro con `ViewChild` a `app-order-payments.open()` + scroll (AC-02, AC-03).
  3. Cambiar clases de botones y formato de fecha de pagos (AC-04, AC-05).
  4. Confirmación al quitar línea con el diálogo ya usado en el detalle (AC-06); foco inicial del buscador (AC-07).
  5. Lista: columna Pedido, fila clicable y «Más filtros» (AC-08, AC-09).
  6. Claves i18n en los tres idiomas y pruebas (AC-10); `npm run lint`, `npm test`, `npm run build`, `npm run i18n:check`.
- **Risks / New dependencies:** pruebas existentes que dependen del orden de tarjetas; verificar en el build la hipótesis del fondo azul/índigo (no se toca). Sin dependencias nuevas.
