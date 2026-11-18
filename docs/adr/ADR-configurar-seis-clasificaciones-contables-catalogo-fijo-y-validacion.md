# ADR-configurar-seis-clasificaciones-contables-catalogo-fijo-y-validacion: Catálogo fijo de seis clasificaciones con habilitación por empresa

**Estado:** Propuesto
**Task relacionado:** TASK-configurar-seis-clasificaciones-contables
**Fecha:** 2026-11-16

## Contexto
CONT-08 pide seis clasificaciones predefinidas (Activo, Pasivo, Patrimonio, Ingresos, Gastos, Costos) que cada empresa solo puede habilitar o deshabilitar. CONT-09 las usará como clasificación obligatoria de cada cuenta. El catálogo CONT-01 (`accounting_classification`: INCOME/EXPENSE, nombre libre) es otro concepto y sigue vigente para los egresos ya integrados.

## Decisión
1. **Catálogo en dominio, no en base.** `domain/account_class.py` define las seis constantes (`ASSET`, `LIABILITY`, `EQUITY`, `INCOME`, `EXPENSE`, `COST`) con su orden fijo. No hay crear, renombrar ni borrar: no existen esos casos de uso ni rutas.
2. **Solo se guarda lo que se deshabilita.** Tabla nueva `accounting_account_class_setting` (`company_id` UUID, `code`, `is_enabled`, marcas de tiempo), única `(company_id, code)`. La ausencia de fila significa **habilitada**. Así toda empresa (existente o nueva) tiene las seis sin sembrar ni migrar datos, y reejecutar cualquier cosa no duplica filas.
3. **API** bajo `/api/accounting/account-classes/`: `GET` lista siempre las seis `{code, enabled}` en orden fijo; `POST <code>/enable/` y `POST <code>/disable/` (idempotentes; código ajeno → 404). Permiso y gate como el resto de la configuración (`_ConfigView`). Nombres y descripciones se traducen en el frontend por `code`.
4. **Campo mínimo en la cuenta.** `accounting_account.account_class` (`CharField`, nulable, sin valor por defecto). La cuenta acepta `account_class` opcional al crear y al editar: si se envía un valor distinto del actual, la clasificación debe existir en el catálogo y estar habilitada (`400` con `account_class` en caso contrario). Un valor igual al actual no se revalida (una cuenta existente de una clasificación deshabilitada sigue editable y operativa). Código de cuenta, obligatoriedad y bloqueo por asientos son de CONT-09.
5. **Fachada** `accounting.services.validate_account_class(company_id, code)` → DTO o `AccountValidationError`; es el punto que usará CONT-09 y siguientes. Los módulos de negocio no importan infraestructura.
6. **Sin efectos colaterales.** Deshabilitar solo escribe su fila: no toca cuentas, entradas ni saldos; no hay cascada.
7. Migración `0007` aditiva: una tabla nueva vacía y una columna nulable. No se editan migraciones aplicadas ni se siembran datos.

## Alternativas consideradas
- **Sembrar seis filas por empresa** (migración de datos o al crear la empresa): obliga a tocar 21 empresas locales y a mantener la siembra para empresas nuevas; la ausencia-es-habilitada evita ambas cosas.
- **Reutilizar `ClassificationModel` (CONT-01) con nombres fijos:** mezcla «por qué se mueve el dinero» con «a qué parte del balance pertenece una cuenta» y rompe su unicidad por dirección.
- **No añadir el campo a la cuenta y dejar el rechazo para CONT-09:** la aceptación 2/3 de la tarjeta exigiría verificarse sin cuenta clasificable; se prefiere el campo nulable mínimo y que CONT-09 lo endurezca.
- **Catálogo editable para el dueño:** descartado por la tarjeta («sin crear, renombrar ni borrar»).

## Estrategia de rollback / mitigación
`migrate accounting 0006` elimina la tabla y la columna; ninguna otra tabla las referencia y la columna es nulable, así que no se pierden datos de negocio. Sin cambios de datos existentes, no requiere respaldo adicional más allá del procedimiento de CONT-07 para bases con datos.

## Consecuencias
- Conviven dos conceptos: clasificaciones de movimiento (CONT-01) y clasificaciones contables (CONT-08); el DDR los distingue en la interfaz y CONT-11 las unificará en Configuración.
- Las cuentas existentes quedan con `account_class` nulo hasta CONT-09; el diagnóstico de CONT-07 las trata como Activo cuando convierta (mapeo ya decidido en su ADR).
- Código de cuenta y obligatoriedad no se introducen aquí; CONT-09 no necesita reabrir este contrato.
