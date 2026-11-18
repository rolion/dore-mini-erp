# DDR-mostrar-sumas-saldos-cuentas-contables-pantalla-saldos: Pantalla Contabilidad › Saldos

**Estado:** Propuesto
**Task relacionado:** TASK-mostrar-sumas-saldos-cuentas-contables
**Fecha:** 2026-11-16

## Contexto
`Contabilidad › Saldos` (`/pocketbiz/accounting/balances`) es hoy un «Próximamente». Debe mostrar sumas y saldos de todas las cuentas del plan, con filtros y acceso a los movimientos de cada cuenta.

## Pantallas/flujos afectados
Solo `balances-page` (se reemplaza el contenido). Enlaza a `journal-list` (Movimientos) con `account_id`, `date_from`, `date_to` en la URL.

## Componentes/patrones elegidos
Plantilla **Lista de solo lectura con filtros** (`design-system.md` §5, ref. `movement-list`) con el selector de período del patrón de reportes:
- Breadcrumb y `.card` como las demás pantallas de Contabilidad.
- Filtros en fila: **Período fiscal** (`form-select`, opcional; al elegirlo rellena Desde/Hasta), **Desde** y **Hasta** (`input type=date`), **Clasificación** (`form-select`: Todas + las seis), **Cuenta** (`form-select`: Todas + cuentas del plan, activas y deshabilitadas) y «Limpiar filtros». Los filtros viven en la URL (se pueden compartir y recargar).
- Tabla (`ngx-datatable`, sin paginación del servidor ni orden en cliente, como el plan de cuentas): **Código**, **Cuenta** (enlace a Movimientos filtrado por esa cuenta y el mismo rango), **Clasificación**, **Total Debe**, **Total Haber**, **Saldo deudor**, **Saldo acreedor**. Importes alineados a la derecha, con «0,00» en lo que no tiene valor (nunca vacío). Con **Desde** informado se insertan **Saldo inicial deudor** y **Saldo inicial acreedor** antes de Debe/Haber; Debe/Haber son entonces los del rango y los saldos deudor/acreedor son los finales acumulados.
- Pie de tabla fijo con la fila **Totales** (suma de lo mostrado) y un badge de texto «Cuadra» (verde) / «No cuadra» (rojo) cuando total Debe = total Haber y total deudor = total acreedor (nunca solo color).
- Cuenta deshabilitada: badge gris «Deshabilitada» junto al nombre; cuenta sin clasificación: «Sin clasificar» gris; sin código: «—».
- Textos de apoyo en `<small class="text-muted">`; sin texto hardcodeado (claves nuevas en `ACCOUNTING.BALANCES.*`, tres idiomas).

## Alternativas consideradas
1. Pestaña dentro de Movimientos: descartada, ya existe la ruta Saldos en el menú.
2. Tabla paginada por servidor: descartada, el plan de cuentas es acotado y los totales deben cubrir todas las filas filtradas.
3. Mostrar siempre saldo inicial: descartada, añade dos columnas sin información cuando no hay rango; solo aparecen con **Desde**.

## Comportamiento por privilegio/estado
- Cargando: indicador de carga. Error: `alert alert-danger` con «Reintentar». Vacío (la empresa no tiene cuentas, o los filtros no dejan ninguna): «Sin registros» y, con filtros, badges de filtros activos y «Limpiar filtros».
- Rango inválido (Desde > Hasta): mensaje de campo y no se consulta.
- Módulo `accounting` deshabilitado: la ruta ya está protegida por `data.module`.
- **El backend es la barrera:** la API exige módulo habilitado, usuario autenticado de la empresa y filtra por `company_id`; el frontend solo oculta y presenta.

## Consecuencias
Sin deuda visual: reutiliza patrones existentes. Si la cantidad de cuentas creciera mucho, se evaluaría paginar (fuera de alcance).
