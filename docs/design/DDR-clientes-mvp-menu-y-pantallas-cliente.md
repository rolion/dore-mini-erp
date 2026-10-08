# DDR-clientes-mvp-menu-y-pantallas-cliente: Menú "Cliente" y pantallas de cliente (lista, formulario, perfil con historial)

**Estado:** Propuesto
**Task relacionado:** TASK-clientes-mvp
**Fecha:** 2026-10-08

## Contexto
La investigación del task muestra que no existe ninguna pantalla de clientes y que el menú (`frontend/panel_admin/src/assets/data/routes.json`) tiene hoy "Dashboard" y "Catálogo ▸ Producto". El pedido es crear un menú llamado **Cliente** y cubrir REQ-CUS-001 a 006: crear, editar, buscar (nombre y teléfono), ver historial de compras, desactivar y advertir duplicados por teléfono. Ya existe un patrón completo y aprobado para un recurso análogo: [DDR-catalogo-productos-mvp-menu-y-pantallas-producto](DDR-catalogo-productos-mvp-menu-y-pantallas-producto.md) y la implementación en `frontend/panel_admin/src/app/features/products/pages/{product-list,product-form,product-detail}`. Este DDR reutiliza esas decisiones y solo diseña lo nuevo: la entrada de menú, la búsqueda por teléfono, la advertencia de duplicado y el historial. `ddd.md:1050-1060` fija `features/customers/{pages/customer-list,pages/customer-detail}`. La plantilla no tiene roles (ver DDR del catálogo): no hay variación por privilegio que diseñar.

## Pantallas/flujos afectados
1. **Menú lateral** (`layout/sidebar`): nueva entrada "Cliente".
2. **Lista de clientes** (`/customers`): buscar por nombre o teléfono, filtrar por estado (por defecto solo activos), ir a crear, ver, editar y activar/desactivar (REQ-CUS-003, 005).
3. **Formulario de cliente** (`/customers/new` y `/customers/:id/edit`): crear y editar nombre, teléfono, correo y notas; flujo de advertencia de duplicado al crear (REQ-CUS-001, 002, 006).
4. **Perfil/detalle de cliente** (`/customers/:id`): datos de contacto y notas de solo lectura, estado, acciones (editar, activar/desactivar) y sección **Historial de compras** con fecha, total y estado de cada pedido (REQ-CUS-004, 005).
5. **Creación rápida desde un pedido** (REQ-CUS-001, criterio 2): se define el comportamiento esperado pero **no se construye en este task**, porque no existe la pantalla de pedidos (`features/sales` no existe). Ver "Consecuencias".

No se diseñan pantallas de pedidos, fusión de duplicados, importación, etiquetas, segmentación ni eliminación: el objetivo del requisito excluye explícitamente un CRM complejo y REQ-CUS-005 prohíbe borrar clientes con ventas (no hay botón "Eliminar").

## Componentes/patrones elegidos

**Menú** — mismo mecanismo (`routes.json` + claves `MENUITEMS.*` en `assets/i18n/{en,es,de}.json`). Entrada de primer nivel **directa** "Cliente" (`class: ""`, `path: "/customers"`, icono feather `users`, sin submenú), igual que "Dashboard" (`routes.json:3-13`). Clave nueva `MENUITEMS.CUSTOMER.TEXT` = "Cliente" (es), "Customer" (en), "Kunde" (de).

**Lista** — copia estructural de `product-list.component.html`: `ngx-datatable class="material"` con paginación externa, cabecera con buscador `table-search-area` + `select` de estado + botón redondo "+" (`btn-primary rounded-button`), breadcrumb `Cliente`. Cambios respecto a productos:
- Buscador con placeholder "Buscar por nombre o teléfono" (un solo campo, con debounce como en productos).
- Columnas: Nombre (enlace al perfil), Teléfono, Correo, Estado, Acciones. Teléfono y correo vacíos se muestran como "—".
- Filtro de estado con **"Activos" preseleccionado** (Activos / Inactivos / Todos), a diferencia de productos donde el predeterminado es "Todos": REQ-CUS-005 pide que el desactivado no aparezca por defecto.
- Estado con `badge-outline col-green` / `col-red`; acciones Ver / Editar / Desactivar-Activar con los mismos colores e iconos que productos (ver `product-list.component.scss`).
- Confirmación con `sweetalert2` al desactivar (texto: "El cliente dejará de aparecer entre los activos. Su historial de pedidos se conserva.") y avisos con `ngx-toastr`.
- Estado vacío: "No hay clientes que coincidan." / "Aún no hay clientes."

**Formulario** — copia estructural de `product-form.component.html` (`main-content` → breadcrumb → `card`, `form-control`, `*` rojo, `small.form-text.text-danger`, botón Guardar deshabilitado si inválido o enviando, Cancelar). Campos: Nombre (obligatorio), Teléfono (texto, `inputmode="tel"`, ayuda: "Se guardará normalizado, p. ej. +591 7xxxxxxx"), Correo (`type="email"`, opcional), Notas (`textarea`). En alta no hay campo de estado (nace activo); el estado solo cambia con activar/desactivar. Errores del servidor se muestran bajo su campo.

**Advertencia de duplicado (REQ-CUS-006)** — se resuelve **al enviar** el alta: si el servidor indica que ya existe un cliente con el mismo teléfono normalizado, se abre un diálogo `sweetalert2` (patrón ya usado para confirmaciones) con el título "Ya existe un cliente con este teléfono", la lista de coincidencias (nombre y estado, cada una con enlace a su perfil) y dos botones: **"Crear de todos modos"** (reenvía confirmando) y **"Cancelar"** (vuelve al formulario con los datos intactos). No bloquea. El contrato exacto (cómo el servidor devuelve las coincidencias y cómo se confirma) lo define `delivery-architect`.

**Perfil/detalle** — copia estructural de `product-detail.component.html` (`card` con `dl.row`): nombre, teléfono, correo, notas, estado (badge), creado, última actualización; botones "Editar", "Activar/Desactivar" y "Volver". Debajo, una segunda `card` **"Historial de compras"** con una tabla Bootstrap simple (`table`, no `ngx-datatable`: es una lista corta de solo lectura dentro de otra página) con columnas **Fecha, Total, Estado**, orden del más reciente al más antiguo. Sin enlaces a cada pedido (no existe pantalla de pedido). Mientras no haya pedidos o Sales no exista: mensaje "Este cliente aún no tiene pedidos." Si el cliente está inactivo, el historial se muestra igual (REQ-CUS-005).

## Alternativas consideradas
- **Menú: entrada directa "Cliente" vs. grupo "Cliente ▸ Clientes".** El grupo imita "Catálogo ▸ Producto", pero Catálogo agrupa varias entidades futuras y Cliente tiene una sola pantalla de entrada; un submenú de un único ítem añade un clic sin aportar. El pedido literal ("un menú llamado Cliente") también encaja con la entrada directa. **Se elige entrada directa.** Si luego se agregan más pantallas del módulo, se convierte en grupo.
- **Alta/edición en modal vs. página propia.** Se mantiene lo decidido en el DDR del catálogo (URL navegable, formulario tipado, sin modal sobrecargado). **Página.** La creación rápida desde pedido sí será modal, pero se diseña con Sales.
- **Duplicado: advertencia inline mientras se escribe el teléfono vs. diálogo al enviar.** Lo inline avisa antes pero exige una consulta al servidor por cada cambio de teléfono, normalizar en el cliente para comparar y mantener un estado visual extra; además el servidor igual debe verificar al guardar (la fuente de verdad). El diálogo al enviar cubre el criterio de aceptación ("advertencia antes de crear otro cliente"), usa el patrón `Swal` existente y no duplica reglas en el frontend. **Diálogo al enviar.** (Un aviso inline queda como mejora posible.)
- **Duplicado: bloquear con error de validación.** Contradice REQ-CUS-006 (no necesariamente bloquea). Descartado.
- **Historial: pestaña vs. sección en la misma página.** Con solo tres columnas y sin acciones, una pestaña añade navegación sin beneficio; sección en el perfil. Tabla Bootstrap simple vs. `ngx-datatable`: se elige tabla simple (menos peso y sin paginación propia; si el historial crece mucho, paginación queda para después).
- **Filtro de estado predeterminado "Todos" (como productos) vs. "Activos".** REQ-CUS-005 exige que el desactivado no aparezca por defecto: "Activos".
- **Un campo de búsqueda vs. dos (nombre y teléfono).** Un solo campo es más rápido durante la venta (REQ-CUS-003, "búsqueda rápida"); el servidor decide si la entrada coincide con nombre o teléfono. Descartados dos campos.

## Comportamiento por privilegio/estado
- **Privilegios:** no existen roles; todo usuario autenticado ve y hace todo. Esto es solo UX: la verificación real corresponde al backend (`IsAuthenticated` por defecto, `backend/config/settings/base.py:75-77`) y a `delivery-architect` si se quisiera algo más fino. El frontend no es la barrera de seguridad.
- **Cliente inactivo:** badge rojo, botón "Activar", sigue visible en el perfil con su historial y editable. No aparece en la lista salvo que el filtro sea "Inactivos" o "Todos".
- **Estados de pantalla:** lista con `loadingIndicator`; vacío con mensaje; error de red con `toastr`; guardar deshabilitado mientras es inválido o se envía; cliente inexistente en perfil/edición → aviso y retorno a la lista; errores de validación del servidor bajo el campo; error al cargar el historial no impide ver los datos del cliente (aviso en la tarjeta del historial).
- **Textos:** contenido de pantallas en español; solo el menú pasa por `translate` (igual que Catálogo).

## Consecuencias
- Más simple: reutiliza `ngx-datatable`, `Swal`, `toastr` y las pantallas de `features/products` como molde; sin nuevas dependencias de UI; menú de una sola entrada.
- Deuda aceptada: los estilos de acciones de tabla (`btn-tbl-view/update/toggle`) viven en el SCSS de `product-list`; clientes los necesita iguales. Duplicarlos es lo más rápido pero genera inconsistencia futura; extraerlos a un estilo compartido es decisión de plan. El menú está en tres idiomas y las pantallas solo en español (igual que Catálogo).
- **Historial y asociación a pedido dependen de Sales** (no existe). El perfil muestra la sección con su estado vacío, pero qué fuente la alimenta y si hoy se oculta o se muestra vacía lo cierra `delivery-architect`/`delivery-plan`. La **creación rápida desde un pedido** (modal con nombre y teléfono, mismo diálogo de duplicado, devuelve el cliente creado al selector del pedido) queda diseñada aquí como intención y se implementará cuando exista `features/sales`; hasta entonces el criterio "se asocia inmediatamente a un pedido" no es verificable en la UI.
- Pendiente para arquitectura (no se decide aquí): normalización del teléfono y librería (dependencia nueva), contrato de duplicado (respuesta y confirmación), si la comparación también aplica al editar el teléfono, fuente del historial desde Sales sin invertir dependencias, longitudes máximas, validación de correo, endpoints `activate`/`deactivate` y filtros de búsqueda por nombre/teléfono.
