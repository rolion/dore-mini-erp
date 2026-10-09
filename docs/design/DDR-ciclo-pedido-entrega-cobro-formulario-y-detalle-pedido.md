# DDR-ciclo-pedido-entrega-cobro-formulario-y-detalle-pedido: Alta/edición de pedido, detalle con ítems, estados, cancelación y pagos

**Estado:** Propuesto
**Task relacionado:** TASK-ciclo-pedido-entrega-cobro
**Fecha:** 2026-10-08

## Contexto
REQ-SAL-001 a 016 piden crear un pedido (cliente opcional, canal, fecha, entrega prevista opcional, notas), agregar/cambiar/quitar ítems de productos activos con snapshot de nombre y precio, aplicar un descuento, ver subtotal/total calculados (no editables), avanzar el estado (NEW → IN_PREPARATION → READY → DELIVERED), cancelar con motivo, registrar pagos parciales y ver saldo, con **entrega y pago como ejes independientes**. Hoy no existe `features/sales`. Ya hay moldes aprobados para formulario y perfil: `features/customers/pages/customer-form`, `customer-detail` (`card` + `dl.row`) y el DDR [DDR-clientes-mvp-menu-y-pantallas-cliente](DDR-clientes-mvp-menu-y-pantallas-cliente.md), que dejó diseñada la **creación rápida de cliente desde un pedido** y la sección de historial. La lista y el menú están en [DDR-ciclo-pedido-entrega-cobro-menu-y-lista-pedidos](DDR-ciclo-pedido-entrega-cobro-menu-y-lista-pedidos.md). La investigación dejó abiertas ambigüedades del modelo de estados ("confirmar", "editable", transiciones): este DDR diseña la pantalla para que **no dependa de la respuesta**, mostrando en cada momento solo las acciones que el servidor declare disponibles (ver "Comportamiento por estado").

## Pantallas/flujos afectados
1. **Formulario de pedido** (`/sales/orders/new` y `/sales/orders/:id/edit`): datos del pedido (cliente, canal, fecha de pedido, entrega prevista, notas). No incluye ítems, descuento ni pagos.
2. **Detalle del pedido** (`/sales/orders/:id`): es la pantalla de trabajo. Resumen de los dos ejes (entrega y cobro), datos, **ítems** (agregar, cambiar cantidad, quitar), **importes** (subtotal, descuento, total, pagado, saldo), **pagos** (registrar, listar) y **acciones de estado** (avanzar, entregar, cancelar). Cubre REQ-SAL-002 a 006, 008 a 013, 015 y 016.
3. **Selector de cliente con creación rápida** (dentro del formulario): buscar un cliente o crear uno sin salir del pedido (REQ-CUS-001, criterio 2, diseñado en el DDR de clientes).
4. **Sección "Historial de compras" del perfil de cliente**: pasa de estado vacío a mostrar pedidos reales con enlace al detalle.

No se diseñan: reembolsos (no hay REQ que los defina), anulación de pagos, edición de un pago, impresión/PDF de comprobante, duplicar pedido, ni pantallas de reportes.

## Componentes/patrones elegidos

**Formulario de pedido** — copia estructural de `customer-form.component.html` (`main-content` → breadcrumb → `card`, `form-control`, `*` rojo, `small.form-text.text-danger`, Guardar deshabilitado si inválido o enviando, Cancelar), Reactive Forms tipados. Campos:
- **Cliente** (opcional): `ng-select` con búsqueda remota por nombre/teléfono sobre clientes **activos** (patrón `src/app/forms/select-item`), con opción vacía "Sin cliente (venta de mostrador)" y, en el pie de la lista, la acción **"+ Nuevo cliente"** que abre la creación rápida.
- **Canal de venta** (obligatorio): `select` con WhatsApp, Facebook, Instagram, Venta directa, Feria, Otro.
- **Fecha del pedido** (obligatorio): `input type="date"`, valor inicial hoy.
- **Entrega prevista** (opcional): `input type="date"`; ayuda "Puede completarla después".
- **Notas** (opcional): `textarea`.
- Al guardar el alta, la UI navega al **detalle** del pedido recién creado, donde se agregan los productos (igual que clientes navega al perfil tras crear). Errores del servidor se muestran bajo su campo.

**Creación rápida de cliente** — modal de `NgbModal` (ng-bootstrap ya instalado y usado en `ui/modals` y `advance-table`) con Nombre (obligatorio) y Teléfono (opcional). Reutiliza el diálogo `Swal` de duplicado de Clientes ("Ya existe un cliente con este teléfono", con "Crear de todos modos" / "Cancelar") y, al guardar, entrega el cliente creado al selector ya seleccionado. El componente vive en `features/customers/components/` y `sales` lo consume por su selector (borde entre features a resolver en plan/arquitectura). **Es separable:** si el plan parte el trabajo, el pedido funciona sin creación rápida (el usuario crea el cliente desde el menú Cliente).

**Detalle** — `main-content` → breadcrumb `Pedidos ▸ Pedido`, y tarjetas en este orden:
1. **Cabecera de ejes** (dos tarjetas lado a lado, `col-md-6`, que apilan en móvil), cada una con título propio para no mezclarlos:
   - **Entrega:** badge de estado con `fa-truck`, entrega prevista y, si está entregado, entrega real.
   - **Cobro:** badge de pago con `fa-coins`, "Pagado Bs X de Bs Y" y **Saldo** en grande (rojo si > 0, verde "Sin saldo" si = 0).
   Debajo de ambas, una **banda de alerta** solo cuando aporta información: `alert-warning` "Entregado con saldo pendiente de Bs X" (entregado, saldo > 0), `alert-info` "Pagado, pendiente de entrega" (pagado y no entregado ni cancelado), `alert-danger` "Pedido cancelado — Motivo: …" con "Los pagos registrados se conservan" si hay pagos. Estos tres mensajes son la representación explícita de REQ-SAL-016.
2. **Datos del pedido** (`dl.row`, como `customer-detail`): cliente (enlace a su perfil o "Sin cliente"), canal, fecha del pedido, notas, creado/actualizado. Botón "Editar datos" (lleva al formulario).
3. **Productos del pedido** (tabla Bootstrap `table`, no `ngx-datatable`: lista corta dentro de una página de trabajo, mismo criterio que el historial del perfil): columnas Producto (snapshot), Precio unitario, Cantidad, Subtotal, Quitar. Con el pedido editable:
   - **Fila de alta** encima de la tabla: `ng-select` de productos **activos** con búsqueda remota (muestra nombre y precio), campo cantidad (`input type="number" min="1"`, valor inicial 1) y botón "Agregar". Los productos inactivos no se ofrecen; si el servidor igual los rechaza, el error se muestra bajo el selector.
   - **Cantidad editable en la fila** (`input number`, aplica al salir del campo o con Enter, con indicador "guardando"); el subtotal y los totales se **actualizan con la respuesta del servidor**, nunca los calcula el navegador.
   - Quitar con botón `fa-trash`, con `Swal` de confirmación; si es el último ítem de un pedido que ya no puede quedar vacío, el botón se deshabilita con tooltip "Un pedido confirmado debe tener al menos un producto" (el servidor es quien valida).
   - Con el pedido no editable, la fila de alta y los controles desaparecen y la tabla queda de solo lectura (no se deshabilita visualmente, para no sugerir que podría activarse).
   - Vacío: "Agregue al menos un producto para poder avanzar el pedido." con el selector enfocado.
4. **Importes** (tarjeta con `dl.row` alineada a la derecha): Subtotal, **Descuento** (monto en `Bs`, campo con botón "Aplicar" mientras sea editable; al aplicar un descuento mayor al subtotal se muestra el error del servidor bajo el campo), **Total** (solo texto, nunca un input: REQ-SAL-005), Pagado, **Saldo**.
5. **Pagos:** tabla (Fecha, Método, Referencia, Monto) más total pagado; botón "Registrar pago" que despliega **en la misma tarjeta** una fila de formulario (Monto, Método `select` Efectivo/QR/Transferencia/Tarjeta/Otro, Fecha `input type="date"` hoy por defecto, Referencia opcional) con "Registrar" y "Cancelar". Se prefiere inline a modal porque el usuario necesita ver el saldo mientras escribe el monto; el campo Monto muestra como ayuda "Saldo: Bs X". Tras registrar, los dos paneles de cabecera y los importes se actualizan con la respuesta del servidor. Vacío: "Aún no hay pagos registrados."
6. **Barra de acciones** (fija arriba de la tarjeta de ejes, a la derecha): una **acción principal** (`btn-primary`) que depende del estado ("Iniciar preparación", "Marcar listo", "Marcar entregado"), la secundaria **"Cancelar pedido"** (`btn-outline-danger`) y "Volver a pedidos". El texto exacto de la primera acción (y si existe un paso explícito "Confirmar pedido") depende de la Specification (ver Pendiente).
   - **Marcar entregado:** `Swal` con confirmación y la **fecha real de entrega** (`input date`, hoy por defecto, editable por si la entrega se registra con retraso). Si hay saldo pendiente, el diálogo lo menciona ("Quedará un saldo de Bs X por cobrar") pero **no bloquea** (DELIVERED ≠ PAID).
   - **Cancelar pedido:** `Swal` con `textarea` "Motivo de la cancelación" **obligatorio** (no se puede confirmar vacío) y texto "Los pagos registrados no se eliminan".

**Historial de compras en el perfil de cliente** (`features/customers/components/customer-purchase-history`) — se conecta a Sales: cada fila pasa a enlazar al detalle del pedido y se agrega la columna Pago junto a Estado (si el contrato de arquitectura lo expone). Se mantiene la tabla Bootstrap simple, orden del más reciente al más antiguo y el vacío "Este cliente aún no tiene pedidos." Esto actualiza el DDR de clientes, que decía "sin enlaces a cada pedido (no existe pantalla de pedido)".

## Alternativas consideradas
- **Pedido en un solo formulario con ítems incluidos vs. alta de datos + gestión de ítems en el detalle.** Un formulario único replica en el navegador las reglas de subtotal/total/descuento (CLAUDE.md las ubica en el dominio) o muestra totales que podrían no coincidir con el servidor, y complica la edición de pedidos existentes. Separar permite que **cada cambio de ítem devuelva los importes calculados por el servidor** y es coherente con los endpoints de `ddd.md:949-950`. Costo: un paso más al crear. **Datos primero, ítems en el detalle.**
- **Asistente por pasos (wizard) vs. dos páginas.** El flujo tiene solo dos momentos (datos, productos) y navegación por URL; un wizard añade estado y no aporta. **Descartado.**
- **Registrar pago en modal vs. inline.** El modal oculta el saldo y el listado de pagos mientras se escribe. **Inline.**
- **Tabla de ítems con `ngx-datatable` vs. tabla Bootstrap simple.** Los ítems son pocos, editables en la fila y sin paginación; `ngx-datatable` es para listas paginadas. **Tabla Bootstrap**, como el historial del perfil.
- **Edición de cantidad con botones +/− vs. campo numérico.** Los botones evitan teclear, pero los pedidos pueden tener cantidades grandes (packs) y el requisito habla de "cantidad final". **Campo numérico**; +/− queda como mejora.
- **Una sola barra de estado en línea de tiempo (stepper NEW → … → DELIVERED) vs. dos paneles Entrega/Cobro.** Un stepper único mezclaría pago y logística, contra REQ-SAL-016. Un stepper solo del eje de entrega sería agradable pero repite la información del badge; **dos paneles**, stepper como mejora posible.
- **Cancelar con diálogo `Swal` + textarea vs. página/modal propio.** El motivo es un solo campo; el `Swal` con `input: 'textarea'` ya es el patrón de confirmación de la app. **`Swal`.**
- **Creación rápida de cliente en modal vs. enviar al usuario al menú Cliente.** Salir del pedido pierde el contexto durante la venta (REQ-CUS-001); el modal es mínimo (nombre y teléfono). **Modal**, pero separable.
- **Confirmar con botón "Confirmar pedido" explícito vs. solo avanzar de estado.** No se decide aquí porque depende de si "confirmar" es una transición o un indicador (investigación). El diseño reserva el lugar de la **acción principal**; ver Pendiente.

## Comportamiento por privilegio/estado
- **Privilegios:** no existen roles; todo usuario autenticado ve y hace todo. Esto es solo UX: **la aplicación real de las reglas (qué transiciones, ediciones y pagos se permiten) la hace el backend; el frontend no es la barrera de seguridad.**
- **Acciones según el servidor, no según el navegador:** la UI no replica la tabla de transiciones. Muestra los botones que el pedido declare disponibles y trata cualquier 400/409 como mensaje al usuario. Requiere que arquitectura defina cómo el pedido expone qué puede hacerse (p. ej. si es editable y qué acciones de estado, de pago y de cancelación están disponibles); se pide como **requisito de contrato**.
- **Propuesta visual por estado** (sujeta a la tabla de transiciones de la Specification):

  | Estado | Datos / ítems / descuento | Acción principal | Cancelar | Registrar pago |
  |---|---|---|---|---|
  | NEW | editables | Iniciar preparación | sí | sí |
  | IN_PREPARATION | según Specification | Marcar listo | sí | sí |
  | READY | solo lectura | Marcar entregado | sí | sí |
  | DELIVERED | solo lectura | — | no | sí (puede haber saldo) |
  | CANCELLED | solo lectura + motivo | — | — | según Specification (los pagos existentes siguen visibles) |

  Un botón no disponible **no se muestra** (en lugar de aparecer deshabilitado), salvo "Quitar" del último ítem, donde se explica el motivo con tooltip.
- **Fecha prevista de entrega:** editable en el formulario mientras el pedido siga abierto; el enlace "Editar datos" se oculta cuando no lo es.
- **Estados de pantalla:** carga con "Cargando…"; pedido inexistente → aviso y retorno a la lista; cada mutación (agregar, cantidad, quitar, descuento, pago, estado, cancelación) deshabilita su botón mientras se envía y refresca el pedido con la respuesta del servidor; errores de validación bajo su campo, errores de regla de negocio (p. ej. pago mayor al saldo, transición inválida) en `toastr`/`alert` junto a la acción; si el pedido cambió mientras se editaba (409), se recarga y se avisa.
- **Importes:** todo importe se muestra tal como lo devuelve el servidor (string decimal) con formato `Bs 0.00`; el navegador no suma, no multiplica ni redondea (REQ-SAL-005, regla de `Decimal`).
- **Textos:** contenido de pantallas en español; solo el menú pasa por `translate`.

## Consecuencias
- Más simple: la pantalla no duplica reglas del dominio; `ng-select`, `NgbModal`, `Swal`, `toastr`, `input type="date"` y tablas Bootstrap ya están en la plantilla; sin dependencias nuevas de UI.
- Costo aceptado: crear un pedido son dos momentos (datos, luego productos); más llamadas al servidor (una por cambio de ítem).
- **Pendiente para arquitectura / Specification (no se decide aquí):**
  1. Significado de "confirmar" y si hay un estado/indicador para ello (define la acción principal de NEW).
  2. Qué estados permiten editar datos, ítems y descuento; transiciones permitidas y si se puede cancelar un pedido entregado.
  3. Contrato del pedido: importes ya calculados (subtotal, descuento, total, pagado, saldo), `payment_status`, qué acciones están disponibles, `delivered_at`, `cancellation_reason`; contrato de cada mutación (ítems, descuento, estado, cancelar, pago) y de errores.
  4. Registro de pago en pedido cancelado, sobrepago, qué es REFUNDED y cómo se llega a él (no hay REQ de reembolso; el DDR no diseña esa acción).
  5. Fecha real de entrega (¿editable al entregar?) y si las fechas de pedido/pago admiten pasado o futuro.
  6. Servicios de consulta a Catalog (producto activo, snapshot) y Customers (cliente activo), y el borde de `features/` para el componente de creación rápida.
  7. Cómo se identifica un pedido a ojos del usuario (código legible).
- Deuda de consistencia: el DDR de clientes queda parcialmente reemplazado en su sección "Historial" (sin enlaces) y "Creación rápida" (ahora definida aquí); no se modifica ese DDR, este documento lo extiende. Mejoras posibles después: stepper del eje de entrega, +/− en cantidad, acciones rápidas en la lista, tablero de cobros.
