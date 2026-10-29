# DDR-gestionar-proveedores-pantallas-proveedores: Lista, formulario y detalle de proveedores

**Estado:** Propuesto
**Task relacionado:** TASK-gestionar-proveedores
**Fecha:** 2026-10-29

## Contexto
PB-COM-001 pide gestionar proveedores bajo Compras → Proveedores. El sistema de diseño ya define plantillas de lista, formulario y detalle (`docs/design/design-system.md` §5) implementadas para clientes y productos; no se necesita un patrón nuevo.

## Pantallas/flujos afectados
- **Menú**: el submenú de Compras pasa a «Inicio», «Proveedores» (`/pocketbiz/purchases/suppliers`) y «Configuración». Texto `MENUITEMS.PURCHASES.LIST.SUPPLIERS` en es/en/de (`es`: «Proveedores»).
- **Lista** `/purchases/suppliers`.
- **Formulario** `/purchases/suppliers/new` y `/purchases/suppliers/:id/edit`.
- **Detalle** `/purchases/suppliers/:id`.
- «Ver compras» navega a `/purchases?supplierId=<id>` (hoy «Próximamente»; el listado real llega con la task de Compras).

## Componentes/patrones elegidos
Plantillas del sistema, referencia `features/customers/pages/*`:
- **Lista** (§5 Lista): buscador «Buscar por nombre o identificación» (debounce), filtro de estado con **Activos** preseleccionado (Activos / Inactivos / Todos), botón «+ Nuevo proveedor». `ngx-datatable` con columnas Nombre (enlace al detalle), Identificación, Teléfono, Correo, Estado (badge) y Acciones (ver, editar, activar/desactivar, ver compras). Vacío: «No hay proveedores que coincidan». Datos faltantes: «—». Paginación en servidor.
- **Formulario** (§5 Formulario): Reactive Form tipado; Nombre*, Identificación, Teléfono, Correo, Notas; errores del servidor bajo cada campo; correo inválido marcado en el campo. Guardar (primario) y Cancelar (`btn-light`) → detalle (edición) o lista (alta). El estado no es editable.
- **Detalle** (§5 Detalle): `dl` con nombre, identificación, teléfono, correo, notas, estado (badge), creado/actualizado (`dd/MM/yyyy HH:mm`), «Sin …» si no hay dato. Acciones: Editar, Activar/Desactivar, Ver compras, Volver. Un proveedor inactivo se ve igual, con badge «Inactivo».
- **Confirmación de desactivar** (SweetAlert2, como clientes): «¿Quieres desactivar a "X"? Dejará de ofrecerse en compras nuevas. Sus compras históricas se conservan.» Activar pide la misma confirmación en versión corta.
- Colores/iconos de acciones iguales a clientes (Ver `#6777ef`, Editar `#ffc107`, Activar/Desactivar `#dc3545`); «Ver compras» usa el icono `shopping-bag`.

## Alternativas consideradas
1. Reutilizar componentes de `features/customers` (compartir): descartado, ADR de clientes establece features independientes y la duplicación de estilos es deuda ya registrada.
2. Mostrar el historial de compras embebido en el detalle: descartado, el requerimiento lo resuelve con el listado de Compras filtrado.

## Comportamiento por privilegio/estado
- Estados: cargando (`loadingIndicator`), vacío, error de red (`toastr`), 404 → aviso y retorno a la lista, errores de campo del servidor.
- Solo el administrador de la empresa accede (rol único hoy). El frontend oculta el menú/ruta si el módulo `purchases` está deshabilitado (`moduleGuard`), pero **la barrera real es el backend**: `required_modules=('purchases',)`, `CompanyModulePermission` y filtro por `company_id`.

## Consecuencias
Se suma un cuarto feature con lista/forma/detalle casi idénticos a clientes (duplicación aceptada). No hay pantalla de compras todavía: «Ver compras» aterriza en «Próximamente» hasta la task de Compras.
