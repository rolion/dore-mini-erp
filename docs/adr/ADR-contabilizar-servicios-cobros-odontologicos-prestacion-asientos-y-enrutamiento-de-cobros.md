# ADR-contabilizar-servicios-cobros-odontologicos-prestacion-asientos-y-enrutamiento-de-cobros: Prestación de servicios, asientos y ruteo de cobros

**Estado:** Propuesto
**Task relacionado:** TASK-contabilizar-servicios-cobros-odontologicos
**Fecha:** 2026-11-17

## Contexto
Cobros (`receivables`) registra pagos por línea aceptada de una proforma y los anota en el libro anterior (origen `SERVICE`). Contabilidad ya ofrece el motor de partida doble, la configuración por módulo (CONT-12) y el patrón de VEN-01 (anticipos, reconocimiento, cobro contra Cuentas por cobrar). Falta el hecho de negocio que reconoce un servicio: no existe «servicio prestado». La persona decidió una acción explícita por tratamiento, irreversible.

## Decisión
1. **Nuevo concepto `RenderedService` en `receivables`** (una fila por obligación y *lineage* de línea): `id` (UUID, es el `origin_id` del asiento), `lineage_id`, `line_id`, descripción, importe aceptado, `service_date`, usuario y fecha de alta. Tabla `receivables_rendered_service` con único `(obligation, lineage_id)` y `CHECK(amount > 0)`; migración aditiva (`receivables/0002`). Marcar es idempotente por esa unicidad. La obligación se crea si aún no existe (prestar sin cobros previos).
2. **Reglas del dominio** (`Obligation.mark_rendered`, puro): solo con la proforma presentada vigente, línea aceptada, no prestada, fecha ≤ hoy. El importe reconocido es el aceptado de la línea (inmutable una vez aceptada). Marcar llama a `mark_lines_collected` para que la línea no pueda rectificarse a rechazada.
3. **Catálogo de Contabilidad:** `SERVICE_RECOGNITION` pasa a llevar `extra_debit_role='CUSTOMER_ADVANCES'` (nunca se contabilizó, no hay asientos históricos) y se añade `SERVICE_ADVANCE` (Debe `MONEY` por método / Haber `CUSTOMER_ADVANCES`). `SERVICE_PAYMENT` no cambia. El panel de configuración, dirigido por datos, los muestra sin tocar el componente; solo hacen falta las claves i18n.
4. **Asientos** (siempre por `post_automatic_entry`, en la transacción del caso de uso, `origin_kind` = evento):
   - *Marcar prestado:* `SERVICE_RECOGNITION`, origen = id de la prestación, fecha = `service_date`, importe = importe de la línea, `advance_applied` = lo imputado hasta ahora a esa línea (todo cobro a una línea no prestada fue anticipo). Debe CxC por el resto, Debe Anticipos por lo aplicado, Haber Ingresos por servicios; sin líneas de importe cero.
   - *Cobro:* cada pago se divide por sus imputaciones en hasta tres porciones, cada una en **exactamente un camino**: (a) a líneas prestadas con reconocimiento contabilizado → `SERVICE_PAYMENT`; (b) a líneas no prestadas con fecha cubierta → `SERVICE_ADVANCE`; (c) el resto (fecha sin cobertura, o línea prestada sin asiento porque su fecha no tenía cobertura) → libro anterior `SERVICE` por el importe de la porción. (a) y (b) usan `origin_id` = id del pago con eventos distintos, por lo que son idempotentes por `(evento, origen)`. Si no hay porción contabilizada ni legada, no se crea nada.
   - El estado contable de una línea se deduce del libro (`find_automatic_entry`/`automatic_entry_origins`), sin bandera ni migración extra.
5. **Bloqueos accionables (409 con `code`)**: `posting_configuration_missing` (con `issues`), `payment_date_not_covered` (cobro a línea prestada o con asiento y fecha sin cobertura), `service_has_unposted_payments` (prestar con cobertura una línea cuyos cobros no tienen asiento), `fiscal_period_unavailable`, `ledger_rejected`, `ledger_conflict`. Con Contabilidad deshabilitada no se bloquea ni se contabiliza nada (marcar prestado sigue siendo un hecho válido).
6. **Atomicidad:** prestar y cobrar corren en una transacción; un rechazo contable deshace la prestación/el pago. Orden de bloqueo existente: obligación → proforma.
7. **Contrato API:** `POST /api/receivables/commitments/<kind>/<number>/services/` con `{line_id, service_date?}` → 201 (nueva) o 200 (ya prestada, sin asiento nuevo). El detalle del compromiso añade por línea `rendered`, `service_date`, `can_render` y en totales `recognized`; cambios solo aditivos.
8. **Sin Agenda ni reembolsos:** no se vincula la cita «atendida» ni se introduce anulación/reembolso de servicios o pagos.

## Alternativas consideradas
- **Reconocer al cobrar (Debe Caja / Haber Ingresos):** no distingue prestación de cobro y descarta Cuentas por cobrar y anticipos; contradice la tarjeta.
- **Reconocer con la cita atendida:** exige modelar tratamientos por cita en Agenda/Odontología; alcance mucho mayor.
- **Marca booleana en la línea de la proforma:** acopla `quotations`/`dentistry`, duplica en dos módulos y no guarda fecha ni autor; descartada frente a una tabla propia de Cobros.
- **Un solo asiento por pago con varias líneas de Debe/Haber:** el motor y el catálogo son de dos importes por evento; dividir por porciones reutiliza los eventos sin cambiar el motor.
- **Permitir desmarcar:** exige reversión y política sobre cobros posteriores; descartado por la persona.

## Estrategia de rollback / mitigación
Migración aditiva (tabla nueva): se revierte con `migrate receivables 0001` si no hay filas, y el comportamiento anterior (libro anterior) se recupera retirando el adaptador nuevo; sin cobertura contable el flujo es el mismo de hoy. Los asientos creados son reversibles con asientos de reversa del motor (no se borran). El cambio de reglas aplica solo a empresas con Contabilidad habilitada y fecha cubierta.

## Consecuencias
- La clínica debe configurar Anticipos de clientes, Ingresos por servicios y Cuentas por cobrar antes de cobrar con cobertura (el 409 explica qué falta y dónde).
- Una prestación no se puede deshacer hasta que exista un flujo de anulación/reembolso.
- Pagos anteriores a la cobertura sobre líneas que luego se prestan con cobertura quedan bloqueados (decisión pendiente, como en VEN-01).
- `mark_lines_collected` pasa a significar «con movimiento financiero» (cobrada o prestada).
