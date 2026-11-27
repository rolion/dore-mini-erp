# DDR-numeracion-correlativa-compras-codigo-y-bloqueo: Cómo se muestra el número de compra y el bloqueo al confirmar

**Estado:** Propuesto
**Task relacionado:** TASK-numeracion-correlativa-compras
**Fecha:** 2026-11-26

## Contexto
La compra pasa a tener un número `NC-000001` que se repite entre períodos fiscales, y confirmar puede quedar bloqueado si no hay período fiscal abierto para su fecha. Es la gemela de `DDR-numeracion-correlativa-pedidos-venta-codigo-y-bloqueo` (mergeado): se aplican los mismos patrones. Todas las pantallas ya muestran la `reference` que entrega el API.

## Pantallas/flujos afectados
- Lista de compras (tabla y tarjetas) y detalle (pestaña «Resumen»): identificación de la compra.
- Recepciones (detalle y formulario) y pestañas de pagos: solo reciben la nueva `reference`.
- Confirmar compra (diálogo de confirmación del detalle): estado de bloqueo (409).

## Componentes/patrones elegidos
- **Lista** (plantilla Lista con la variante de seguimiento de estados, `docs/design/design-system.md` sección 5, referencia `features/purchases/pages/purchase-list`): la referencia sigue en el enlace `fw-bold`. Si hay número, el nombre del período aparece como `small.text-body-secondary` bajo la fecha («Período {nombre}»), en tabla y tarjetas. Sin número (borrador o heredado), solo la etiqueta provisional.
- **Detalle** (plantilla Detalle con acciones de ciclo de vida, referencia `purchase-detail`): el título conserva «Compra {referencia}»; en la ficha del Resumen, bajo la referencia, una fila `dt/dd` «Período fiscal» con el nombre, solo si hay número.
- **Bloqueo al confirmar:** `app-fiscal-period-alert` (alerta tenue `alert-warning`, mismo componente que ventas, movido a `shared/components`), sobre las acciones del detalle; el enlace a Contabilidad solo si el módulo está habilitado. Reemplaza el toast para estos dos códigos (los demás errores de la acción siguen en toast). Sin pantallas nuevas.
- Se actualiza `docs/design/design-system.md` solo para reflejar que el componente vive ahora en `shared/components` (sección 3), si lo lista.

## Alternativas consideradas
- Dejar el toast con el `detail` del servidor: efímero y sin enlace; inconsistente con ventas.
- Mostrar el año en el código (`NC-2026-000001`): contradice el formato `NC-xxxxxx`.

## Comportamiento por privilegio/estado
- Borrador: etiqueta provisional `COM-…`, sin período.
- Confirmada y posteriores (incluye cancelada tras confirmar): `NC-…` y período, sin cambios de color ni de acciones.
- El backend es la barrera: el 409 `fiscal_period_missing`/`fiscal_period_closed` lo impone el servidor; el frontend solo lo explica.

## Consecuencias
Compras heredadas con fecha fuera de todo período siguen sin número y muestran la etiqueta provisional: deuda visual aceptada. Textos nuevos en `es`, `en` y `pt` (se reutilizan las claves `SALES.FISCAL_PERIOD.*` del componente; al moverlo, pasan a `COMMON.FISCAL_PERIOD.*` o equivalente).
