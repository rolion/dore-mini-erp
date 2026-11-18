# ADR-adaptar-reportes-libro-partida-doble-lectura-contable-en-reporting: Reporting lee el libro de asientos por una fachada de solo lectura de Accounting

**Estado:** Propuesto
**Task relacionado:** TASK-adaptar-reportes-libro-partida-doble
**Fecha:** 2026-11-18

## Contexto
Los reportes actuales (`backend/modules/reporting/`) se calculan desde Ventas (`sales_services.get_sales_totals`, por fecha de pedido) y Gastos (`expense_services.get_expense_report`, gastos vigentes por `expense_date`); no leen el libro de partida doble (`accounting_journal_entry` / `accounting_journal_line`). Eso no distingue flujo de dinero de resultado, no sabe de compras de inventario, costo de ventas, transferencias ni reversiones por fecha contable. El libro ya expone `journal_balances` (`accounting/services.py:459`) pero solo acumulado total por cuenta, sin rango de fechas, sin agrupar por asiento y sin cobertura. Reporting hoy solo depende de `{sales, expenses, customers}` (`docs/architecture/ddd.md` §821).

## Decisión
1. **Nueva dependencia permitida `reporting → accounting`**, solo por `modules/accounting/services.py` y desde `reporting/infrastructure/adapters.py` (puerto `LedgerReader` en `reporting/application/ports.py`). Accounting se trata como **fuente opcional** como Ventas y Gastos: con el módulo `accounting` deshabilitado la sección contable responde «No disponible» (no 0). Se actualizan `ddd.md` y `test_boundaries.py`.
2. **Fachada `accounting.services.get_ledger_report(company_id, date_from, date_to) -> LedgerReport`** (DTO congelado, solo lectura, sin escribir ni crear periodos). Lee **solo el libro de asientos**, por `accounting_date` (las reversiones cuentan en su propia fecha), siempre filtrado por `company_id`. Devuelve:
   - **Flujo de dinero:** cuentas de dinero = cuentas de Activo con `kind` configurado (Caja/Banco/Billetera). Saldo inicial, entradas, salidas, neto y saldo final por cuenta y total, calculados por **variación de esas cuentas** (Debe − Haber). Se agrupa **por asiento**: el neto de las líneas de dinero del asiento decide si es entrada (>0), salida (<0) o **transferencia interna** (=0, p. ej. Caja→Banco 200). Las transferencias no suman a entradas ni salidas, y se informan aparte (importe movido) para conciliar.
   - **Resultado contable:** por clase `INCOME` (Haber − Debe), `COST` y `EXPENSE` (Debe − Haber); `margen = ingresos − costos`; `resultado = margen − gastos`. Las cuentas contra quedan netas dentro de su clase. Sin estados financieros legales ni cierre de resultados.
   - **Cobertura:** `cutoff_date` de la empresa y `partial` (el rango empieza antes del corte o cruza un hueco de cobertura, vía `domain/coverage.gaps`); el libro anterior al corte no se suma.
3. **Nuevo endpoint `GET /api/reports/ledger/`** (mismo parseo de periodo que los demás reportes, `required_modules = ('reporting',)` y bloqueo por módulo `accounting` como fuente). Respuesta camelCase como el resto de `/api/reports/*`; importes como cadenas decimales. Aditivo: los endpoints `sales`, `expenses`, `dashboard`, etc. **no cambian de contrato**.
4. **Los reportes operativos se conservan y se rotulan** («operativo, no contable»): no se retiran porque Ventas/Gastos siguen siendo útiles y no hay consulta incompatible que migrar (no hay otros consumidores del libro antiguo en Reporting; `account_balances`/`journal_balances` solo se usan dentro de Accounting). El criterio de cada reporte se muestra con un texto único.
5. **No** se agrega un quinto submenú de Contabilidad: la sección vive en la pantalla existente de Reportes (`/pocketbiz/reports`).

## Alternativas consideradas
- **Calcular en Reporting con consultas directas a modelos de Accounting:** viola la regla de fachada (`services.py`) y el aislamiento entre módulos.
- **Reutilizar `trial_balance` (sumas y saldos) y derivar todo en Reporting:** el flujo exige agrupar por asiento (para neutralizar transferencias); con solo totales por cuenta una transferencia entre Caja y Banco se vería como entrada y salida brutas. Descartada.
- **Contar todos los débitos/créditos como flujo:** prohibido por la tarjeta.
- **Reemplazar los reportes de Ventas/Gastos por los contables:** rompe contrato y a empresas sin Contabilidad. Descartada.

## Estrategia de rollback / mitigación
Cambio aditivo y de solo lectura: sin migraciones ni escritura en el libro. Revertir el PR quita el endpoint y la sección; los reportes existentes siguen intactos. Rendimiento: consultas agregadas con índices existentes (`company_id`, `accounting_date`); si el rango es grande, el costo es una agregación por asiento acotada por empresa y fechas.

## Consecuencias
- Reporting gana una dependencia opcional hacia Accounting (mapa y prueba de fronteras actualizados).
- Convive el reporte operativo (por pedido/gasto) con el contable (por libro); pueden diferir si hay operaciones sin cobertura o sin contabilizar, y la cobertura lo hace visible.
- Los movimientos del libro anterior (`accounting_entry`) no entran en este reporte (decisión de transición CONT-07: lo anterior al corte es histórico).
