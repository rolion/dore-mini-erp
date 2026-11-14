# ADR-libro-entradas-filtros-totales-registro-unico-y-contrato: Registro único de entradas, contrato transaccional y consulta

**Estado:** Propuesto
**Task relacionado:** TASK-libro-entradas-filtros-totales
**Fecha:** 2026-11-14

## Contexto
Ventas (pagos del pedido) y Cobros (pagos de proformas de servicios) deben generar, en entregas posteriores (PB-ACC-003, PB-COB-002), una entrada en un libro común de `accounting`, en la misma transacción del pago. Esta entrega define el contrato, la tabla y la consulta. `accounting` no puede importar `sales` ni `receivables`, y los pagos de productos no tienen `company_id`, usuario ni clave de idempotencia propios.

## Decisión
1. **Agregado `Entry` inmutable** en `accounting/domain/entry.py` (sin Django). Se crea solo con `Entry.record(...)`, que valida: monto `Decimal` > 0 con 2 decimales, moneda del catálogo, método del catálogo, origen ∈ {`PRODUCT`, `SERVICE`}. No tiene métodos de mutación.
2. **Tabla `accounting_entry`** (migración `0002`, solo `CreateModel`): `id` UUID, `company_id` (UUID indexado, sin FK), `account` (FK `PROTECT` a `AccountModel`; las cuentas no se borran), `currency`, `amount` (12,2) con `CheckConstraint(amount > 0)`, `payment_date` (fecha efectiva), `created_at`, `payment_method`, `recorded_by` (id) y `recorded_by_name` (instantánea, ambos opcionales), `origin_kind`, `origin_id` (UUID del pago), `origin_document_ref` (id del pedido o número de proforma) y `receipt_number` (CB-NNNNNN, vacío si no hay). **Único `(company_id, origin_kind, origin_id)`**; índices `(company_id, payment_date)` y `(company_id, account)`. Sin texto libre del pago, por lo que no hay datos clínicos.
3. **La cuenta se guarda en la entrada** (`account_id`) y nunca se recalcula: cambiar el mapeo no toca entradas previas. La moneda de la entrada debe igualar la de la cuenta y la cuenta debe ser de la misma empresa; si no, se rechaza (`EntryValidationError`). Una cuenta inactiva se admite solo si ya estaba asignada al cobrar (decide quien llama con `resolve_account`); el libro valida pertenencia y moneda, no vigencia, para no rechazar un cobro legítimo de otro módulo.
4. **Contrato transaccional en `accounting/services.py`**: `record_entry(company_id, entry: EntryInput) -> RecordedEntry` con DTO inmutables. No abre ni cierra la transacción del llamante: exige estar dentro de una (`transaction.get_connection().in_atomic_block`, si no, `EntryContractError`) y usa un `transaction.atomic()` interno (punto de guardado) para el `INSERT`. Si la restricción única salta (carrera o reintento), lee la existente: mismos datos de negocio (cuenta, moneda, monto, fecha, método, referencia y comprobante) → devuelve `RecordedEntry(created=False)`; datos distintos → `EntryConflict`. Así dos solicitudes concurrentes producen una sola fila y la transacción externa sigue utilizable. Los orígenes distintos con el mismo ID no colisionan porque `origin_kind` forma parte de la clave.
5. **Consulta** (`ListEntries`, `GetEntry`) con repositorio `DjangoEntryRepository(company_id)`; filtros `date_from`, `date_to` (sobre `payment_date`), `account_id`, `method`, `origin`. **Totales por agregación SQL** sobre el queryset completo filtrado, agrupados por moneda y origen, sin conversión de moneda. Cobertura: primera/última fecha efectiva y primer `created_at` del libro de la empresa (sin filtros).
6. **API de solo lectura** `GET /api/accounting/entries/` (paginada, tamaño 20, `page_size` hasta 100, orden `-payment_date, -created_at, id`) y `GET /api/accounting/entries/<id>/`. No se registran rutas de POST/PUT/PATCH/DELETE (405). Vistas con `required_modules = ('accounting',)` y `CompanyAdminPermission`; la empresa sale del usuario. El detalle ajeno responde 404.
7. **Enlace al origen**: la API devuelve `source = {kind, id, document_ref, receipt_number, available}`; `available` = el módulo propietario (`sales` para `PRODUCT`, `receivables` para `SERVICE`) está habilitado para la empresa (`shared/module_gate.is_enabled`). El frontend solo enlaza si `available` y existe pantalla. `accounting` no importa esos módulos.
8. **Sin integración** con Ventas/Cobros ni cambios en reporting en esta entrega: el contrato queda probado con llamadas directas a `services.record_entry` en tests.

## Alternativas consideradas
- **Evento/señal desde Ventas y Cobros** para crear la entrada: rompe «misma transacción» explícita y oculta el fallo; descartado.
- **Que `accounting` consulte los pagos de origen** (vista unificada): acopla el libro a esquemas ajenos y no sirve como registro inmutable de la cuenta usada; descartado.
- **`get_or_create` sin punto de guardado**: ante carrera lanza `IntegrityError` y aborta la transacción del pago; descartado.
- **Copiar `reference`/notas del pago**: riesgo de datos clínicos; descartado.
- **Totales calculados en frontend o por página**: incumple el criterio de aceptación; descartado.

## Estrategia de rollback / mitigación
La migración es aditiva (tabla nueva, sin tocar datos existentes) y ningún flujo escribe en ella todavía: revertir = desplegar la versión anterior (la tabla queda sin uso) o `migrate accounting 0001` antes de que haya entradas. Con `accounting` deshabilitado nada cambia. Tras PB-ACC-003/COB-002 la reversión de datos deja de ser trivial y se tratará en PB-ACC-006.

## Consecuencias
- Las integraciones posteriores solo llaman a `services.record_entry` dentro de su transacción; los reintentos idempotentes salen gratis de la restricción única.
- La entrada no se corrige: una equivocación requiere el flujo de reversiones (fuera de alcance).
- `origin_document_ref` y `receipt_number` son instantáneas de texto: no se actualizan si el origen cambia (es el comportamiento buscado para trazabilidad).
- Una cuenta con entradas no puede borrarse (ya no hay borrado) ni cambiar de moneda sin revisar: el cambio de moneda de una cuenta con entradas queda bloqueado por regla (ver plan, INV-08).
