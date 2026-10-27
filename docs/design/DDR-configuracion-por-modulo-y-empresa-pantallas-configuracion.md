# DDR-configuracion-por-modulo-y-empresa-pantallas-configuracion: Pantallas de Configuración por módulo

**Estado:** Propuesto
**Task relacionado:** TASK-configuracion-por-modulo-y-empresa
**Fecha:** 2026-10-27

## Contexto
El administrador necesita definir reglas por módulo (hoy solo Ventas tiene ajustes reales) y ver quién cambió qué. Cada pantalla de configuración tiene las pestañas «General» e «Historial de cambios». Compras e Inventario son placeholders sin reglas: no se muestran opciones futuras como disponibles.

## Pantallas/flujos afectados
1. **Menú lateral:** Ventas, Compras e Inventario pasan a ser submenús. Ventas: «Pedidos» (`/sales/orders`) y «Configuración» (`/sales/settings`). Compras: «Inicio» (`/purchases`, placeholder) y «Configuración» (`/purchases/settings`). Inventario: igual (`/inventory`, `/inventory/settings`). Los ítems siguen filtrados por módulo habilitado (`module`).
2. **Configuración de módulo** (`/sales/settings`, `/purchases/settings`, `/inventory/settings`): mismo componente `ModuleSettingsComponent` parametrizado por `data.settingsModule`.
3. **Configuración › Módulos** (`/settings/modules`, existente): se agrega la pestaña «Historial de cambios»; «General» es la lista actual (activación general).
4. **Aviso al salir con cambios sin guardar** (guard `canDeactivate` + `beforeunload`).

## Componentes/patrones elegidos
- **Formulario** (design-system §5, referencia `features/products/pages/product-form`): breadcrumb (`Ventas › Configuración`), `.card` con `card-header` (`h4` «Configuración de Ventas»), pestañas con `ngbNav` (ng-bootstrap, ya usado en el proyecto) «General» e «Historial de cambios». Desviación: el formulario vive dentro de una pestaña y se compone de filas de ajuste, no de campos sueltos.
- **Fila de ajuste (pestaña General):** por cada ajuste, `.form-group` con `label` asociado (etiqueta del ajuste), control (`form-select` para canal/método; `input type="number"` con sufijo «%» para el descuento), texto `<small class="form-text text-muted">` con la **descripción de su efecto**, `Valor predeterminado: …` (con botón de texto «Restablecer» que solo rellena el control, no guarda) y `<small class="form-text text-danger">` con el error del campo (cliente o servidor). El valor actual es el valor del control.
- **Compras e Inventario (General):** mensaje informativo (`alert alert-info`): «Este módulo aún no tiene ajustes configurables. Cuando haya reglas disponibles aparecerán aquí.» Sin controles ni botones de guardado; el Historial funciona y muestra «Sin cambios registrados.».
- **Acciones:** pie con `Guardar cambios` (`btn btn-primary`, `disabled` si el formulario no tiene cambios, es inválido o está guardando) y `Cancelar cambios` (`btn btn-light ms-2`, restablece el formulario al último valor guardado, `disabled` sin cambios). Éxito: toast «Configuración guardada». Error de campo: mensaje bajo el campo y los datos introducidos se conservan; error general: `alert alert-danger`.
- **Historial** (referencia `category-list`; tabla Bootstrap simple como el DDR de módulos): filtros en una fila (`Desde`, `Hasta` como `input type="date"` con `label`; `Ajuste` como `form-select` con «Todos»), botones `Filtrar`/`Limpiar`. Tabla (`<caption class="visually-hidden">`) con columnas **Fecha y hora** (`dd/MM/yyyy HH:mm`), **Usuario**, **Ajuste**, **Valor anterior**, **Valor nuevo**; paginación del servidor con `ngb-pagination` (ya disponible en ng-bootstrap). Estados: «Cargando…», «Sin cambios registrados.» (vacío), mensaje de error con «Reintentar». En móvil la tabla se apila por fila como la lista de módulos.
- **Aviso de salida:** al navegar con cambios sin guardar se usa `window.confirm` con «Hay cambios sin guardar. ¿Salir sin guardar?»; para cierre/recarga de pestaña, `beforeunload`. Se justifica no crear un diálogo propio: el aviso es secundario y estándar.
- Textos en español en `assets/i18n/es.json` (con en/de por consistencia con el menú).

## Alternativas consideradas
- **Pantalla única «Configuración» con una sección por módulo:** simplifica rutas, pero contradice «sección de configuración en cada módulo» y mezcla módulos deshabilitados. Descartada.
- **Guardar cada ajuste al cambiarlo (autoguardado):** descarta Cancelar y el aviso de salida pedidos. Descartada.
- **Historial como página separada:** más rutas; la historia pide pestaña. Descartada.
- **`ngx-datatable` en el historial:** infraestructura pesada para una tabla de 5 columnas; coherente con el DDR de módulos (tabla Bootstrap simple). Descartada.

## Comportamiento por privilegio/estado
- Solo el administrador de la empresa lee/guarda; el backend responde 403 a quien no lo sea (`CompanyAdminPermission`). El frontend no es la barrera: ocultar el menú o deshabilitar el formulario no sustituye la validación del servidor.
- Un módulo deshabilitado no muestra su submenú ni su ruta (`moduleGuard`); el servidor rechaza guardar ajustes de un módulo deshabilitado (409).
- Estados: cargando («Cargando…»), vacío (historial), error de validación por campo (400), error de servidor/red (mensaje + «Reintentar», conserva lo escrito), éxito (toast).
- Los ajustes nuevos aplican solo a documentos nuevos: la descripción de cada ajuste lo dice («Aplica a los descuentos que se registren desde ahora; los pedidos existentes no cambian.»).

## Consecuencias
Se actualiza `docs/design/design-system.md` (§5 «Formulario de configuración con pestañas» y §6 menú con submenús de Ventas, Compras e Inventario). Deuda: el aviso de salida usa `window.confirm`; la tabla de historial es Bootstrap simple y no `ngx-datatable`. La pantalla «Módulos» tendrá pestañas aunque solo la lista de módulos sea editable.
