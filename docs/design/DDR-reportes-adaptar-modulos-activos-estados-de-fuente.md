# DDR-reportes-adaptar-modulos-activos-estados-de-fuente: Estados por fuente en Dashboard y Reportes

**Estado:** Propuesto (implementado en PR #41)
**Task relacionado:** TASK-reportes-adaptar-modulos-activos
**Fecha:** 2026-10-30

## Contexto
Con Ventas y/o Gastos opcionales (ADR-reportes-adaptar-modulos-activos-fuentes-opcionales), Dashboard y Reportes deben mostrar solo lo que sus fuentes activas permiten, sin tarjetas rotas, errores de carga (ni 403 que expulse a «Módulo no habilitado») ni ganancia engañosa.

## Pantallas/flujos afectados
- Dashboard (`/pocketbiz/dashboard/main`): indicadores y listas de pendientes.
- Reportes (`/pocketbiz/reports`): tarjetas por fuente.
- Pantalla Configuración › Módulos: sin cambio de código; Reportes mostrará Ventas/Gastos como opcionales.

## Componentes/patrones elegidos
Plantilla «Dashboard y reportes» (design-system §5): `app-period-selector`, `app-report-card`, textos de apoyo en `<small class="text-muted">`.

Estados por tarjeta (se suman a los de §4):
| Estado | Tratamiento |
|---|---|
| Fuente deshabilitada | Mismo marco de la tarjeta (título/etiqueta visibles) con el texto **«No disponible: módulo deshabilitado»** (`text-muted`, `data-testid="unavailable"`); nunca «0», «—» ni error. No se pide el dato. |
| Fuente activa, sin datos | Totales y conteos: **0** (`Bs 0.00`, `0`). Listas, desgloses, rankings y ticket promedio: **«Sin registros»**. |
| Ganancia estimada | Con ambas fuentes: valor y nota fija «Ventas menos gastos registrados; no incluye costo de producción ni costo de ventas». Si falta una: «No disponible: módulo deshabilitado» + línea «Requiere Ventas y Gastos habilitados» (sin valor, sin color verde/rojo) y se mantiene la nota. |

Cada indicador: **etiqueta** (título), **periodo** (`dd/MM/yyyy – dd/MM/yyyy` del periodo efectivo en tarjetas dependientes del periodo; «Estado actual» en pendientes) y **unidad** (`Bs` vía `money`; cantidades con su palabra: «pedidos»).

Tarjetas por fuente — Dashboard: Ventas, Pedidos (+ticket promedio), Pendientes de entrega, Pendientes de cobro → Ventas; Gastos → Gastos; Ganancia → ambas. Reportes: Total de ventas, Ventas por canal, Productos más vendidos → Ventas; Total de gastos, Gastos por categoría → Gastos; Clientes con mayor compra → Clientes (se mantiene: se oculta, DDR previo). La decisión sale de `ModulesService.enabledKeys$` (ya cargado por `moduleGuard`) y el dashboard además lee `sources` de la respuesta.

Cambiar el periodo recarga solo lo disponible; las definiciones (ventas por fecha de pedido, no canceladas) no cambian.

## Alternativas consideradas
- Ocultar las tarjetas de fuentes apagadas: la tarjeta desaparece sin explicar y la ganancia faltante confunde; la tarjeta pide «explicar una ausencia». Descartada para Ventas/Gastos (Clientes se conserva oculto por decisión previa, es un complemento).
- Mostrar 0 para fuentes apagadas: prohibido por la tarjeta (engañoso).
- Un banner global único: no explica qué indicador falta; descartada.

## Comportamiento por privilegio/estado
Solo administrador de empresa (ya rige). El frontend no es la barrera: la API devuelve `sources` + nulos en el dashboard y 403 `module_disabled` en reportes de una sola fuente deshabilitada.

## Consecuencias
Se actualiza `design-system.md` §5 (estado «No disponible» y «Sin registros»). El texto «Sin datos para este periodo.» cambia a «Sin registros» en Reportes. Deuda aceptada: Clientes se oculta mientras Ventas/Gastos se explican (criterios distintos por tipo de fuente).
