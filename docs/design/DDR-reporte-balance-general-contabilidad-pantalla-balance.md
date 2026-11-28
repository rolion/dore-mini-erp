# DDR-reporte-balance-general-contabilidad-pantalla-balance: Pantalla Contabilidad › Balance general

**Estado:** Propuesto
**Task relacionado:** TASK-reporte-balance-general-contabilidad
**Fecha:** 2026-11-26

## Contexto
Nuevo reporte contable de solo lectura con filtros de fecha inicio y fin. Debe leerse como un estado financiero: Activo a un lado de la ecuación, Pasivo y Patrimonio al otro, con totales y señal de que cuadra.

## Pantallas/flujos afectados
- Nueva: Contabilidad › Balance general, ruta `/pocketbiz/accounting/balance-sheet` (`data.module = 'accounting'`), entrada de menú junto a «Saldos» (`MENUITEMS.ACCOUNTING.LIST.BALANCE_SHEET`).
- Sin cambios en otras pantallas.

## Componentes/patrones elegidos
Plantilla «Lista de solo lectura con filtros» de `docs/design/design-system.md` (sección 5), con la estructura de `pages/balances` y `pages/income-expense`: breadcrumb, `.card`, `ngxTableHeader`, filtros en `form.row.g-2` y `table-responsive`. Sin componentes compartidos nuevos.
- Filtros: **Desde** y **Hasta** (`input type=date`), «Limpiar filtros»; viven en la URL (`date_from`, `date_to`). Rango invertido: mensaje de error sin llamar a la API (igual que Saldos).
- Una tarjeta-tabla por sección en este orden: **Activo**, **Pasivo**, **Patrimonio**. Columnas: Código, Cuenta, Saldo inicial (solo si hay «Desde»), Movimiento (solo si hay «Desde»), Saldo final. Pie de cada sección: «Total <sección>».
- Patrimonio añade al final dos filas calculadas, en cursiva y con `text-body-secondary`: «Resultados de ejercicios anteriores» y «Resultado del período».
- Bloque de cierre con tres cifras: Total Activo, Total Pasivo + Patrimonio y badge `Cuadra` (verde) / `No cuadra` (rojo) con la diferencia.
- Nota `small.text-muted` bajo los filtros que explica: saldos acumulados hasta «Hasta»; «Desde» separa saldo inicial y movimiento.
- Aviso `alert alert-warning` si hay cuentas sin clasificar con saldo (con el importe).
- Importe negativo: `text-danger` y no solo color (signo «−» visible), reutilizando `MoneyPipe`.
- Móvil (< 576 px): sin ancho mínimo, fuente y relleno compactos como `income-expense.component.scss` (REV-03 de ese task).

## Alternativas consideradas
- Una sola tabla con las tres secciones: más corta pero mezcla subtotales; descartada por legibilidad.
- Dos columnas lado a lado (Activo | Pasivo+Patrimonio): fiel al formato clásico pero inutilizable en móvil; descartada.
- Reutilizar la pantalla Saldos con una pestaña: Saldos es por cuenta y sin agrupación; mezclarlas complica ambas.

## Comportamiento por privilegio/estado
- Cargando: texto «Cargando…»; error: `alert-danger` con «Reintentar»; vacío (sin cuentas con saldo): «Sin registros» y, si hay filtros, chips con los filtros y «Limpiar filtros».
- Acceso: solo con el módulo Contabilidad habilitado (`data.module` en la ruta y `required_modules = ('accounting',)` en el backend). El frontend no es la barrera: el backend filtra por la empresa del usuario autenticado y responde 403/404 sin el módulo.

## Consecuencias
Sin deuda visual aceptada. La pantalla es nueva y coherente con Saldos e Ingresos y egresos. Se propone añadir a `design-system.md` solo si aparece un patrón reutilizable (no se prevé).
