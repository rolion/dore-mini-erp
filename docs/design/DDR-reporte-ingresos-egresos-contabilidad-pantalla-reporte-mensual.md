# DDR-reporte-ingresos-egresos-contabilidad-pantalla-reporte-mensual: Pantalla «Ingresos y egresos»

**Estado:** Propuesto
**Task relacionado:** TASK-reporte-ingresos-egresos-contabilidad
**Fecha:** 2026-11-20

## Contexto
Contabilidad necesita ver, por mes de un período fiscal, cuánto ingresó, cuánto egresó y la utilidad. Es un reporte de solo lectura sobre el libro de asientos.

## Pantallas/flujos afectados
- Nueva: Contabilidad › Ingresos y egresos, ruta `/pocketbiz/accounting/income-expense` (`data.module = 'accounting'`), con entrada en el menú de Contabilidad junto a «Flujo de dinero».
- La persona entra, ve el período abierto actual con todos los meses, puede cambiar de período, elegir uno o más meses y ordenar por cualquier columna.

## Componentes/patrones elegidos
- Plantilla «Lista de solo lectura con filtros» (design-system sección 5): breadcrumb, `.card`, filtros en fila **encima de la tabla**, tabla Bootstrap simple (sin paginación: pocas filas) y error en `alert alert-danger` con «Reintentar».
- Filtros: **Período** (`form-select`, períodos fiscales; por defecto el actual) y **Mes** (`ng-select` múltiple de la plantilla Oreva, ya usada en el proyecto; vacío = «Todos los meses»). Los filtros viven en la URL (`period`, `months`). «Limpiar filtros» restablece mes a todos y período al actual.
- Tabla: columnas Mes, Ingreso, Egreso, Utilidad; importes con `MoneyPipe`, alineados a la derecha. Pie `tfoot` con **Total** de cada columna (los totales se calculan en el servidor sobre los meses filtrados).
- Orden: cabeceras como `button` dentro de `th` con `aria-sort` e icono de dirección; primer clic = mayor a menor, segundo = menor a mayor. Orden por defecto: cronológico (mes ascendente). Ordenar en cliente se justifica porque no hay paginación (desviación consciente de «sin ordenamiento en cliente»).
- Utilidad negativa: `text-danger` **y** etiqueta de texto «(pérdida)» (no solo color). La etiqueta de negocio es «Utilidad» por pedido explícito del usuario; la regla «Ganancia estimada» del módulo Reporting no aplica porque aquí la fuente es el libro de asientos, no una estimación.
- Estados: cargando (spinner), error con reintento, vacío «Sin períodos fiscales» (sin períodos) y «Sin movimientos en el período» (meses en 0 se muestran igualmente). Móvil: tabla con `table-responsive`; los filtros se apilan.

## Alternativas consideradas
- `ngx-datatable` con orden integrado: más pesado y la plantilla Bootstrap simple ya cubre pocas filas.
- Gráfico de barras: no pedido; fuera de alcance.

## Comportamiento por privilegio/estado
El frontend solo oculta el menú si el módulo está deshabilitado; el backend exige `required_modules = ('accounting',)` y filtra por la empresa del usuario autenticado. Un período de otra empresa responde 400/404.

## Consecuencias
Una pantalla nueva consistente con Saldos y Flujo de dinero. Deuda aceptada: orden en cliente solo para este reporte.
