# ADR-periodos-fiscales-por-empresa-agregado-y-bloqueo: Agregado FiscalPeriod y contrato de bloqueo para contabilizar

**Estado:** Propuesto
**Task relacionado:** TASK-periodos-fiscales-por-empresa
**Fecha:** 2026-11-16

## Contexto
CONT-10 introduce períodos fiscales por empresa. El motor de asientos (CONT-02) deberá validar que la fecha contable cae en un período abierto, también en automáticos y reversiones, y no puede quedar un asiento insertado tras el cierre. Hoy no hay asientos: solo el libro de entradas de una cuenta (`record_entry`), que por decisión de negocio no cambia.

## Decisión
1. **Agregado `FiscalPeriod`** en `accounting/domain/fiscal_period.py` (sin Django): `id, name, start_date, end_date, status (OPEN|CLOSED), closed_at/by, reopened_at/by`. Métodos `rename`, `change_limits`, `close()`, `reopen()`; un período cerrado rechaza `rename/change_limits`. Invariantes: nombre 1-80 caracteres, `start_date ≤ end_date`, fechas `date` (inclusivas).
2. **Tabla `accounting_fiscal_period`** (migración nueva `0004`): `company_id` UUID sin FK, `CHECK start_date <= end_date`, `CHECK status IN (…)`, único `(company_id, lower(name))`, índice `(company_id, start_date)`. La no superposición no se delega a un `EXCLUDE` (exigiría la extensión `btree_gist` y privilegios que producción no garantiza).
3. **No superposición por serialización:** crear/editar límites toma un bloqueo advisory transaccional `pg_advisory_xact_lock(namespace_periodos, hash(company_id))`, verifica solapamiento (`start ≤ other.end AND end ≥ other.start`, excluyendo el propio id) y guarda. El bloqueo es por empresa: empresas distintas no se bloquean y pueden repetir rangos.
4. **Cambio de límites vs. asientos:** puerto `PeriodUsage` (`accounting/application/ports.py`) con `entries_outside(company_id, period_id, start, end) -> int`; el caso de uso rechaza (409 `period_has_entries`) si cuenta > 0. Adaptador actual `NoJournalPeriodUsage` devuelve 0 (todavía no hay asientos; los cobros del libro de entradas quedan fuera de períodos por decisión de negocio). **CONT-02 reemplaza el adaptador** por uno que lee las cabeceras de asiento.
5. **Contrato para contabilizar** (fachada `accounting/services.py`, mismo estilo que `record_entry`):
   - `lock_open_period(company_id, accounting_date) -> PeriodRef`: exige transacción abierta (`PeriodContractError` si no), busca el período de la empresa que contiene la fecha con `SELECT … FOR UPDATE`, y lanza `DateOutsideFiscalPeriod` (sin período) o `FiscalPeriodClosed` (cerrado) **tras** obtener el bloqueo. El bloqueo dura hasta el fin de la transacción del llamante.
   - `period_for(company_id, accounting_date) -> PeriodRef | None`: lectura sin bloqueo.
   - `close` y `reopen` toman `FOR UPDATE` sobre la misma fila. Así: o el asiento se inserta antes del cierre (el cierre espera al commit) o el cierre gana y el asiento ve el período cerrado al reanudarse (READ COMMITTED relee la fila tras el bloqueo). Nunca queda un asiento posterior al cierre.
   - Las reversiones llaman a `lock_open_period` con **su propia fecha explícita**: si el original está en un período cerrado, la reversión va a un período abierto sin tocar el original (el motor CONT-02 aporta fecha y vínculo; este contrato solo exige que la fecha dada esté en un período abierto).
6. **Cerrar no genera asientos** de cierre de resultados: el caso de uso solo cambia el estado y registra quién y cuándo.
7. **Permisos:** sin permiso nuevo. La API usa el permiso por defecto (rol admin de empresa activa); cerrar y reabrir exigen lo mismo, cumpliendo «solo el administrador reabre». Un superusuario sin empresa no llega a la API de negocio (403) y gestiona vía Django admin.
8. **API** bajo `/api/accounting/fiscal-periods/` con `required_modules = ()` (configurable antes de habilitar Contabilidad, como cuentas): `GET/POST` lista y alta; `GET/PATCH <id>/`; `POST <id>/close/`; `POST <id>/reopen/`. Códigos 409: `period_overlap` (incluye nombres de los períodos en conflicto), `period_closed`, `period_has_entries`, `period_invalid_state` (cerrar un cerrado / reabrir un abierto). Validación de forma/tipos en serializers; reglas en dominio.

## Alternativas consideradas
- `ExclusionConstraint` con `DateRangeField`: garantiza el solapamiento en base, pero requiere `btree_gist` (extensión con privilegios); rechazado por riesgo operativo. El bloqueo advisory cubre las escrituras y cada una pasa por el caso de uso.
- Aplicar períodos a `record_entry` ya: rechazado por la persona (rompería empresas sin períodos y cobros vigentes).
- `FOR SHARE` para contabilizar y `FOR UPDATE` para cerrar (más concurrencia entre asientos): Django no lo expone sin SQL crudo y el volumen de un mini ERP no lo justifica; se puede optimizar después sin cambiar el contrato.
- Eliminar períodos: fuera de alcance; editar límites de un período abierto cubre la corrección.

## Estrategia de rollback / mitigación
Migración aditiva (tabla nueva, sin tocar datos): revertir es `migrate accounting 0003`. Sin períodos creados nada cambia para el resto de módulos; el contrato `lock_open_period` aún no lo llama nadie en producción hasta CONT-02. Si el bloqueo advisory diera problemas, el respaldo es bloquear una fila por empresa (`select_for_update` sobre la empresa) sin cambiar la API.

## Consecuencias
- Un solo punto (`lock_open_period`) concentra la regla «fecha en período abierto» para manuales, automáticos y reversiones.
- Hasta CONT-02, el bloqueo de cambio de límites se verifica con un puerto simulado; CONT-02 debe cablear el adaptador real y añadir la prueba de integración.
- Posibles huecos entre períodos: fechas sin período se rechazan al contabilizar (comportamiento deseado, mensaje accionable).
