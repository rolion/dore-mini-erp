# ADR-modularidad-corte-historicos-contabilidad-ciclo-de-vida-y-corte: Ciclo de vida de Contabilidad, fecha de corte y límites entre módulos

**Estado:** Propuesto
**Task relacionado:** TASK-modularidad-corte-historicos-contabilidad
**Fecha:** 2026-11-15

## Contexto
Los egresos (CONT-02, GAS-01, COM-01) se sumarán a un libro que hoy solo registra ingresos. Antes hace falta fijar cuándo empieza a contar Contabilidad para cada empresa, qué pasa con lo anterior y con los periodos desactivados, cómo se deshabilita sin dejar egresos huérfanos y que Gastos/Compras sigan operando sin Contabilidad. `modularity` no puede importar módulos de negocio; hoy solo hay un puerto de precondiciones al habilitar (`shared/enable_preconditions.py`) y ninguna noción de corte, apertura o cobertura. El usuario ya decidió que habilitar/deshabilitar no exige configuración previa (ADR crear-cuentas, ajuste 2026-11-14).

## Decisión
1. **Puerto neutro de ciclo de vida** `shared/module_lifecycle.py` (mismo patrón que `enable_preconditions`): un módulo registra `on_enabled(company_id)`, `on_disabled(company_id)` y `disable_blockers(company_id) -> list[str]`. `EnableModule`/`DisableModule` los invocan dentro de la misma transacción; si hay bloqueadores, `DisableModule` lanza `DisableBlocked` y la API responde 409 `{code: 'disable_blocked', blockers: [...]}`. `modularity` sigue sin importar `accounting`.
2. **Ajustes y cobertura en `accounting`** (UUID de empresa, sin FK a otros módulos):
   - `accounting_settings`: `company_id` único, `cutoff_date` (date), `created_at`.
   - `accounting_coverage_period`: `company_id`, `started_at`, `ended_at` nulo; como máximo **un periodo abierto por empresa** (restricción única parcial). Habilitar abre uno si no hay abierto (idempotente); deshabilitar cierra el abierto. Los huecos entre periodos son los «periodos sin cobertura».
3. **Fecha de corte** (decisión del usuario): al habilitar por primera vez se crea el ajuste con `cutoff_date = hoy` (`TIME_ZONE`); habilitar de nuevo (reactivación) **no** la modifica ni duplica filas. Se puede cambiar (`PATCH`) solo mientras no existan movimientos de la empresa; después es inmutable (409 `cutoff_locked`). Empresas con Contabilidad ya habilitada: el ajuste se completa de forma perezosa en el primer acceso (`ensure_settings`) con corte = fecha de pago de su primera entrada o, sin entradas, hoy; el periodo abierto empieza en ese momento. Nunca se contabiliza nada retroactivamente.
4. **Saldo de apertura** (decisión del usuario): `accounting_account.opening_balance` `Decimal(12,2) ≥ 0`, por defecto 0, es el monto a la fecha de corte. Editable (`PATCH` de la cuenta) solo si la cuenta no tiene movimientos (409 `account_has_entries` ya existente). Regla de saldo para CONT-04: `apertura + movimientos con fecha efectiva ≥ corte`; lo anterior al corte es histórico y no suma (evita doble conteo con la apertura). Las entradas ya registradas no cambian.
5. **Fachada de decisión** en `accounting/services.py`: `coverage_status(company_id, effective_date)` → DTO `(enabled, cutoff_date, covered, reason)`; `covered` solo si Contabilidad está habilitada, la fecha es ≥ corte y no cae en un periodo sin cobertura. Es la única regla que egresos y compras usarán para decidir si crean movimiento: sin cobertura → la operación se guarda **sin** movimiento y sin error (independencia operativa); con cobertura → exigen cuenta activa y clasificación válida y fallan **antes de confirmar** (CONT-03/GAS-01/COM-01). Un gasto anterior al corte nunca genera movimiento ni reversión.
6. **Bloqueo al deshabilitar:** `accounting` registra `disable_blockers` consultando a su repositorio si hay movimientos de egreso vigentes sin revertir. Hoy no hay egresos (devuelve vacío); CONT-02 implementa la consulta real sobre el mismo contrato, probado aquí con un doble. Los ingresos no bloquean (comportamiento actual).
7. **Catálogo:** `purchases` pasa de `requires=('catalog','expenses')` a `requires=('catalog',)`, `optional=('expenses',)`: no hay dependencia funcional. `ALLOWED_DEPENDENCIES` queda `purchases: {catalog, inventory}` y `expenses: set()`; se fija la **dirección objetivo** `expenses → accounting` y `purchases → accounting` (futuras, por `services.py`) y la regla `accounting` ↛ `expenses`/`purchases`, con una prueba que la comprueba. El ciclo preexistente accounting ⇄ sales/receivables se documenta y no se amplía.
8. **Contrato API:** `GET/PATCH /api/accounting/settings/` (corte, periodos, `locked`), `opening_balance` en cuentas, y `coverage` del libro ampliado con `cutoff_date` y `gaps`. `POST /api/modules/accounting/disable/` puede devolver 409 `disable_blocked`.

## Alternativas consideradas
- **Corte por origen (ingresos/egresos):** más flexible, pero duplica reglas; el usuario eligió un corte único.
- **Apertura como movimiento del libro:** auditada, pero introduce un tipo de movimiento antes de CONT-02; rechazada por el usuario.
- **Que `modularity` consulte tablas de `accounting`:** viola fronteras; se usa el puerto neutro.
- **Recontabilizar al reactivar:** crea movimientos silenciosos; descartado.
- **Quitar `purchases → expenses` sin sustituto:** se conserva como `optional` para que el panel siga mostrando la relación.

## Estrategia de rollback / mitigación
Migración `accounting/0005` aditiva (dos tablas nuevas y una columna con defecto 0): revertir = `migrate accounting 0004`. El cambio de catálogo es solo código (más permisivo). El puerto de ciclo de vida sin registros se comporta como hoy. Sin datos destructivos.

## Consecuencias
- Contabilidad pasa a tener un estado propio de corte y cobertura que CONT-02..05 consumirán por `coverage_status`.
- Las empresas nuevas habilitan sin fricción (corte = hoy); las existentes se completan al primer acceso.
- El bloqueo al deshabilitar es efectivo cuando existan egresos (CONT-02); hasta entonces el contrato queda probado con dobles.
- Compras ya no obliga a tener Gastos habilitado; deshabilitar Gastos deja de verse bloqueado por Compras.
