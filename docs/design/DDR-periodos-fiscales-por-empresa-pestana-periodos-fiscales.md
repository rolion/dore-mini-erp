# DDR-periodos-fiscales-por-empresa-pestana-periodos-fiscales: Pestaña «Períodos fiscales» en la configuración de Contabilidad

**Estado:** Propuesto
**Task relacionado:** TASK-periodos-fiscales-por-empresa
**Fecha:** 2026-11-16

## Contexto
La persona administradora debe crear, editar, cerrar y reabrir períodos desde Configuración (CONT-10). CONT-11 reorganizará la navegación (Configuración contendrá Clasificaciones y Períodos fiscales); hoy Configuración es `Contabilidad › Configuración` con pestañas Cuentas y Métodos de pago.

## Pantallas/flujos afectados
- `Contabilidad › Configuración` (`/pocketbiz/accounting/settings`): tercera pestaña **Períodos fiscales**. Sin ruta ni ítem de menú nuevos.
- Listado: nombre, inicio, fin, estado (badge «Abierto»/«Cerrado» con texto), acciones por fila.
- Diálogo **Nuevo/Editar período** (nombre, inicio, fin). Editar solo en períodos abiertos.
- Diálogo de confirmación **Cerrar** (aviso: no se podrán contabilizar asientos con fecha en el período; no genera asientos de cierre; puede reabrirse) y **Reabrir**.

## Componentes/patrones elegidos
Plantilla «Configuración con listados en pestañas y diálogo» (design-system §5; referencia `features/accounting/components/accounts-tab` y `account-dialog`): tabla Bootstrap simple apilada en móvil, badges de estado §3, `btn-primary` para «+ Nuevo período», diálogos `NgbModal` con `backdrop: 'static'`, errores 409 en `alert alert-warning` dentro del diálogo sin perder lo escrito, toast de éxito. Cierre/reapertura reutilizan el patrón de `deactivate-dialog` (confirmación, sin motivo: la tarjeta no pide motivo). Sin componentes nuevos del tema ni cambios a `design-system.md`.

## Alternativas consideradas
- Pantalla propia con ruta y menú: duplicaría navegación que CONT-11 va a rehacer; rechazada.
- Calendario visual de períodos: sin necesidad real; rechazada.

## Comportamiento por privilegio/estado
- **Cargando:** indicador de la plantilla. **Vacío:** «Aún no hay períodos fiscales» con explicación (sin períodos no se podrá contabilizar asientos) y botón «Crear período». **Error:** alerta con «Reintentar». **Éxito:** toast.
- Orden: más reciente primero (inicio descendente).
- Fila abierta: «Editar», «Cerrar». Fila cerrada: «Reabrir»; nombre y fechas solo lectura.
- Errores del servidor mostrados en el diálogo: fechas invertidas (campo fin), nombre duplicado (campo nombre), solapamiento (409 con el nombre del período en conflicto), cambio de límites bloqueado por asientos (409).
- Foco y teclado: diálogos con foco inicial en el primer campo, `Esc` cierra, etiquetas asociadas, estado comunicado con texto además del color.
- Solo administradores acceden (la pestaña vive en una pantalla ya restringida). **El frontend no es la barrera:** el backend aplica rol admin, empresa del usuario, solapamientos, inmutabilidad del cerrado y bloqueo de límites.
- Todo texto con claves i18n es/en/pt.

## Consecuencias
Sin deuda visual nueva. Al llegar CONT-11 la pestaña se mueve bajo Configuración sin cambiar su contenido; el ancho de la pestaña bar crece a tres pestañas (mantener el patrón de teclado WAI-ARIA existente).
