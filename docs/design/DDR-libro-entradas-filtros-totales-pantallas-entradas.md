# DDR-libro-entradas-filtros-totales-pantallas-entradas: Pantallas Contabilidad → Entradas (lista y detalle)

**Estado:** Propuesto
**Task relacionado:** TASK-libro-entradas-filtros-totales
**Fecha:** 2026-11-14

## Contexto
El administrador necesita ver el dinero efectivamente cobrado (productos y servicios) en un libro común, filtrarlo y ver totales de todo el conjunto filtrado. No es un saldo bancario ni una utilidad, y la pantalla debe decirlo.

## Pantallas/flujos afectados
- **Lista** `/pocketbiz/accounting/entries` (menú Contabilidad → Entradas, solo admin, módulo `accounting`).
- **Detalle** `/pocketbiz/accounting/entries/:id`.
- Sin alta, edición ni borrado: no hay botones «+», Editar ni Eliminar.

## Componentes/patrones elegidos
- **Lista:** «Lista de solo lectura con filtros» (design-system §5, referencia `features/inventory/pages/movement-list`): breadcrumb, `.card`, filtros en fila (Desde, Hasta, Cuenta, Método, Origen; «Limpiar filtros»), `ngx-datatable` con paginación del servidor, error en `alert alert-danger` con «Reintentar». Los filtros viven en la URL (query params) como en `purchase-list`, para volver desde el detalle sin perderlos (sin servicio de estado nuevo).
- **Totales** (nuevo bloque dentro del patrón de reportes, `app-report-card` no se reutiliza porque son varias monedas): sobre la tabla, un recuadro «Totales del filtro» con una fila por **moneda** (moneda, N.º de entradas, **Total**, y debajo «Productos Bs X · Servicios Bs Y»). Importes con `MoneyPipe` (a la derecha). Una moneda sin entradas en el filtro no aparece; sin ninguna: «Sin registros». Nunca se suman monedas distintas.
- **Periodo y cobertura:** línea `small.text-muted` bajo el título: «Periodo: dd/MM/yyyy – dd/MM/yyyy» (los filtros, o «Todas las fechas») y «Cobertura del libro: desde dd/MM/yyyy hasta dd/MM/yyyy (fecha del pago). Los cobros anteriores al registro no aparecen hasta regularizarlos.» Libro vacío: «Aún no hay entradas registradas».
- **Texto de contexto** fijo (`alert alert-info`): «Cobros recibidos. No es saldo de cuenta, utilidad ni devengamiento.»
- **Columnas:** Fecha del pago, Cuenta, Método, Origen (badge de texto: Productos azul / Servicios verde), Documento (enlace o texto), Comprobante (CB-NNNNNN o «—»), Monto (derecha, con moneda), Registrada por. Tabla apilada en móvil.
- **Detalle:** plantilla Detalle (`.card`, `h4`, `dl.row`): monto y moneda en cabecera, cuenta, método, fecha del pago, fecha de registro, usuario, origen con enlace al pedido o comprobante cuando corresponda, ID del pago de origen. Botón «Volver» (`btn-light`). Sin acciones de ciclo de vida; texto `small.text-muted` «Las entradas no se editan ni se eliminan».
- **Enlace al origen:** solo si el servidor indica `source.available` (módulo propietario habilitado) y existe pantalla: productos → `/pocketbiz/sales/orders` (detalle del pedido por id si la ruta existe; si no, se muestra el texto); servicios → `/pocketbiz/receivables/:kind/:number`. Si no está disponible se muestra el texto «Documento X (módulo deshabilitado)» sin enlace.
- Estados: cargando (spinner/«Cargando…»), vacío (con y sin filtros: sin filtros, mensaje de «aún no hay…»; con filtros, badge por filtro activo + «Limpiar filtros»), error con «Reintentar», éxito (datos). Rango inválido (Desde > Hasta): mensaje bajo los filtros y no se consulta.
- Todo el texto vía `translate` en es/en/pt.

## Alternativas consideradas
- **Totales por página en la tabla (`ngx-datatable` summary):** incumple el criterio (todo el filtro); descartado.
- **Selector de moneda único:** oculta monedas; se prefiere una fila por moneda.
- **Ítem de menú dentro de «Configuración»:** las entradas no son configuración; se añade como segundo ítem de Contabilidad junto a «Cuentas y Métodos de pago».
- **Servicio en memoria para conservar filtros** (`StockFiltersState`): la URL ya cubre el caso con menos código.

## Comportamiento por privilegio/estado
Solo administrador de empresa (ítem `adminOnly`, ruta con `moduleGuard('accounting')`). **El frontend no es la barrera:** el backend aplica `CompanyAdminPermission`, `required_modules=('accounting',)`, empresa del usuario y 404 para detalles ajenos; `source.available` también lo decide el servidor. No se exponen notas ni datos clínicos.

## Consecuencias
Se introduce un bloque «Totales por moneda» reutilizable por futuros reportes; se propone añadirlo a `docs/design/design-system.md` §5 (variante de lista de solo lectura con totales por moneda) y el ítem Entradas a §6. Deuda aceptada: sin exportación a CSV ni gráficos en esta entrega.
