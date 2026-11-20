# DDR-importacion-en-segundo-plano-progreso-de-la-importacion: Paso «Resultado» con corrida en cola, en curso y retomable

**Estado:** Propuesto
**Task relacionado:** TASK-importacion-en-segundo-plano
**Fecha:** 2026-11-20

## Contexto
La carga deja de ser instantánea: tras confirmar, la importación queda en cola y se procesa en segundo plano (ADR `ADR-importacion-en-segundo-plano-cola-en-base-de-datos-y-worker`). El asistente de `DDR-cargar-ventas-desde-archivo-asistente-de-importacion` debe mostrar el avance y permitir salir y volver.

## Pantallas/flujos afectados
- **Asistente «Importar ventas», paso 4 (Resultado)** (`features/data-import/pages/sales-import`): gana dos estados previos al resultado final.
- **Retomar `?run=<id>`**: hoy solo abre corridas `COMPLETED|FAILED`; pasa a abrir también `QUEUED|RUNNING`.
- **Historial** (`import-history`) y **detalle** (`import-detail`): nuevos estados `QUEUED` («En cola») y `RUNNING` («En curso») con su progreso, y mensaje de fallo.

## Componentes/patrones elegidos
- Misma plantilla del asistente (design-system §5, «Variante de operación con previsualización obligatoria» como referencia de la confirmación y el resultado). Sin pantallas nuevas.
- **Paso 4 en curso**: `.card` con `h5` (foco al entrar, como hoy), `progress` de Bootstrap (`.progress` + `.progress-bar`, `role="progressbar"` con `aria-valuenow/min/max`) y el texto «Procesando 120 de 480 ventas…» en `small.text-muted` dentro de `role="status" aria-live="polite"`. En cola: el mismo bloque sin barra, con «En cola: empezará en un momento.». Debajo, `alert alert-info bg-info-subtle text-info-emphasis border-info-subtle` (patrón tenue admitido): «Puedes salir de esta página: la importación sigue en segundo plano. Vuelve desde el historial.» y el enlace «Ir al historial» (`btn btn-light`).
- **Fallo del proceso** (`FAILED` con mensaje de la corrida): `alert alert-danger` con el motivo del servidor y «Volver a intentar» (vuelve al paso 3 conservando mapeo y opciones; reintentar es seguro, lo ya cargado sale «Ya importada»).
- **Consulta de estado**: sondeo cada 3 s con `timer` + `switchMap` y `takeUntilDestroyed`; se detiene al llegar a `COMPLETED|FAILED`, al salir de la página y si la pestaña queda oculta se espacia (sin suscripciones colgadas). Un error de red en el sondeo muestra «No se pudo consultar el avance. Reintentando…» (`small.text-danger`, `role="alert"`) y sigue intentando.
- **Badges de estado** (`app-status-badge`): `QUEUED` y `RUNNING` en tono `info` (texto, no solo color).
- El 409 `import_running` al confirmar sigue mostrándose como `alert-warning` sin perder lo escrito.

## Alternativas consideradas
- **Notificación (toast/correo) al terminar:** no hay infraestructura de notificaciones; descartada.
- **Bloquear el asistente hasta terminar con spinner:** reproduce la espera que causó el problema y no sobrevive a recargar. Descartada.
- **WebSocket/SSE para el avance:** sin infraestructura; el sondeo cada 3 s basta.

## Comportamiento por privilegio/estado
- Cargando (consulta inicial al retomar): `resuming` actual. Vacío: no aplica. Error de consulta: mensaje con reintento automático. Éxito: contadores actuales (`app-import-counts`) y detalle por venta.
- Sin sondeo si la corrida ya está `COMPLETED|FAILED`.
- **Backend (la barrera real):** solo administradores con `sales` y `catalog` habilitados; el estado de una corrida de otra empresa responde 404; el cliente no envía `company_id`; el worker toma empresa y usuario de la corrida guardada.

## Consecuencias
- El paso «Resultado» ahora puede mostrarse antes de tener resultados; el historial deja de ser solo de corridas terminadas.
- Sin nuevos componentes compartidos ni cambios en `design-system.md`: el bloque de progreso es local al asistente (se promueve a componente si otra pantalla lo necesita).
