# ADR-configurar-asientos-automaticos-modulo-catalogo-modelo-y-fachada: Catálogo fijo de eventos, mapeo de cuentas por rol y fachada de contabilización

**Estado:** Propuesto
**Task relacionado:** TASK-configurar-asientos-automaticos-modulo
**Fecha:** 2026-11-16

## Contexto
Los módulos aún no contabilizan por partida doble; VEN-01, COM-01/02, INV-01 y las tarjetas de gastos lo harán. Todas necesitan lo mismo: saber **qué cuentas** usar en cada evento, validarlas, mostrar la configuración faltante **antes** de confirmar y deduplicar con el motor CONT-02 (`post_journal_entry`, idempotente por `(empresa, origen)`). La tarjeta CONT-12 pide hacerlo **sin un constructor genérico de reglas** y con la configuración dentro de cada módulo. Hoy solo existe el mapeo método de pago → cuenta (`MethodMapping`), sin validar clasificación (`domain/account.py:157-174`).

## Decisión
1. **Catálogo fijo en código** (`accounting/domain/posting.py`, sin Django). Nada de reglas definidas por la persona.
   - **Roles** (cuenta con una clasificación obligatoria): `SALES_INCOME` y `SERVICE_INCOME` (INCOME), `RECEIVABLE`, `INVENTORY` (ASSET), `COST_OF_SALES` (COST), `PAYABLE` (LIABILITY). Roles con origen distinto: `MONEY` (método de pago → cuenta ASSET con tipo Caja/Banco/Billetera) y `EXPENSE_BY_CATEGORY` (categoría de gasto → cuenta EXPENSE).
   - **Eventos** (todos de dos líneas con el mismo importe; el código del evento **es** el `origin_kind` del asiento, ≤ 30 caracteres):
     | Módulo | Evento | Debe | Haber |
     |---|---|---|---|
     | `sales` | `SALE_RECOGNITION` | `RECEIVABLE` | `SALES_INCOME` |
     | `sales` | `SALE_PAYMENT` | `MONEY` (método) | `RECEIVABLE` |
     | `receivables` | `SERVICE_RECOGNITION` | `RECEIVABLE` | `SERVICE_INCOME` |
     | `receivables` | `SERVICE_PAYMENT` | `MONEY` (método) | `RECEIVABLE` |
     | `inventory` | `INVENTORY_SALE_COST` | `COST_OF_SALES` | `INVENTORY` |
     | `purchases` | `PURCHASE_RECOGNITION` | `INVENTORY` | `PAYABLE` |
     | `purchases` | `PURCHASE_PAYMENT` | `PAYABLE` | `MONEY` (método) |
     | `expenses` | `EXPENSE_RECORD` | `EXPENSE_BY_CATEGORY` | `MONEY` (método) |
   - Cada módulo solo ve los eventos de su clave; un módulo agrega eventos con una entrada en el catálogo (sin migración).
2. **Persistencia** (migración nueva `0011_posting_account`, solo `CreateModel`): `accounting_posting_account(id, company_id indexado, scope 'ROLE'|'CATEGORY', key, account FK PROTECT, updated_at)` con unicidad `(company_id, scope, key)`; `key` = código de rol o id de la clasificación. Una cuenta por rol y empresa (compartida entre módulos: p. ej. `INVENTORY` en Compras e Inventario). **El método → cuenta Caja/Banco sigue en `MethodMapping`** (fuente única compartida por cobros, pagos de compras y gastos); su validación de **usos nuevos** se endurece: la cuenta debe ser de Activo con tipo Caja/Banco/Billetera, activa y en BOB. Lo ya configurado no se revalida al guardar otra cosa.
3. **Validación de una asignación nueva** (dominio + caso de uso; la API solo valida forma): la cuenta existe **en la empresa** (el repositorio filtra por `company_id`; una ajena responde como inexistente), está activa, su clasificación está habilitada en la empresa y coincide con la del rol; categorías: clasificación de la empresa, de dirección EXPENSE y activa. Errores por campo (`account_id`) con mensaje accionable. Quitar la asignación (`account_id: null`) siempre se permite.
4. **Resolución en cada evento** (en vivo, no cacheada): `resolve_posting(company_id, event, método/categoría)` re-valida la cuenta configurada (existe, activa, clasificación vigente, misma empresa). Cualquier falta produce `PostingConfigurationMissing(issues)` con una lista `{code, role, label, module, message}`; el mensaje nombra la cuenta faltante o deshabilitada y **dónde** corregirla («Configúrela en Ventas › Configuración › Asientos automáticos»).
5. **Fachada pública** (`accounting/services.py`, DTO inmutables; los módulos no importan nada más de Contabilidad):
   - `describe_posting_config(company_id, module) -> PostingConfigRef`: eventos con vista previa Debe/Haber, estado por rol/categoría/método y faltantes. Alimenta la API y la UI.
   - `check_posting_ready(company_id, event, *, accounting_date, method=None, classification_id=None) -> PostingReadiness` (`required`, `issues`): para mostrar la configuración faltante **antes de confirmar** una operación. `required=False` cuando `coverage_status(...)` dice que la operación no se contabiliza (Contabilidad deshabilitada, anterior al corte o en hueco): ahí nunca se exigen cuentas.
   - `post_automatic_entry(company_id, event, origin_id, accounting_date, description, amount, *, method=None, classification_id=None, created_by=None, created_by_name='') -> AutomaticPosting` (en la transacción del llamante): si no hay cobertura devuelve `posted=False` con la razón y **no** crea nada (los módulos operativos siguen independientes; reactivar no contabiliza históricos porque la cobertura ya excluye esos tramos); si hay cobertura y falta configuración lanza `PostingConfigurationMissing` (nunca omite en silencio); si todo está bien arma las dos líneas con las cuentas resueltas y llama a `post_journal_entry` con `origin_kind = código del evento` y `origin_id` del evento del módulo, heredando idempotencia y conflicto del motor. El importe es `Decimal` > 0 (cuentas y moneda las valida el motor).
   - `reverse_automatic_entry(company_id, event, origin_id, reversal_date, reason, ...)`: localiza el asiento por origen y llama a `reverse_journal_entry`, que usa las **cuentas originales** y no consulta la configuración actual; `None` si el evento nunca se contabilizó.
   - Altas: `set_role_account`, `set_category_account`; `post_journal_entry` y `reverse_journal_entry` siguen disponibles.
6. **API** (`/api/accounting/posting-config/`, permiso por defecto de administrador y empresa del usuario; **sin** `required_modules = ('accounting',)`, igual que Cuentas: se configura antes de habilitar Contabilidad):
   - `GET ?module=<clave>` → `200 {module, ready, events:[{code,label,preview:[{side,label,account_label}],issues}], roles:[…], methods:[…], categories:[…]}`; módulo ajeno al catálogo → `404`.
   - `PUT roles/<role>/` y `PUT categories/<classification_id>/` con `{account_id: uuid|null}` → `200` (mismo cuerpo de la entrada); `400` por campo (cuenta ajena, inactiva, clasificación incorrecta); `404` rol/categoría desconocidos.
   - Métodos: `PUT payment-methods/<code>/` ya existe; solo cambia su validación (nuevo `400` por `account_id` si no es Caja/Banco de Activo).
7. **Deduplicación y origen:** el motor ya rechaza duplicados por `(empresa, origen)` y orígenes presentes en el libro anterior; el catálogo fija el vocabulario `origin_kind` (cierra la deuda declarada en `TASK-asientos-manuales-navegacion-contable`). Un cambio de configuración **no** toca asientos: las líneas guardan `account_id` y la reversión usa esas líneas.
8. **Fronteras:** los módulos de negocio consumen solo `accounting.services` (ya permitido y vigilado por `test_boundaries.py`); `accounting` no importa módulos de negocio. El dominio de Contabilidad no importa Django.

## Alternativas consideradas
- **Constructor genérico de reglas** (evento → N líneas editables): descartado por la tarjeta; más superficie, errores de configuración y soporte.
- **Configuración guardada en cada módulo** (tabla propia en Ventas, Compras…): obligaría a cada módulo a validar cuentas de Contabilidad (importar su infraestructura o duplicar reglas) y a repetir roles compartidos (Inventario, CxC). Descartada; los módulos solo **muestran** la configuración que Contabilidad guarda.
- **Pantalla única en Contabilidad:** descartada por la persona (la configuración va en cada módulo).
- **Un mapeo método → cuenta por módulo:** descartado: una caja es de la empresa; triplicaría el dato y la posibilidad de contradicciones. Se reutiliza `MethodMapping`.
- **Caché de la resolución / copiar cuentas en la operación de origen:** descartado; se resuelve en vivo en la transacción de contabilizar y el asiento guarda las cuentas usadas (snapshot en las líneas).
- **Bloquear desactivar o reclasificar una cuenta configurada:** descartado; la tarjeta pide que una cuenta deshabilitada **impida la operación con mensaje accionable**, no que no se pueda deshabilitar.
- **Tabla de historial de cambios de configuración:** fuera de alcance (la tarjeta no la pide); el asiento ya conserva las cuentas usadas.

## Estrategia de rollback / mitigación
Migración solo aditiva (una tabla): revertir = `migrate accounting 0010` o desplegar la versión anterior. Ningún módulo depende todavía de la fachada, así que no hay efecto en operaciones existentes; sin filas, todo evento aparece como «Sin configurar». El endurecimiento del mapeo de métodos solo afecta a asignaciones nuevas; una empresa con cuentas heredadas sin clasificar sigue operando con lo ya guardado y recibe un mensaje que indica clasificar la cuenta en Cuentas.

## Consecuencias
- Contrato único para cinco módulos; cada integración se reduce a «verificar con `check_posting_ready`, contabilizar con `post_automatic_entry`».
- Agregar un evento o rol es una entrada de catálogo + tests; no hay migración salvo roles con almacenamiento nuevo.
- Todos los eventos son de dos líneas con un único importe; un evento con más líneas (p. ej. venta con impuestos o descuentos) requiere ampliar el catálogo y la fachada.
- Una sola cuenta por rol y empresa: no hay cuentas distintas por almacén, canal o sucursal.
- Compras e Inventario comparten el rol `INVENTORY`: cambiarlo en uno lo cambia en el otro (la UI lo indica).
- Se resuelve en vivo: más consultas por evento (bajas: ≤ 3 cuentas), a cambio de no mostrar nunca una configuración desactualizada.
