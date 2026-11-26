# DDR-numeracion-correlativa-pedidos-venta-codigo-y-bloqueo: Cómo se muestra el número de pedido y el bloqueo al confirmar

**Estado:** Propuesto
**Task relacionado:** TASK-numeracion-correlativa-pedidos-venta
**Fecha:** 2026-11-25

## Contexto
El pedido pasa a tener un número `NV-000001` que se repite entre períodos fiscales, y confirmar puede quedar bloqueado si no hay período fiscal abierto para la fecha. Todas las pantallas ya muestran el `code` que entrega el API, así que el cambio visual es de contexto, no de estructura.

## Pantallas/flujos afectados
- Lista de pedidos (tabla y tarjetas compactas) y detalle del pedido: identificación del pedido.
- Diálogos de entrega, pago y devolución y el historial de compras del cliente: solo reciben el nuevo `code`.
- Formulario único de pedido (`order-create`, «Iniciar preparación») y detalle («Iniciar preparación»): estado de bloqueo (409).

## Componentes/patrones elegidos
- **Lista** (plantilla Lista, variante compacta; `docs/design/design-system.md` sección 5): el código sigue en el enlace `fw-bold`. Cuando el pedido tiene número, el nombre del período aparece como `small.text-body-secondary` junto a la fecha («Período 2026»). Sin número (pedido NEW o heredado), se muestra la etiqueta provisional y ningún período, como hoy.
- **Detalle** (plantilla «Detalle de documento en curso con acciones en la cabecera»): el `h4` conserva «Pedido {code}». Bajo él, `small.text-body-secondary` con «Período fiscal: {nombre}» solo si está numerado.
- **Bloqueo al confirmar:** `alert alert-warning` (patrón de 409 de reglas de negocio, sin perder lo escrito) con el motivo en texto: «La fecha del pedido no está en ningún período fiscal. Cree el período en Contabilidad para poder confirmarlo.» o «El período fiscal «{nombre}» está cerrado…». Un enlace a Períodos fiscales se muestra solo si el módulo Contabilidad está habilitado (`ModulesService.enabledKeys$`), como en el resto de enlaces entre módulos. En `order-create` el borrador y los datos escritos se conservan.
- Sin pantallas ni componentes nuevos; nada que añadir a `design-system.md`.

## Alternativas consideradas
- Mostrar el año en el propio código (`NV-2026-000001`): contradice el formato pedido por el usuario (`NV-xxxxxx`).
- Badge de período en cada fila: ruido visual; basta texto secundario.
- Ocultar la etiqueta provisional hasta confirmar: el pedido NEW quedaría sin identificación visible; se mantiene como hoy.

## Comportamiento por privilegio/estado
- Pedido NEW: etiqueta provisional, sin período.
- Pedido confirmado y posteriores (incluye cancelado y devuelto): `NV-…` y período, sin cambios de color ni de acciones.
- El backend es la barrera: el 409 `fiscal_period_missing`/`fiscal_period_closed` lo impone el servidor; el frontend solo lo explica.

## Consecuencias
Pedidos heredados con fecha fuera de todo período siguen sin número y muestran la etiqueta provisional: deuda visual aceptada. Los textos nuevos van en `es`, `en` y `pt`.
