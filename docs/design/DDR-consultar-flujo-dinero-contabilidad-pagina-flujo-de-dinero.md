# DDR-consultar-flujo-dinero-contabilidad-pagina-flujo-de-dinero: Página «Flujo de dinero» en Contabilidad

**Estado:** Propuesto
**Task relacionado:** TASK-consultar-flujo-dinero-contabilidad
**Fecha:** 2026-11-18

## Contexto
La tarjeta «Flujo de dinero» de Reportes da totales y una tabla por cuenta con variación y saldo final, pero no permite verificar cómo se compone ni llegar al asiento. La persona de Contabilidad necesita el detalle en una página propia.

## Pantallas/flujos afectados
1. **Nueva** `/pocketbiz/accounting/cash-flow` (submenú «Flujo de dinero» de Contabilidad, entre «Saldos» y «Configuración»; `adminOnly`, módulo `accounting`).
2. **Tarjeta «Flujo de dinero» de Reportes:** el `<details>` «Ver por cuenta» se reemplaza por un enlace «Ver por cuenta» a `/pocketbiz/accounting/cash-flow?date_from=…&date_to=…` con las fechas efectivas devueltas por el servidor. El resto de la tarjeta (neto, tabla de saldo inicial/entradas/salidas/saldo final, transferencias, «Cómo se calcula») no cambia. La tabla por cuenta pasa a la página nueva. Con Contabilidad deshabilitada la tarjeta ya muestra «No disponible», así que no hay enlace.

Estructura de la página (de arriba abajo):
- Breadcrumb y título «Flujo de dinero». Aviso de cobertura (`alert alert-warning`, cerrable) cuando el período es parcial (mismo texto que Reportes).
- **Filtros de período:** Desde / Hasta (`input type=date`) con «Limpiar filtros» (vuelve al mes actual). Por defecto, el mes actual o las fechas de la URL. Un rango inválido muestra el error en línea y no consulta.
- **Resumen** (`card`): saldo inicial, entradas, salidas, flujo neto (resaltado) y saldo final, con `money`. Nota «Las transferencias entre tus cuentas no cambian el flujo neto» con su importe.
- **Cuentas de dinero** (tabla `table table-sm`, fila seleccionable): Cuenta, Saldo inicial, Entradas, Salidas, Transf. recibidas, Transf. enviadas, Saldo final y fila de total. Al elegir una cuenta (botón en el nombre, `aria-pressed`) se filtra el detalle y se muestra un chip «Cuenta: X ✕» para quitar el filtro.
- **Movimientos** (plantilla «Lista de solo lectura con filtros», §5): filtro «Tipo» (Todos, Entradas, Salidas, Transferencias) y la cuenta seleccionada; columnas Fecha contable, Cuenta, Concepto (con badge «Reversión» si aplica), Origen, Tipo (badge con texto), Importe y acción «Ver asiento» (botón circular de 44 px a `/pocketbiz/accounting/journal/:id`). El origen enlaza solo si el servidor lo marca disponible (`journalOriginLink`); si no existe, «—». Paginación del servidor con resumen «Mostrando n–m de N» y totales del filtro vigente (entradas, salidas, transferencias recibidas y enviadas).
- **Compacta (< 992 px):** los filtros (Desde, Hasta, Tipo) van en un panel plegable «Filtros» con «Aplicar filtros» y contador/chips; la tabla de movimientos pasa a tarjetas con `ngb-pagination` y `CompactViewportService`; la tabla por cuenta se muestra como tarjetas (una por cuenta, `dl`). Es la variante compacta ya documentada para «Lista de solo lectura con filtros».

## Componentes/patrones elegidos
- Plantilla «Lista de solo lectura con filtros» (referencia `inventory/movement-list`, con `ngx-datatable` y variante compacta) y la estructura de `journal-list` para origen y enlace al asiento; resumen con `card` y `money` como en `balances-page`. Sin componentes nuevos de la plantilla Oreva; el selector de período compartido de Reportes no se reutiliza porque resuelve «hoy/semana/mes» en el servidor, y esta página recibe y envía fechas explícitas (ver PLAN §Architecture considerations).
- Importes: entrada en verde (`text-success`), salida en rojo (`text-danger`), transferencia en gris/azul neutro con badge de texto y signo (+/−) además del color.
- Etiquetas de negocio: «Entradas», «Salidas», «Transferencias recibidas/enviadas», «Flujo neto» (como Reportes).

## Alternativas consideradas
- **Mantener el `<details>` y añadir otro enlace:** duplica «Ver por cuenta» y deja dos tablas por cuenta con cifras distintas. Descartado; se prefiere un solo lugar para el detalle.
- **Pestañas Resumen / Movimientos:** oculta la relación entre cuenta seleccionada y detalle (la tarjeta pide filtrar al seleccionar). Descartado; una sola página con secciones.
- **Reutilizar `app-period-selector`:** requeriría que Contabilidad dependa de Reportes para resolver períodos; descartado (acoplamiento frontend y backend).

## Comportamiento por privilegio/estado
- Admin de empresa con módulo `accounting` habilitado: acceso completo. Módulo deshabilitado: `moduleGuard` lleva a `/module-disabled`; el backend responde 403 `module_disabled`. Usuario no admin o sin empresa: 403 de la API; el frontend no es la barrera.
- Estados (§4): cargando (resumen, cuentas y movimientos independientes), error con «Reintentar», vacío («Sin movimientos en este período»; con filtros, badges de filtros activos y «Limpiar filtros»), sin cuentas de dinero configuradas (mensaje con enlace a Contabilidad → Cuentas), éxito.
- El enlace «Ver asiento» exige acceso a Contabilidad en backend (el detalle del asiento ya lo aplica).
- Textos con `translate` y claves en `es/en/pt`.

## Consecuencias
La tarjeta de Reportes pierde la tabla por cuenta inline (queda en la página nueva). El design-system §6 debe sumar el submenú «Flujo de dinero» (se actualiza en este PR). Deuda aceptada: sin exportación CSV ni selector «hoy/semana/mes» en la página.
