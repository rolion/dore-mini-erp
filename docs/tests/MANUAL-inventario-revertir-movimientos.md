# Prueba manual: revertir movimientos mediante contramovimientos (PB-INV-008)

Task: `TASK-inventario-revertir-movimientos` · Plan: `docs/plans/PLAN-2026-10-30-inventario-revertir-movimientos.md` (v2) · PR: https://github.com/rolion/dore-mini-erp/pull/40

Cuenta: **oleon** (usuario admin de su empresa). Esta prueba **crea datos reales** en la base: usa nombres con prefijo `PRUEBA-REV` (productos, almacén, proveedor) para reconocerlos y descartarlos después. Las pantallas se prueban a ≈1440 px, ≈390 px (modo móvil de las herramientas del navegador) y en tema claro y oscuro (selector de tema de la plantilla, panel «Setting Panel»).

## Preparación

1. Backend (desde `backend/`, con `.env`, rama del PR): `python manage.py migrate` (aplica `purchases/0007_receipt_reversal`) y `python manage.py runserver`.
2. Frontend (desde `frontend/panel_admin/`): `npm start`. Entra a `http://localhost:4200/pocketbiz/login` con **oleon**.
3. Configuración → Módulos: habilita **Inventario**, **Compras** y **Ventas** si no lo están.
4. Inventario → Configuración: crea el almacén `PRUEBA-REV Central` (si no es el predeterminado, no importa) y una unidad `kg` si no existe.
5. Catálogo → Productos: crea `PRUEBA-REV Arroz` y `PRUEBA-REV Frijol`, ambos con **control de stock**, unidad `kg`, y marcados como **comprables**; a Arroz además **vendible** (para la venta de la sección D).
6. Compras → Proveedores: crea `PRUEBA-REV Proveedor`.
7. Inventario → Ajustes: deja la política de stock negativo **desactivada** (Inventario → Ajustes de configuración, interruptor «Permitir stock negativo»).

## A. Revertir un ajuste (Inventario)

| # | Paso | Resultado esperado |
|---|---|---|
| A1 | Inventario → Ajustes de existencias → nuevo ajuste de `PRUEBA-REV Arroz` en `PRUEBA-REV Central`, contado **5 kg**, motivo «Conteo inicial PRUEBA-REV». Confirma | Se crea el ajuste (entrada de 5 kg). Entra a su detalle |
| A2 | En el detalle del ajuste mira los botones | Aparece **Revertir** (naranja) junto a «Volver» |
| A3 | Pulsa **Revertir** | Diálogo «Revertir movimiento» con referencia `AJ-…`, tipo «Entrada de ajuste», producto, almacén, cantidad 5 kg y aviso: «Se registrará una salida de 5 kg en … El movimiento original se conserva como «Revertido»…». El botón **Revertir movimiento** está **deshabilitado** |
| A4 | Escribe solo espacios en el motivo | El botón sigue deshabilitado |
| A5 | Escribe un motivo de más de 200 caracteres | El campo no admite más de 200 (contador «n / 200») |
| A6 | Escribe «Conteo mal registrado» y pulsa **Volver** | Se cierra sin cambios; el ajuste sigue «Confirmado» |
| A7 | Antes de revertir, registra una salida que consuma parte del stock: Ajustes → ajuste de Arroz contando **2 kg** (baja a 2) | Se crea un ajuste de salida |
| A8 | Vuelve al ajuste del A1 → **Revertir** → motivo → **Revertir movimiento** | **No** se revierte: dentro del diálogo aparece un cuadro rojo «No hay existencia suficiente» con producto, almacén, **cantidad solicitada 5** y **existencia actual 2**. El diálogo no se cierra y el **motivo escrito se conserva** |
| A9 | Cierra el diálogo y activa «Permitir stock negativo»; vuelve a intentar la reversión | Esta vez se revierte (el saldo queda en −3). Vuelve a desactivar la política al terminar |
| A10 | Tras revertir (o con política activa) mira el detalle del ajuste | Alerta verde «Ajuste revertido»; estado **Revertido** (gris); **ya no** hay botón Revertir |
| A11 | Abre «Ver movimiento» del ajuste | Estado **Revertido**; bloque **Reversión** con enlace «Contramovimiento · <referencia>», «Revertido por» oleon, fecha/hora y el motivo escrito; sin botón Revertir ni mensaje de bloqueo |
| A12 | Sigue el enlace «Contramovimiento · …» | Detalle del contramovimiento: tipo **Salida**, «Revierte a este movimiento» enlazando al original, motivo igual al escrito; **sin botón Revertir** |

## B. Revertir un movimiento manual (sin documento)

Los movimientos sin origen no se crean desde la interfaz; si no tienes uno, sáltate B y valida el comportamiento equivalente con A (un ajuste es un origen manual). Si quieres cubrirlo, pide el movimiento por la fachada de Inventario en el shell de Django (`inventory.record_movement(...)` sin `source_type`) y repite A3–A12 desde Inventario → Movimientos.

## C. Compras: revertir una recepción

| # | Paso | Resultado esperado |
|---|---|---|
| C1 | Compras → nueva compra a `PRUEBA-REV Proveedor` con `PRUEBA-REV Arroz` 10 kg a 5,00 y `PRUEBA-REV Frijol` 6 kg a 4,00. Guarda y **Confirma** | Compra confirmada, total 74,00 |
| C2 | Registra una recepción de **4 kg de cada producto** en `PRUEBA-REV Central` | Recepción creada; estado de recepción «Parcial» |
| C3 | Pestaña «Pagos» → registra un pago de **20,00** | Pagado 20,00, saldo 54,00 |
| C4 | Abre el detalle de la recepción | Botón **Revertir recepción** (naranja); tabla de movimientos con columna **Estado** = «Confirmado» |
| C5 | Pulsa **Revertir recepción** | Diálogo con la recepción y compra, **tabla con las 2 líneas** (producto, cantidad, «Se registrará una salida de stock»), aviso azul «…**no devuelve los pagos registrados**», sin reversión parcial. Botón deshabilitado hasta escribir motivo (máx. 200) |
| C6 | **Antes de revertir**, consume stock de Arroz: Ajustes → ajuste de Arroz contando **1 kg** (queda 1 de los 4 recibidos, si partías de 0 más el ajuste que corresponda) y repite C5 con motivo «Devuelto al proveedor» → **Revertir recepción** | Cuadro amarillo **«No hay existencia suficiente para revertir la recepción. No se revirtió ninguna línea.»** con el **almacén** y **una línea por cada producto sin saldo** (se necesitan X y hay Y). El diálogo no se cierra, el motivo se conserva. Comprueba después que ni Arroz ni Frijol cambiaron de saldo (Inventario → Existencias) |
| C7 | Deshaz el consumo del C6 (ajuste de Arroz contando de nuevo el saldo correcto, o activa la política de stock negativo) y vuelve a **Revertir recepción** | Se cierra el diálogo; alerta verde «Recepción revertida»; estado **Revertida**; aparecen «Revertida el», «Revertida por» oleon y «Motivo de la reversión»; el botón desaparece |
| C8 | En la tabla de movimientos de la recepción | Ambos movimientos con estado **Revertido** y enlace «Ver contramovimiento» (abre su detalle: tipo Salida, «Revierte a…») |
| C9 | Inventario → Existencias | El saldo de Arroz y Frijol baja exactamente lo recibido (4 kg cada uno) |
| C10 | Vuelve a la compra (resumen y pestaña Recepciones) | La recepción aparece como **Revertida**; el estado de recepción vuelve a «No recibida»; las cantidades pendientes se restituyen (Arroz 10, Frijol 6); **Registrar recepción** vuelve a estar disponible |
| C11 | Pestaña «Pagos» de la misma compra | El pago de 20,00, el pagado, el saldo (54,00) y el estado de pago **no cambiaron** |
| C12 | Intenta cancelar la compra | Se permite cancelar solo si no hay pagos; con el pago de C3, el botón no se ofrece (la reversión de recepción no devuelve pagos) |
| C13 | Registra una nueva recepción de 10 kg de Arroz, y revierte esa recepción | Funciona igual; no hay límite de ciclos |
| C14 | Recepción de un producto **sin control de stock** (crea `PRUEBA-REV Bolsas` sin stock y una compra con él; recíbela) | En el diálogo la línea dice «Sin control de stock · sin entrada» y la reversión no genera movimientos (la lista de movimientos de la recepción queda vacía) |

## D. Restricciones por origen

| # | Paso | Resultado esperado |
|---|---|---|
| D1 | Ventas → crea un pedido con `PRUEBA-REV Arroz` y llévalo hasta **Entregado** (genera una salida por venta) | En Inventario → Movimientos aparece «Salida por venta» |
| D2 | Abre el detalle de esa salida | **Sin botón Revertir**; texto gris: «Las salidas por venta requieren una devolución, que aún no está disponible.» |
| D3 | Abre el detalle de una entrada que viene de una **recepción** (la de C2, p. ej. antes de revertirla) | **Sin botón Revertir**; texto gris: «Este movimiento proviene de una recepción: corrígelo desde la recepción en Compras.» |
| D4 | Fuerza la llamada directa (consola del navegador, estando logueado, o cliente de API con tu token): `POST /api/stock-movements/<id>/reverse/` con `{"reason":"x"}` sobre el movimiento de venta y sobre el de recepción | `409` con `code` `requires_return` y `reverse_from_origin`; nada cambia |
| D5 | Misma llamada sin cuerpo o con `{"reason":"   "}` sobre un ajuste confirmado | `400` con error en `reason` |
| D6 | Repite la reversión de un movimiento ya revertido (D4 sobre el original del A11) | `409` `already_reversed` |

## E. Estados y aspecto

| # | Paso | Resultado esperado |
|---|---|---|
| E1 | Mientras envías una reversión (botón pulsado) | El botón muestra «Revirtiendo…» y queda deshabilitado |
| E2 | Detén el backend y pulsa Revertir | El diálogo muestra un mensaje de error de conexión sin cerrarse ni perder el motivo |
| E3 | Detalle de movimiento, ajuste y recepción en **390 px** | Sin desbordes de la página; la tabla del diálogo de recepción puede desplazarse horizontalmente (observación Low conocida: la columna «Efecto» queda cortada, no es un defecto bloqueante). Los botones no se solapan |
| E4 | Las mismas pantallas y ambos diálogos en **1440 px** | Mismo orden y estilo que el resto del módulo (breadcrumb, `.card`, `dl`, botones); diálogo centrado y legible |
| E5 | Tema **oscuro** (Setting Panel → Dark) | Diálogos, alertas (azul/ámbar/rojo) y badges legibles; texto de ayuda gris visible |
| E6 | Teclado: abre el diálogo con Tab+Enter sobre «Revertir», escribe el motivo, Tab hasta el botón y Enter; Esc | El foco queda dentro del diálogo; Esc lo cierra sin revertir |
| E7 | Cierra sesión e inicia con **otra empresa** (otro usuario) y abre la URL de un movimiento/recepción de oleon | «Movimiento no encontrado.» / «No se encontró la compra o la recepción.» (404, sin filtrar datos) |

## F. Documental e Inventario deshabilitado

| # | Paso | Resultado esperado |
|---|---|---|
| F1 | Configuración → Módulos: **deshabilita Inventario**; registra una recepción nueva (queda *documental*) y ábrela | Aviso «Recepción documental, sin movimiento de inventario»; **Revertir recepción** disponible |
| F2 | Revierte esa recepción documental | Se revierte sin movimientos; estado «Revertida»; pendientes restituidos |
| F3 | Con Inventario aún deshabilitado, abre una recepción **antigua que movió stock** (la de C13 si la dejaste confirmada) | Sin botón Revertir; texto gris «Inventario está deshabilitado: habilítalo para revertir una recepción que movió existencias.» |
| F4 | Vuelve a habilitar Inventario | El botón Revertir reaparece en esa recepción |

## Limpieza

Los datos `PRUEBA-REV` no se pueden borrar desde la UI (movimientos y recepciones son inmutables): desactiva los productos, el almacén y el proveedor de prueba, y deja la política de stock negativo como la tenías.

## Qué reportar

Anota el paso (p. ej. «C6») y adjunta captura si algo difiere. Lo que falle y no sea la observación Low conocida de E3 se trata como hallazgo del PR.
