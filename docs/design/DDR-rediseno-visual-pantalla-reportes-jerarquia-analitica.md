# DDR-rediseno-visual-pantalla-reportes-jerarquia-analitica: Jerarquía analítica en la pantalla de Reportes

**Estado:** Propuesto
**Task relacionado:** TASK-rediseno-visual-pantalla-reportes
**Fecha:** 2026-11-18

## Contexto
Tras CONT-05 (DDR `adaptar-reportes-libro-partida-doble-seccion-contable-en-reportes`) la pantalla muestra seis bloques al mismo peso, con criterios largos siempre visibles y tablas abiertas. Este DDR **complementa** ese DDR (no lo reemplaza): conserva su contenido y reordena su presentación.

## Pantallas/flujos afectados
Solo `/pocketbiz/reports`. Orden y contenido, en un contenedor centrado de ancho máximo 80 rem (~1280 px):
1. `app-period-selector` (sin cambios de comportamiento; botones de al menos 40 px de alto).
2. **Sección «Contable (libro de asientos)»** con chip «Contable»: avisos (cobertura cerrable; «sin cuentas de dinero» con enlace a Cuentas) y dos KPIs grandes de igual altura: **Flujo de dinero** (neto grande; entradas/salidas/saldo inicial/final; transferencias internas como `small`; «Ver por cuenta» plegado) y **Resultado contable** (resultado grande, **Resultado** negativo en `text-danger` con la etiqueta «Resultado negativo», positivo en `text-success`, cero neutro; Ingresos, Costos, **Margen**, Gastos). «¿Cómo se calcula?» plegable con el criterio del servidor.
3. **Sección «Operativo (pedidos y gastos)»** con chip «Operativo»: Total de ventas y Total de gastos en tarjetas más pequeñas (cifra `h4`), criterios plegados en «¿Cómo se calcula?»; luego Ventas por canal (barras), Gastos por categoría (dona de 200 px + tabla, `aria-label` en el gráfico), Productos y Clientes.

## Componentes/patrones elegidos
Plantilla «Dashboard y reportes» (§5), `app-report-card`, `app-period-selector`, `<details>/<summary>` nativo para plegables (teclado y lector de pantalla gratis, sin dependencia), alerta tenue `alert alert-info bg-info-subtle text-info-emphasis border-info-subtle`, `btn-close` con `aria-label`, chips = `badge rounded-pill` con `bg-primary-subtle text-primary-emphasis` (misma familia tonal que `app-status-badge`; solo informativos). Textos auxiliares con `small` sin `text-muted` sobre fondo claro de bajo contraste: se usa `text-body-secondary` (≥ 4,5:1) y nunca menos de 12 px. Sin HEX nuevos; sin componente compartido nuevo.

## Alternativas consideradas
- **Tooltip ⓘ (`ngbTooltip`):** no es accesible en táctil sin foco; se elige `<details>`.
- **Chips interactivos como filtro contable/operativo:** añade estado y no lo pidió la crítica; descartado.
- **Mantener todo en una fila de 4 KPIs:** mezcla fuentes distintas al mismo nivel; descartado.

## Comportamiento por privilegio/estado
- Cargando / error con «Reintentar» / «No disponible: módulo deshabilitado» / «Sin registros»: iguales a §4 y al DDR de estados de fuente; cada tarjeta carga y falla por separado.
- Aviso de cobertura: cerrable (`aria-label` «Cerrar aviso»); **reaparece al cambiar de periodo**.
- Aviso «sin cuentas de dinero»: aparece cuando el libro responde `cash_flow.accounts` vacía; enlaza a `/pocketbiz/accounting/accounts`; el enlace no concede acceso (el backend aplica empresa, módulo y rol; el frontend no es la barrera).
- Resultado negativo: color + signo + etiqueta de texto (nunca solo color).

## Consecuencias
Pantalla más densa en jerarquía y más corta de leer. Deuda aceptada: `foreColor` HEX de la dona preexistente; sin series por día (la API no las da). Las pantallas Dashboard y otras no cambian.
