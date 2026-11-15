# DDR-refinar-ux-libro-entradas-enlaces-lista-y-detalle: Enlace al cobro y legibilidad en Entradas (lista y detalle)

**Estado:** Propuesto (actualizado 2026-11-15: el enlace al cobro desde Comprobante y el botón «Ver cobro» están **diferidos** por REV-06; se conserva el botón «Ver pedido» y el resto)
**Task relacionado:** TASK-refinar-ux-libro-entradas-enlaces
**Fecha:** 2026-11-15

## Contexto
La persona pide que el código del cobro de la tabla de Entradas sea un enlace al cobro (módulo Cobros). La revisión de la pantalla encontró además enlaces poco visibles, un aviso informativo con contraste insuficiente y un detalle sin salida clara hacia el origen. Refina el DDR `DDR-libro-entradas-filtros-totales-pantallas-entradas.md`; no cambia sus columnas, filtros ni totales.

## Pantallas/flujos afectados
- Lista `/pocketbiz/accounting/entries` y detalle `/pocketbiz/accounting/entries/:id`.

## Componentes/patrones elegidos
Plantillas «Lista de solo lectura con filtros» y «Detalle» de `docs/design/design-system.md` §5, sin componentes nuevos.
- **Comprobante (`CB-…`) = enlace al cobro** (`/pocketbiz/receivables/<kind>/<number>`, el detalle del cobro donde el comprobante figura en «Pagos»). Solo si hay `CB`, `source.available` y destino válido; si no, texto o «—». Productos no tienen `CB`: «—».
- **Documento** sigue enlazando al origen (pedido o proforma). En servicios ambos enlaces comparten destino: se acepta; Comprobante responde a la petición explícita y Documento ya existía.
- **Estilo de enlace:** color `primary` (regla del sistema), subrayado al pasar el cursor y con foco visible; el icono/texto no depende solo del color (subrayado en foco/hover). `aria-label` «Ver cobro CB-000002» (clave i18n con parámetro).
- **Detalle:** Documento y Comprobante con el mismo estilo de enlace; botón primario «Ver cobro» (servicios) o «Ver pedido» (productos) junto a «Volver» cuando el servidor declara el origen disponible. «ID del pago de origen» se conserva (trazabilidad) pero con contraste AA.
- **Aviso de contexto:** `alert alert-info bg-info-subtle text-info-emphasis border-info-subtle` (patrón tenue admitido, §5).
- **Textos auxiliares** (periodo, cobertura, pie de tabla, nota del detalle): color con contraste ≥ 4,5:1 (medido con estilos computados; `text-body-secondary` si `text-muted` no llega).
- **Cabecera «Monto»** alineada a la derecha igual que sus cifras.
- Todo el texto vía `translate` (es/en/pt).

## Alternativas consideradas
- **Un solo enlace por fila (solo Comprobante):** quita el acceso al pedido de productos y regresa lo que ya existe; descartado.
- **Fila completa clicable, exportar CSV, formato `Bs 900,00`:** fuera de alcance (mejoras de otro orden o decisión regional).
- **Anclar al pago concreto dentro del detalle del cobro:** exige tocar `receivables` (id en la fila + scroll); no se hace aquí.

## Comportamiento por privilegio/estado
Sin cambios: solo administrador de empresa y módulo `accounting`. **El frontend no es la barrera:** el backend decide `source.available` y aplica permisos y aislamiento por empresa; si el módulo propietario está deshabilitado se muestra texto «(módulo deshabilitado)» sin enlace.

## Consecuencias
Pequeña inconsistencia aceptada: otras pantallas aún usan `alert-info` plano (el sistema ya pide migrarlas al tocarlas). Si el estilo de enlace resulta ser global (no solo de la tabla), se anota en `design-system.md` §10.
