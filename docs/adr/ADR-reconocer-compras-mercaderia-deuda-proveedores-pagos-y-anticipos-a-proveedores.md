# ADR-reconocer-compras-mercaderia-deuda-proveedores-pagos-y-anticipos-a-proveedores: Asiento del pago a proveedores y anticipos a proveedores

**Estado:** Propuesto
**Task relacionado:** TASK-reconocer-compras-mercaderia-deuda-proveedores
**Fecha:** 2026-11-17
**Reemplaza parcialmente a:** `ADR-reconocer-compras-mercaderia-deuda-proveedores-evento-recepcion-y-asiento.md` (decisión 7: «pago antes de recibir deja saldo deudor» queda reemplazada; las demás siguen vigentes)

## Contexto
La persona amplió COM-02 con COM-01 (Trello «Registrar pagos de compras contra cuentas por pagar»): el pago de una compra debe tener su asiento. Hoy `RegisterPayment` solo guarda el pago y exige una clasificación de egreso (`purchases/application/payment_commands.py:20-69`); el catálogo ya trae `PURCHASE_PAYMENT` (Debe `PAYABLE` / Haber `MONEY` por método) (`accounting/domain/posting.py:95`). Un pago puede hacerse desde que la compra está confirmada, antes de recibir (`Purchase.can_pay`, `purchase.py:338-342`); sin deuda reconocida, Debe Cuentas por pagar crearía deuda inexistente. La tarjeta pide tratar el pago anticipado como Activo «Anticipos a proveedores» aplicado al reconocer la compra, y no inventar deuda. Decisiones de la persona (2026-11-17): (1) anticipos a proveedores como flujo real, (2) cuenta de salida por el método de pago, (3) dejar de exigir la clasificación de egreso.

## Decisión
1. **Catálogo de Contabilidad** (`accounting/domain/posting.py`): rol nuevo `SUPPLIER_ADVANCES` («Anticipos a proveedores», Activo, sin código ni id fijo) y evento `PURCHASE_ADVANCE` (Debe `SUPPLIER_ADVANCES` / Haber `MONEY`). `PURCHASE_RECOGNITION` gana una **segunda línea de Haber** opcional (`extra_credit_role = SUPPLIER_ADVANCES`) para aplicar anticipos, espejo de la segunda línea de Debe de `SALE_DELIVERY`. Ninguna línea de importe cero. `PURCHASE_PAYMENT` no cambia.
2. **Un pago puede dar hasta dos asientos**, ambos con `origin_id` = id del pago y distinto evento: la parte que **liquida deuda reconocida** → `PURCHASE_PAYMENT` (Debe Cuentas por pagar / Haber cuenta del método); el resto, que excede la deuda reconocida → `PURCHASE_ADVANCE` (Debe Anticipos a proveedores / Haber cuenta del método). Cuenta de salida = mapeo **método → cuenta** existente (fuente única); el diálogo muestra el asiento previsto. No hay selector de cuenta por pago.
3. **Deuda reconocida por compra** = valor acumulado de lo recibido en recepciones vigentes (`Σ subtotal(cantidad recibida, precio de línea)`, mismo cálculo y redondeo de la decisión 1 del ADR vigente) − deuda ya pagada. **Deuda ya pagada** = Σ `debt_amount` de los pagos + Σ `advance_applied` de las recepciones vigentes. Pago `p`: `debt_part = min(p, max(deuda reconocida, 0))`, `advance_part = p − debt_part`. Todo bajo el bloqueo de la compra que ya usa `RegisterPayment` (dos pagos simultáneos se serializan y el segundo ve al primero).
4. **Aplicación al recibir:** el reconocimiento de la recepción de importe `R` aplica `a = min(R, anticipos pendientes)` donde pendientes = Σ `advance_amount` de los pagos − Σ `advance_applied` de las recepciones vigentes: Debe Inventario `R` / Haber Cuentas por pagar `R − a` / Haber Anticipos `a`. Revertir la recepción revierte el asiento completo; los anticipos vuelven a estar pendientes porque la recepción deja de ser vigente.
5. **Persistencia (migración aditiva):** `purchases_payment.debt_amount` y `advance_amount` (Decimal 12,2, `debt_amount + advance_amount = amount`) y `purchases_receipt.advance_applied` (Decimal 12,2, anticipos aplicados por esa recepción). Datos existentes: `debt_amount = amount`, `advance_amount = 0`, `advance_applied = 0` (los pagos históricos cuentan como deuda pagada). Sin tablas nuevas ni cambios en `accounting`.
6. **Cobertura (CONT-07/10):** la fecha contable del pago es `payment_date`. Sin cobertura (módulo deshabilitado, anterior al corte, hueco) el pago se guarda **sin asiento** y se registra como `debt_amount = amount` (nunca crea anticipos que no estén en el libro). Con cobertura y configuración incompleta (rol Anticipos o Cuentas por pagar sin cuenta, método sin cuenta activa o ajena/inactiva) → 409 `posting_configuration_missing` con `issues`; período cerrado/fuera de períodos → 409 `fiscal_period_unavailable`. Todo corre en la transacción de `_run`: pago, importes y asientos son todo o nada.
7. **Clasificación de egreso:** deja de exigirse. Si hay una configurada y válida se sigue guardando como instantánea; si no, el pago se registra igual y nunca falla por ella. La API y la pantalla de configuración de la clasificación no cambian.
8. **Vista previa y vínculo:** `GET /api/purchases/{id}/payments/preview/?amount=&method=&payment_date=` devuelve el desglose (deuda / anticipo), las líneas Debe/Haber con nombre de cuenta y los `issues`, sin escribir nada. La lista de pagos expone `accounting_entries` (asientos del pago, 0-2) consultados con una fachada nueva `automatic_entries_for(company_id, event, origin_ids)`.
9. **Anulaciones:** no existen anulaciones ni reembolsos de pagos (`PaymentRecordStatus.VOIDED` no lo produce ningún flujo; cancelar una compra con pagos está bloqueado, `purchase.py:327-330`); no se agregan.
10. **Pagos anteriores al corte:** un pago sin asiento, con compras recibidas después del corte, deja Cuentas por pagar sin liquidar en el libro (el pago no se contabilizó); es el mismo límite de los cobros históricos y se regulariza con el saldo de apertura/regularización de CONT-07. Se documenta como limitación.

## Alternativas consideradas
- **Bloquear pagos antes de recibir:** cambia el flujo actual y rompe compras pagadas por adelantado (comunes con proveedores). Descartada por la persona.
- **Solo documentar saldo deudor** (ADR vigente, decisión 7): deja Cuentas por pagar con saldo deudor y mezcla anticipos con deuda. Reemplazada.
- **Calcular lo pagado/aplicado leyendo el libro** en lugar de columnas: obligaría a Compras a interpretar líneas de asientos y fallaría con pagos sin cobertura. Descartada: columnas explícitas en Compras, el libro solo se escribe.
- **Un único asiento por pago con tres líneas** (deuda + anticipo + caja): `post_automatic_entry` solo modela una línea de Haber/Debe extra; dos asientos independientes son idempotentes por evento y más simples de revertir.
- **Selector de cuenta de salida por pago:** más validaciones y campo nuevo de API sin beneficio claro; descartada por la persona.

## Estrategia de rollback / mitigación
Migración aditiva `purchases 0009` (solo `AddField` y una actualización de datos): revertir con `migrate purchases 0008` borra las tres columnas; los asientos ya publicados son inmutables y no se tocan. Antes de desplegar con cobertura activa, configurar el rol «Anticipos a proveedores» (y Cuentas por pagar e Inventario); sin él, pagar se rechaza con un mensaje accionable (solo cuando el pago genera anticipo; un pago que solo liquida deuda no lo exige). Para neutralizar el efecto: deshabilitar Contabilidad o fijar el corte posterior a la fecha de operación.

## Consecuencias
- Con cobertura, pagar exige cuenta de Caja/Banco para el método y, si hay anticipo, el rol Anticipos a proveedores.
- Recibir con anticipos pendientes cambia el asiento de reconocimiento (línea extra de Haber).
- Un pago puede producir dos asientos; la interfaz los lista.
- Recepciones o pagos históricos sin asiento no se regularizan aquí.
- La clasificación de egreso queda sin uso obligatorio (candidata a retiro en una tarea posterior).
