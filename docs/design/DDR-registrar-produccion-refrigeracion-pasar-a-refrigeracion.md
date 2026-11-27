# DDR-registrar-produccion-refrigeracion-pasar-a-refrigeracion: Formulario «Pasar a refrigeración»

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-produccion-refrigeracion
**Fecha:** 2026-11-26

## Contexto
El operario cierra la elaboración: confirma cuánto consumió de cada ingrediente, cuánto salió y cuándo entró a refrigeración. Debe ver lo previsto como punto de partida y, si falta stock, saber exactamente qué falta sin perder lo escrito.

## Pantallas/flujos afectados
- **Detalle de orden** (`/production/orders/:id`): en En preparación aparece la acción primaria **Pasar a refrigeración** (lleva a la pantalla nueva). En En refrigeración se muestra la sección **Producción registrada**: cantidad elaborada vs prevista, fecha y hora de ingreso, lote (código), costo total («Sin costo» si no hay), y tabla de ingredientes con previsto y consumido real.
- **Nueva pantalla** `/production/orders/:id/refrigerate`: cabecera con orden, receta y almacén (solo lectura); tabla **Ingredientes** con Previsto (solo lectura) y **Consumo real** (campo numérico precargado con lo previsto, un campo por línea); campo **Cantidad elaborada** (precargado con el previsto) con unidad del producto; campo **Fecha y hora de ingreso** (`datetime-local`, precargada con ahora). Pie: **Pasar a refrigeración** (primario, se deshabilita mientras envía → evita doble clic) y Cancelar (`unsavedChangesGuard`).
- **Lista**: badge nuevo «En refrigeración» y filtro de estado ampliado.

## Componentes/patrones elegidos
Plantilla «Formulario con líneas» de `docs/design/design-system.md` §5 (`purchase-form`) con líneas fijas (derivadas de la orden); detalle según `purchase-detail`; badges de §3; tarjetas bajo 957 px como en el detalle actual. Sin componentes nuevos de Oreva.

## Alternativas consideradas
- Modal sobre el detalle: descartado; la tabla de ingredientes editable no cabe bien en móvil.
- Un solo campo de rendimiento por preparación: descartado; la tarjeta pide cantidad elaborada total.

## Comportamiento por privilegio/estado
- Cargando (detalle de la orden), error de carga con reintento, enviando (botón con spinner, campos deshabilitados), éxito (aviso y regreso al detalle con el lote).
- **Faltante de stock (409)**: alerta en la parte superior «No hay existencias suficientes» y, en cada fila afectada, marca y texto «Falta X unidad (hay Y)»; los valores escritos se conservan y la orden sigue En preparación. Sin período fiscal abierto: alerta con el mensaje del servidor.
- Validación en línea: consumo ≥ 0, cantidad elaborada > 0, fecha no anterior al inicio ni futura; errores por campo del servidor bajo el campo.
- El frontend solo oculta/deshabilita; **el backend** impone módulo habilitado, aislamiento por empresa, estado, rangos, todo-o-nada, idempotencia y bloqueo del lote para empaque.

## Consecuencias
Deuda aceptada: sin lectura previa del saldo por ingrediente (el faltante se informa al enviar, no antes). Pantalla de liberación/empaque queda para tarjetas siguientes.
