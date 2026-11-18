# DDR-incorporar-egresos-reversion-libro-lista-y-detalle-entradas: Lista y detalle de Entradas con egresos y reversiones

**Estado:** Propuesto
**Task relacionado:** TASK-incorporar-egresos-reversion-libro
**Fecha:** 2026-11-15

## Contexto
El libro pasa de solo ingresos a ingresos, egresos y reversiones. No se crean pantallas.

## Pantallas/flujos afectados
- `features/accounting/pages/entry-list` (lista con filtros y totales) y `pages/entry-detail`.

## Componentes/patrones elegidos
Se mantienen las plantillas de lista y detalle de `docs/design/design-system.md` (sección 5) y sus tokens. Cambios mínimos:
- Filtro nuevo «Dirección» (Todas / Ingresos / Egresos) junto al de origen; el de origen suma «Gastos» y «Pagos de compras».
- Columna/insignia de tipo: `badge-outline` de origen existente; una reversión muestra además la insignia «Reversión» y, en el detalle, el enlace al movimiento original (y el original, a su reversión).
- Importes de egreso (y reversión de ingreso) con signo «−» y clase de texto de contexto; la reversión de un egreso se muestra como entrada de dinero.
- Totales: se conserva el total de ingresos y se añaden Egresos y Neto por moneda, sin sumar monedas.
- Detalle: muestra la clasificación y, para egresos, el origen (gasto/pago de compra) con enlace solo si el módulo está habilitado y existe pantalla.
- Sin texto hardcodeado: claves nuevas en `es/en/pt`.

## Alternativas consideradas
Pestañas separadas Ingresos/Egresos (más navegación, duplica filtros y totales): descartada.

## Comportamiento por privilegio/estado
Cargando, vacío y error como hoy. Solo lectura: no hay acciones de edición ni reversión en la UI. El backend filtra por empresa y bloquea el módulo; el frontend no es la barrera.

## Consecuencias
La lista mezcla direcciones; los enlaces a documentos de gastos/compras se activan cuando GAS-01/COM-01 expongan su pantalla de detalle.
