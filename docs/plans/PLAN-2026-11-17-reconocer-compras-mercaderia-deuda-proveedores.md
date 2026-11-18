# PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores (v2)

**Task:** TASK-reconocer-compras-mercaderia-deuda-proveedores · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-reconocer-compras-mercaderia-deuda-proveedores-errores-accionables-y-asiento-en-recepcion.md` · `docs/design/DDR-reconocer-compras-mercaderia-deuda-proveedores-dialogo-de-pago-asiento-previsto-y-vinculo.md` (v2) · `docs/adr/ADR-reconocer-compras-mercaderia-deuda-proveedores-evento-recepcion-y-asiento.md` (decisión 7 reemplazada) · `docs/adr/ADR-reconocer-compras-mercaderia-deuda-proveedores-pagos-y-anticipos-a-proveedores.md` (v2)

## Objective
**v2:** además, contabilizar el **pago** al proveedor (COM-01 incorporado por decisión de la persona): Debe Cuentas por pagar / Haber Caja o Banco contra deuda reconocida; lo pagado antes de la deuda es un **anticipo a proveedores** (Activo) que se aplica al reconocer la recepción.

Contabilizar la **adquisición de mercadería** al registrar una recepción (Debe Inventario / Haber Cuentas por pagar, un asiento por recepción), separada del pago al proveedor (COM-01), de forma atómica, idempotente, enlazada y respetando cobertura y períodos.

## Context
Base: `accounting` (CONT-12 y VEN-01 integrados). Hechos con `archivo:línea` en el TASK y en el ADR. Compras hoy no contabiliza.

# Specification

## Domain context
`purchases` (compra, recepción, pagos) consume `accounting` solo por `accounting.services` desde `infrastructure/adapters.py`. `accounting` no cambia su catálogo (ya tiene `PURCHASE_RECOGNITION`/`PURCHASE_PAYMENT`). INV-01 (costo de ventas) queda fuera.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Reconocimiento de compra | Asiento `PURCHASE_RECOGNITION` por recepción: Debe Inventario / Haber Cuentas por pagar (Proveedores) | ADR §1-2; `accounting/domain/posting.py:94` |
| Importe reconocido | Σ cantidad recibida × precio unitario de la línea (redondeo por línea a 2 decimales) | `purchases/domain/purchase.py:110` |
| Cobertura | `coverage_status(fecha)`: si la operación debe crear asiento | `accounting/services.py:167` |
| Pago anticipado | Pago antes de recibir; deja Proveedores deudor hasta recibir | ADR §7 |

## Current behavior
Confirmar, recibir y pagar no crean asientos (`purchase_commands.py:121`, `receipt_commands.py:55`, `payment_commands.py:20`). Recibir registra entradas de stock si Inventario está activo (`receipt_commands.py:89-103`). Revertir una recepción revierte stock y recalcula el estado (`receipt_commands.py:125-154`).

## Expected behavior
Con Contabilidad habilitada y **cobertura** de la fecha de recepción:
- Borrador, confirmar, cancelar y pagar: sin asiento de reconocimiento ni cambio de comportamiento.
- **Registrar una recepción** (parcial o completa, con o sin Inventario): un asiento Debe `INVENTORY` / Haber `PAYABLE` por el importe recibido, fecha = fecha de la recepción, en la misma transacción que la recepción y las entradas de stock.
- **Reintentar** la recepción (mismo `receipt_id`) o repetir el evento desde otro módulo no duplica el asiento ni el importe.
- **Revertir** una recepción revierte su asiento (cuentas originales, fecha de hoy) en la misma transacción; sin asiento, no hay nada que revertir.
- Si falta configuración, el período está cerrado o falla el motor: la recepción **no se guarda** (ni stock ni asiento).
- Sin cobertura (módulo deshabilitado, anterior al corte o hueco): recepción como hoy, sin asiento y sin error.
- Nunca se generan gastos operativos.
- **v2 · Pagar** (compra confirmada, con cobertura de `payment_date`): un pago de `p` crea hasta dos asientos con `origin_id` = id del pago: `PURCHASE_PAYMENT` (Debe Cuentas por pagar / Haber cuenta del método) por la parte que liquida deuda reconocida y `PURCHASE_ADVANCE` (Debe Anticipos a proveedores / Haber cuenta del método) por el exceso. Pagar no mueve stock ni crea gastos. Pago, importes y asientos son atómicos e idempotentes por `payment_id`.
- **v2 · Recibir con anticipos pendientes:** el reconocimiento aplica `a = min(importe, anticipos pendientes)`: Debe Inventario / Haber Cuentas por pagar (importe − a) / Haber Anticipos a proveedores (a), sin líneas de cero. Revertir la recepción devuelve el anticipo a pendiente.
- **v2 · Vista previa:** el diálogo de pago muestra el desglose y el asiento previsto; la pestaña Pagos enlaza los asientos de cada pago.
- **v2 · Clasificación de egreso:** ya no se exige para pagar (si hay una válida se guarda como instantánea).

## Domain rules / invariants
- **INV-01** (nueva) Una recepción tiene como máximo un asiento de reconocimiento (`origin_id` = id de la recepción) y su importe es Σ `quantity × unit_price` de sus líneas; recibir todo reconoce el total de la compra.
- **INV-02** (nueva) Recibir y contabilizar son todo o nada (stock + recepción + asiento).
- **INV-03** (existente, CONT-02/12) Importes `Decimal` > 0 en BOB, partida doble, período abierto, idempotencia por `(empresa, evento, origen)`, reversión con cuentas originales.
- **INV-04** (nueva) Ningún asiento de reconocimiento por un importe 0 (recepción de líneas con precio 0 no genera asiento).
- **INV-05** (existente) Aislamiento por `company_id`; el pago no cambia las cuentas de reconocimiento.
- **INV-06** (v2, nueva) Por pago: `debt_amount + advance_amount = amount`; `debt_amount ≤ deuda reconocida pendiente` (valor acumulado recibido − Σ `debt_amount` − Σ `advance_applied`).
- **INV-07** (v2, nueva) Anticipos aplicados por recepciones vigentes ≤ anticipos pagados (Σ `advance_amount`); el saldo neto de Anticipos a proveedores en el libro = anticipos pendientes de aplicar (de pagos con cobertura).
- **INV-08** (v2, nueva) Por compra, Cuentas por pagar neto = valor recibido reconocido − deuda pagada − anticipos aplicados; nunca se crea deuda ni se reconoce inventario al pagar.
- **INV-09** (v2, existente) El pago no supera el saldo de la compra (`total − pagado`) y se serializa con el bloqueo de la compra.

## Acceptance criteria
- **AC-01** Compra de 1.000 recibida completa: un asiento Debe Inventario 1.000 / Haber Proveedores 1.000 (tarjeta AC1); el saldo de Proveedores en `journal_balances` es 1.000.
- **AC-02** Recepciones parciales: cada una reconoce su importe (p. ej. 400 y luego 600); la suma = total de la compra; recibir cantidades que superan lo pendiente sigue siendo rechazado como hoy.
- **AC-03** Con la compra reconocida, un pago de 300 no genera un segundo asiento de inventario ni gasto (v1; desde v2 el pago sí tiene asiento, AC-11 y AC-12); un asiento `PURCHASE_PAYMENT` aplicado por la fachada (lo que hará COM-01) deja Proveedores en 700 sin tocar Inventario ni gastos (tarjeta AC2).
- **AC-04** Reintento con el mismo `receipt_id` (HTTP 200) y concurrencia de dos recepciones iguales no duplican asiento ni importe; el mismo evento reconocido «por ambos módulos» (llamada repetida a la fachada con el mismo origen) devuelve el asiento existente (tarjeta AC3).
- **AC-05** Borrador, confirmar y cancelar no crean asientos ni cambian saldos (tarjeta AC4); un fallo del asiento (configuración faltante, período cerrado, motor) deja la compra sin recepción, sin stock y sin asiento (atomicidad).
- **AC-06** Cobertura: Contabilidad deshabilitada, fecha anterior al corte o en un hueco → recepción sin asiento y sin error; con cobertura y cuentas `INVENTORY`/`PAYABLE` sin configurar → 409 `posting_configuration_missing` con `issues`, sin escribir nada; período cerrado → 409 `fiscal_period_unavailable`.
- **AC-07** Revertir una recepción con asiento crea el asiento de reversión (Haber Inventario / Debe Proveedores) y deja los saldos de la compra en cero; sin asiento sigue como hoy; período de hoy cerrado → 409 sin revertir stock ni estado.
- **AC-08** Enlace: el detalle de la recepción devuelve `accounting_entry` (`id`, `accounting_date`, `total`) o `null`, y la descripción del asiento contiene la referencia de la compra y de la recepción.
- **AC-09** Independencia: con Inventario deshabilitado (recepción `DOCUMENTAL`) o líneas sin control de stock, el asiento se crea igual; sin Contabilidad, Compras funciona como hoy (regresión).
- **AC-11** (v2) Compra de 1.000 recibida completa; pagar 300 en efectivo y 700 por transferencia crea dos asientos `PURCHASE_PAYMENT` (Debe Cuentas por pagar 300 / Haber Caja 300; Debe Cuentas por pagar 700 / Haber Banco 700); Cuentas por pagar queda en cero (tarjeta COM-01 AC1).
- **AC-12** (v2) Pagar no cambia Inventario ni Gastos; el reintento del mismo `payment_id` (200) no duplica pago ni asientos (tarjeta AC2).
- **AC-13** (v2) Dos pagos simultáneos que juntos exceden el saldo no pueden confirmarse ambos (el segundo recibe 400/409 y no deja asiento) (tarjeta AC3).
- **AC-14** (v2) Falla contable (cuenta del método sin configurar, inactiva o ajena; rol sin cuenta; período cerrado; fuera de períodos) → el pago no se guarda ni deja asiento; 409 `posting_configuration_missing` (con `issues`) o `fiscal_period_unavailable` (tarjeta AC4).
- **AC-15** (v2) Pagar antes de recibir (compra confirmada sin recepción): asiento `PURCHASE_ADVANCE` Debe Anticipos a proveedores / Haber Caja o Banco; no crea gasto ni reduce deuda inexistente; un pago mixto (parte deuda, parte anticipo) crea los dos asientos y `debt_amount + advance_amount = amount` (tarjeta AC5).
- **AC-16** (v2) Al recibir con anticipos pendientes el asiento aplica el anticipo (Haber Anticipos) y Cuentas por pagar queda por el resto; todo pagado por adelantado y recibido en dos tandas deja Anticipos y Cuentas por pagar en cero y Inventario por el total; revertir la recepción restituye el anticipo pendiente.
- **AC-17** (v2) Configuración: Compras ofrece el rol Anticipos a proveedores (solo cuentas de Activo) y el evento «Pagar por adelantado a un proveedor»; un pago que solo liquida deuda no exige ese rol; uno con anticipo sin ese rol → 409 con `issues`.
- **AC-18** (v2) Vista previa: `GET .../payments/preview/` devuelve desglose, líneas con nombre de cuenta e `issues` sin escribir nada; valida monto, método y fecha como el alta.
- **AC-19** (v2) Vínculo: la lista de pagos expone `accounting_entries` (0-2 asientos por pago); el campo Origen de Movimientos muestra la etiqueta del evento automático y su módulo (no el código técnico).
- **AC-20** (v2) La clasificación de egreso deja de exigirse: pagar sin clasificación configurada funciona con cobertura; con una válida se sigue guardando.
- **AC-21** (v2) Sin cobertura (Contabilidad deshabilitada, anterior al corte, hueco): el pago se guarda como hoy, sin asiento y sin error, con `debt_amount = amount`; los pagos existentes se migran con `debt_amount = amount`.
- **AC-10** UI: el formulario de recepción y el diálogo de reversión muestran los rechazos accionables y el detalle muestra el asiento o «Sin asiento contable» (DDR), con textos en es/en/pt.

## Edge cases / Error cases
- Recepción con importe 0 (precios 0) → sin asiento (INV-04).
- Recepción anterior a esta tarea sin asiento → revertir no falla.
- **v2** Pago antes de recibir = anticipo a proveedores (ADR de pagos §2); pago mixto = dos asientos; pago por un importe mayor que la deuda reconocida pero menor que el saldo de la compra = deuda + anticipo.
- **v2** Revertir una recepción tras pagar: la deuda reconocida baja y los pagos ya aplicados pueden dejar Cuentas por pagar con saldo deudor (límite documentado).
- **v2** Pago anterior al corte de una compra recibida después: el libro no tiene el pago (limitación, ADR §10).
- **v2** Compra recibida antes del corte (o antes de esta tarea, sin asiento) y pagada después con cobertura: el pago se reparte como deuda y Cuentas por pagar puede quedar deudor hasta regularizar (límite aceptado, ADR §11, REV-08).
- Reversión en la misma transacción que el stock: si el stock falta (`RevertStockShortage`) no se revierte el asiento.
- Cuenta `INVENTORY` compartida con INV-01: cambiarla no afecta asientos ya publicados (guardan sus cuentas).

## Authorization / permissions
Sin permisos nuevos: las vistas de recepción mantienen `required_modules`/permisos de Compras; contabilizar corre con el usuario autenticado como `created_by`. El panel de configuración sigue con los permisos de Contabilidad (CONT-12).

## API contract
- **API-01** `POST /api/purchases/{id}/receipts/` y `.../revert/`: nuevos 409 `{code: 'posting_configuration_missing' | 'fiscal_period_unavailable' | 'ledger_rejected' | 'ledger_conflict', detail, issues?}` (forma de Ventas: `issues[{code, role, subject, message, params}]`). Compatible hacia atrás: solo aparecen con cobertura.
- **API-02** `GET`/`POST` detalle de recepción: campo aditivo `accounting_entry: {id, accounting_date, total} | null`.

- **API-03** (v2) `GET /api/purchases/{id}/payments/preview/?amount=&method=&payment_date=` → `{debt_amount, advance_amount, lines:[{side, role, account:{name}, amount}], issues:[...], covered}`; solo lectura.
- **API-04** (v2) `GET .../payments/` y `POST .../payments/`: campos aditivos `debt_amount`, `advance_amount`, `accounting_entries:[{id, kind: debt|advance, accounting_date, total}]`; `POST` nuevos 409 como API-01; ya no devuelve el error de clasificación.
- **API-05** (v2) Detalle del asiento en Contabilidad: `origin.label` y `origin.module` del evento automático (aditivo).

## UI behavior
- **UI-01** Formulario de recepción: alerta de `issues` con enlace a Compras › Asientos automáticos y mensaje de período; conserva lo escrito (DDR).
- **UI-02** Diálogo de reversión: error de período sin cerrar el diálogo.
- **UI-03** Detalle de recepción: fila «Asiento contable» con enlace, o «Sin asiento contable»; oculta con Contabilidad deshabilitada.

- **UI-04** (v2) Diálogo de pago: bloque «Asiento previsto» y alertas accionables (DDR 2).
- **UI-05** (v2) Pestaña Pagos: enlaces a los asientos del pago y marca de anticipo (DDR 2).
- **UI-06** (v2) Movimientos: Origen con etiqueta y módulo del evento (DDR 2).

## Non-functional requirements
`Decimal`, BOB sin conversión; una consulta extra por recepción para `find_automatic_entry`; v1 sin migraciones, v2 con la migración aditiva `purchases/0009`.

## Out of scope
costo de ventas y salidas (INV-01) y contabilidad de existencias iniciales/ajustes de Inventario; anulaciones o reembolsos de pagos (no existen); selector de cuenta de salida por pago; impuestos y costos adicionales (flete, aduana); regularización de recepciones históricas (CONT-07); notas de crédito/devoluciones a proveedor; multimoneda.

## Open questions
- Si INV-01 quisiera ser dueño del asiento de recepción (ADR §2): cambio de ADR, no bloquea.
- Tratamiento de pagos anticipados con cuenta de anticipos a proveedores: futuro.

# Test Specification

## Unit tests
- Dominio: `Purchase.receipt_amount` (parcial, completa, redondeo, cero) → AC-01, AC-02, INV-01/04.
- Aplicación con puerto falso: `RegisterReception` publica una vez, no publica en reintento, propaga rechazo sin guardar; `RevertReception` revierte el asiento antes de marcar revertida → AC-04, AC-05, AC-07.
## Integration tests
- Con Contabilidad real (como `sales/tests/test_sales_posting.py`): AC-01..AC-09, cobertura (corte, hueco, deshabilitado), período cerrado, concurrencia con hilos (`TransactionTestCase`), boundaries (`purchases → accounting` solo desde adapters).
## E2E
**NO** — el flujo cruza dos módulos cubiertos por integración con base real; no se instala Playwright.
## Regression tests
Suites existentes de `purchases` (recepciones, reversión, pagos) y `accounting` sin Contabilidad deshabilitada; `manage.py test`, `makemigrations --check`; frontend `lint`, `i18n:check`, `test`, `build`.
## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-02 | integración `purchases/tests/test_purchase_posting.py` + unit de dominio |
| AC-03 | integración: pago + `post_automatic_entry('PURCHASE_PAYMENT')` sobre `journal_balances` |
| AC-04 | integración (reintento HTTP 200, hilos, fachada repetida) |
| AC-05 | integración (configuración faltante, período cerrado) + unit con puerto falso |
| AC-06 | integración (deshabilitado, corte, hueco, sin configurar, período cerrado) |
| AC-07 | integración (reversión, sin asiento, período cerrado) |
| AC-08 | integración API + unit del serializer |
| AC-09 | integración (DOCUMENTAL, sin control de stock, sin Contabilidad) |
| AC-10 | specs Karma de reception-form, revert dialog, reception-detail; `i18n:check` |
| AC-11, AC-12 | integración `purchases/tests/test_payment_posting.py` (dos métodos, reintento, Inventario/Gastos intactos) |
| AC-13 | integración con hilos (`TransactionTestCase`, bloqueo de la compra) |
| AC-14 | integración (cuenta inactiva/ajena, rol sin cuenta, período cerrado) + unit con puerto falso |
| AC-15, AC-16 | integración (pago antes de recibir, mixto, aplicación al recibir, reversión) + unit de dominio del reparto |
| AC-17 | integración (rol, evento y 409) + prueba del catálogo en `accounting` |
| AC-18, AC-19 | integración API (vista previa sin escritura, `accounting_entries`, origen en Movimientos) |
| AC-20, AC-21 | integración (sin clasificación, sin cobertura, migración de datos) |
| UI-04..06 | specs Karma de payment-dialog, purchase-payments-tab y detalle de asiento; `i18n:check` |

# Implementation Plan

## Architecture considerations
Puerto `PurchasePosting` en `purchases/application/ports.py` implementado por `PurchasePostingAdapter` (solo `accounting.services`); mismo patrón que `SalesPostingAdapter` (`sales/infrastructure/adapters.py:177-317`). Dominio sin Django.

## Proposed solution
`Purchase.receipt_amount(receipt)` calcula el importe en el dominio. `RegisterReception` y `RevertReception` reciben el puerto opcional; el adaptador comprueba que Contabilidad esté habilitada, usa `post_automatic_entry`/`reverse_automatic_entry` y traduce errores a una excepción de Compras (`PostingRejected(code, message, extra)`) que `_run` convierte en 409.

## Files/components affected
**v2 adicional:** backend `accounting/domain/posting.py` (rol, evento, `extra_credit_role`), `accounting/services.py` (aplicación del anticipo, `preview_automatic_entry`, `automatic_entries_for`), `purchases/domain` (`Payment`, reparto deuda/anticipo, `Receipt.advance_applied`), `payment_commands.py`, `receipt_commands.py`, adaptador, vistas y serializers de pagos, migración `purchases 0009`, etiqueta de origen en el serializer de asientos; frontend `payment-dialog`, `purchase-payments-tab`, modelos/servicios de pagos, detalle de asiento, i18n es/en/pt, fixtures del panel de configuración.

- Backend: `purchases/domain/purchase.py`, `purchases/domain/exceptions.py`, `purchases/application/ports.py`, `receipt_commands.py`, `receipt_queries.py`, `purchases/infrastructure/adapters.py`, `purchases/api/purchase_views.py` (`_run`), `receipt_views.py`, `receipt_serializers.py`; tests nuevos en `purchases/tests/` y ajustes de fakes existentes.
- Frontend: `features/purchases/models/receipt.ts`, servicio de recepciones, `reception-form`, `receipt-revert-dialog`, `reception-detail`, `assets/i18n/{es,en,pt}.json`, specs.
- Docs: TASK, ADR, DDR, este PLAN; `docs/design/design-system.md` solo si cambia un patrón (no previsto).

## Implementation steps
**v2 (después de los pasos 1-7 ya hechos):** 8. Catálogo y fachada de Contabilidad (rol, evento, segunda línea de Haber, aplicación, vista previa, asientos por origen; AC-15..19). 9. Dominio de Compras: reparto deuda/anticipo, columnas y migración con datos (INV-06..09, AC-21). 10. `RegisterPayment` con puerto de pagos: asientos atómicos, sin exigir clasificación (AC-11..14, 20). 11. `RegisterReception`: aplicar anticipos (AC-16). 12. API: vista previa y `accounting_entries` (API-03..05). 13. Frontend (UI-04..06). 14. Pruebas y verificación.

1. Dominio: `receipt_amount` + excepción `PostingRejected` (INV-01/04).
2. Puerto y adaptador (AC-05, AC-06, AC-07, AC-09).
3. Comandos: publicar tras guardar la recepción; revertir asiento antes de marcar revertida (INV-02, AC-04, AC-05, AC-07).
4. API: mapeo 409 en `_run`; `accounting_entry` en el detalle (API-01/02, AC-08).
5. Pruebas backend (AC-01..AC-09) y de fronteras.
6. Frontend (UI-01..03, AC-10) con i18n es/en/pt.
7. Documentar en el panel/TASK el saldo deudor temporal por pagos anticipados.

## Database / migrations
**v2:** `purchases 0009` aditiva: `purchases_payment.debt_amount`, `advance_amount`; `purchases_receipt.advance_applied` (Decimal 12,2, default 0) y actualización de datos `debt_amount = amount` en pagos existentes. Reversible (`migrate purchases 0008`). `accounting` sin migraciones.

## Risks
- Cambio de reglas: con cobertura, recibir exige configuración (documentado, acotado).
- Coordinación con INV-01: ADR §2 fija el dueño; riesgo de doble asiento si INV-01 posteara recepciones (prueba de no duplicación por origen).
- Revertir con período cerrado bloquea la corrección operativa (aceptado).
- Reversión en la fecha de hoy, no en la de la recepción (patrón de Ventas).

## New dependencies
Ninguna.

## Changelog
- **v2** (2026-11-17): [Specification] Se incorpora COM-01: asiento del pago, anticipos a proveedores, vista previa y vínculo, clasificación de egreso opcional, etiqueta de origen en Movimientos (AC-11..AC-21, INV-06..09, API-03..05, UI-04..06). Aprobado explícitamente por la persona (pidió ampliar la tarea y eligió: anticipos a proveedores, cuenta por método de pago, dejar de exigir la clasificación). [Implementation Plan] pasos 8-14 y migración `purchases 0009`. La contabilidad de Inventario (INV-01) sigue fuera de alcance.
