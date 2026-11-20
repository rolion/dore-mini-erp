# DDR-adaptar-reportes-libro-partida-doble-seccion-contable-en-reportes: Sección «Libro contable» en la pantalla de Reportes

**Estado:** Propuesto
**Task relacionado:** TASK-adaptar-reportes-libro-partida-doble
**Fecha:** 2026-11-18

## Contexto
La persona necesita ver el flujo de dinero y el resultado contable sin confundirlos con los reportes operativos de Ventas y Gastos. La tarjeta prohíbe un quinto submenú de Contabilidad.

## Pantallas/flujos afectados
Solo `/pocketbiz/reports` (`features/reporting/pages/reports`). Se añade, bajo el selector de periodo existente, un bloque «Libro contable» con dos tarjetas (`app-report-card`) y un aviso de cobertura:
1. **Flujo de dinero:** entradas, salidas, neto, transferencias internas (informativo, «no cambian el flujo neto») y saldo inicial/final; tabla por cuenta de dinero.
2. **Resultado contable:** Ingresos, Costos, **Margen** (ingresos − costos), Gastos y **Resultado** (margen − gastos).
3. **Aviso de cobertura** (`alert alert-warning`): «Parte del periodo es anterior al corte contable (dd/mm/aaaa); esos datos no se incluyen.» cuando `partial`.
Los reportes operativos existentes no cambian de lugar; cada uno muestra su criterio con la etiqueta «Operativo» (ventas por pedido, gastos por fecha de gasto), y el bloque contable «Contable (libro de asientos)».

## Componentes/patrones elegidos
Plantilla «Dashboard y reportes» de `docs/design/design-system.md` §5: `app-period-selector`, `app-report-card`, tablas `table table-sm`, `<small class="text-muted">` para criterios, `money` pipe. Sin componentes nuevos ni desviaciones. Etiquetas de negocio exactas: «Margen», «Resultado» (nunca «utilidad»); «Ganancia estimada» del dashboard no se renombra.

## Alternativas consideradas
- **Pantalla/submenú nuevo de Contabilidad:** descartado por la tarjeta.
- **Mezclar las cifras contables en las tarjetas operativas:** confunde flujo con resultado. Descartado.

## Comportamiento por privilegio/estado
- Módulo `accounting` deshabilitado: el bloque conserva títulos y dice **«No disponible: módulo deshabilitado»** (nunca 0).
- Cargando / error con reintento / sin movimientos («Sin registros» en tablas; totales en 0) según §4 del sistema de diseño.
- El permiso sigue el de Reportes; **el backend** aplica empresa (token), módulo y rango; el frontend no es barrera.
- Textos con `translate` y claves en `es/en/pt`.

## Consecuencias
La pantalla de Reportes crece; la deuda visual existente no cambia. Los textos de criterio distinguen operativo de contable, pero ambos pueden mostrar cifras distintas por diseño (documentado en el criterio).
