# DDR-liberar-lote-despues-refrigeracion-panel-liberacion: Panel de liberación en el detalle de la orden

**Estado:** Propuesto
**Task relacionado:** TASK-liberar-lote-despues-refrigeracion
**Fecha:** 2026-11-27

## Contexto
El encargado necesita ver, en la orden En refrigeración, cuándo ingresó el lote, cuánto lleva y desde cuándo puede liberarlo, y confirmar la liberación.

## Pantallas/flujos afectados
- **Detalle de la orden** (`order-detail`, plantilla Detalle del sistema de diseño, sección 5): nueva sección «Liberación» visible si la orden está `refrigerating` o `ready_to_pack`, junto a «Producción registrada». Muestra: ingreso a refrigeración, tiempo transcurrido, mínimo configurado, **primera hora habilitada** y, si ya se liberó, quién y cuándo. Acción primaria **Liberar lote** en la cabecera de acciones, solo en `refrigerating`; deshabilitada con texto «Disponible desde dd/MM/yyyy HH:mm» mientras no se cumpla el mínimo; al confirmar muestra un diálogo de confirmación con el lote y la cantidad (118 u).
- **Lista de órdenes**: badge y filtro «Listo para empacar».
- **Ajustes → Producción**: campo numérico «Horas mínimas de refrigeración» (formulario de ajustes existente, mismo patrón que el porcentaje).

## Componentes/patrones elegidos
Componentes compartidos y tokens de `docs/design/design-system.md`; `badge-outline` para estado, `order-row`/`dl` de la sección registrada, botón primario/`disabled` como en «Iniciar»; diálogo de confirmación igual al de otras acciones destructivas/irreversibles del proyecto. Sin componentes nuevos compartidos.

## Alternativas consideradas
- Liberar desde la lista: oculta el contexto (hora habilitada, cantidad); descartada.
- Botón oculto antes del mínimo: la persona no sabría cuándo; se prefiere deshabilitado con la hora.

## Comportamiento por privilegio/estado
`in_preparation`/`draft`: sin sección. `refrigerating`: sección y botón (habilitado o no según el mínimo; el tiempo transcurrido se calcula con el reloj local solo para informar y la habilitación del botón se refresca al cumplirse la hora). `ready_to_pack`: solo lectura con quién y cuándo. Estados: cargando, error con reintento, éxito, error 409 «aún no se puede liberar» con la hora habilitada. **El frontend no es la barrera:** el backend rechaza liberar antes del mínimo y fuera de `refrigerating`.

## Consecuencias
Todo texto en i18n es/en/pt. Deuda aceptada: el temporizador usa el reloj del navegador solo informativo; el servidor decide.
