# ADR-reportes-adaptar-modulos-activos-fuentes-opcionales: Ventas y Gastos como fuentes opcionales de Reportes

**Estado:** Propuesto
**Task relacionado:** TASK-reportes-adaptar-modulos-activos
**Fecha:** 2026-10-30

## Contexto
`modules.py:21-22` declara `requires=('sales','expenses')` para Reportes; por eso nunca falta una fuente. PB-REP-001 exige que Reportes use solo fuentes activas, y el usuario confirmó (2026-10-30) hacerlas opcionales y permitir Reportes sin ninguna.

## Decisión
1. **Catálogo:** `reporting` → `requires=()`, `optional=('sales','expenses','customers')`. Habilitar/deshabilitar Ventas o Gastos deja de verse bloqueado por Reportes (Compras sigue requiriendo Gastos; `check_can_disable` no cambia). Sin migración: el catálogo vive en código y la selección por empresa no cambia.
2. **Disponibilidad como puerto:** Reporting define el puerto `SourceAvailability` (`sales_enabled()`, `expenses_enabled()`) implementado en `infrastructure/adapters.py` con `shared.module_gate` (una consulta por petición), igual que `CustomerNamesAdapter`. Los casos de uso no leen una fuente deshabilitada.
3. **Contrato:**
   - `GET /api/reports/dashboard/` responde 200 siempre que Reportes esté activo y agrega `sources: {sales, expenses}` (booleanos). Campos de Ventas (`sales_total`, `orders_count`, `average_ticket`, `pending_*`) = `null` si Ventas está off; `expenses_total` = `null` si Gastos está off; `estimated_profit` = `null` si falta cualquiera. Nunca se sustituye por 0.
   - Reportes de una sola fuente declaran esa fuente en `required_modules`: `sales`, `sales-by-channel`, `top-products`, `pending` → `('reporting','sales')`; `expenses` → `('reporting','expenses')`; `top-customers` → `('reporting','sales','customers')`. Con la fuente off: 403 `module_disabled` (patrón vigente, fail-closed).
   - El panel no pide esos endpoints cuando la fuente está off (evita la expulsión del interceptor).
4. Ganancia estimada, ventas por fecha de pedido y exclusión de Compras no cambian.

## Alternativas consideradas
- Mantener `requires` y solo endurecer la UI: los criterios sobre fuentes ausentes serían inalcanzables (rechazada por el usuario).
- Reportes parciales con 200 y `available:false` en cada endpoint: dos convenciones para lo mismo; se prefirió el 403 ya establecido y el contrato nullable solo en el dashboard, que es agregado.
- Regla «al menos una fuente»: rechazada por el usuario.

## Estrategia de rollback / mitigación
Revertir el PR restaura `requires`. Una empresa que ya apagó Ventas o Gastos quedaría con Reportes activo sin su requisito: con el código antiguo el dashboard seguiría leyendo las tablas (los datos persisten) y la pantalla de módulos mostraría la dependencia incumplida; se corrige re-habilitando la fuente. No hay migración que deshacer.

## Consecuencias
- Cambia el contrato del dashboard (campos anulables + `sources`); único consumidor: panel Angular, mismo PR.
- Deshabilitar Ventas/Gastos ya no se bloquea por Reportes; el diálogo de módulos no listará Reportes como afectado.
- Nuevo caso de prueba por combinación de fuentes (4) en backend.
