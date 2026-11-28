# DDR-consultar-ordenes-seguimiento-estado-detalle-orden-rediseno: Rediseño del detalle de la orden de producción

**Estado:** Propuesto
**Task relacionado:** TASK-consultar-ordenes-seguimiento-estado
**Fecha:** 2026-11-27
**Reemplaza:** la parte «Detalle» de DDR-consultar-ordenes-seguimiento-estado-lista-y-detalle (la parte «Lista» sigue vigente).

## Contexto
Tras ver el detalle con datos reales, la crítica de diseño (pedida por el usuario) encontró que la pantalla es una pila de pares etiqueta/valor: el estado y los datos de identificación están al final, no hay línea de etapas, las cifras clave pasan desapercibidas, hay datos repetidos y el motivo del botón «Liberar lote» deshabilitado es un texto gris pequeño. El usuario pidió corregirlo en este mismo PR.

## Pantallas/flujos afectados
`/pocketbiz/production/orders/:id` (detalle). Sin cambios de API ni de comportamiento de negocio.

## Componentes/patrones elegidos
Plantilla «Detalle de documento en curso con acciones en la cabecera» de `design-system.md` §5, con estas piezas:
1. **Cabecera:** `h4` con el número, `app-status-badge` (icono + texto: Borrador gris, En preparación ámbar, En refrigeración azul, Listo para empacar verde) y debajo «receta · producto · almacén». Acciones a la derecha/abajo según ancho (primaria según estado, «Volver»).
2. **Línea de etapas:** cuatro pasos (Borrador → En preparación → En refrigeración → Listo para empacar) como lista ordenada; paso hecho (icono de check), actual (resaltado, `aria-current="step"`) y pendiente (atenuado). Bajo cada paso alcanzado, su fecha (creada, iniciada, ingreso a refrigeración, liberado). El estado nunca va solo en color.
3. **Cifras clave (tarjetas):** Producción prevista (siempre) y, con lote: Elaboradas («20 de 20 previstas»), Saldo físico, Disponible para empaque (resaltada) y Costo total («Sin costo» si no hay). Rejilla 1 columna en móvil, 2 en tablet, 4 desde escritorio.
4. **Dos tarjetas:** «Datos de la orden» (receta, producto, almacén, preparaciones, creada, iniciada) y «Lote y refrigeración» (código, estado del lote, ingreso, barra de progreso «0 h 4 min de 1 h» con `role="progressbar"`, primera hora habilitada, liberado por/el). Se elimina la repetición del ingreso y de lo previsto.
5. **Botón «Liberar lote» deshabilitado:** su motivo («Disponible desde …») va en texto legible de contraste normal bajo el botón y enlazado con `aria-describedby`.
6. **Ingredientes:** tabla (tarjetas bajo 957 px) con Previsto, Consumo real y columna **Diferencia** (`+`/`−` con unidad; «—» si no hay diferencia o aún no hay consumo real), calculada con enteros escalados, nunca con `float`.
Sin HEX ni fuentes propias: clases Bootstrap/variables CSS existentes.

## Alternativas consideradas
- Pestañas (Resumen / Lote / Ingredientes): oculta información que el encargado quiere ver junta; descartada.
- Mantener las filas etiqueta/valor y solo mover el estado arriba: no resuelve la jerarquía ni el progreso; descartada.

## Comportamiento por privilegio/estado
Las acciones por estado no cambian (Borrador: editar/iniciar; En preparación: registrar producción; En refrigeración: liberar; Listo para empacar: ninguna). El frontend no es la barrera: el backend valida estado y mínimo de refrigeración. Estados: cargando, error con «Reintentar», éxito de acción (`role="status"`) y error de acción (`role="alert"`).

## Consecuencias
El detalle de órdenes queda como referencia de «detalle con etapas»; si se reutiliza la línea de etapas en otro módulo se moverá a `shared/` (hoy un solo consumidor). La lista mantiene sus badges actuales (deuda: migrar a `app-status-badge`).
